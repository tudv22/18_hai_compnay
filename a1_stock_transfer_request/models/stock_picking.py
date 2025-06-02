# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict
from datetime import date
import requests

PICKING_TRANSFER_REQUEST_TYPES = [
    ('outgoing', 'Outgoing'),
    ('incoming', 'Incoming')
]


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_destination_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Destination Warehouse',
    )
    x_stock_transfer_request_id = fields.Many2one(
        'stock.transfer.request',
        string='Stock Transfer Request',
        ondelete='cascade'
    )
    x_is_hide_action_return = fields.Boolean(
        compute='_compute_is_hide_action_return',
        string='Hide Action Return',
    )
    x_origin_out_picking_from_transfer_request_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Origin Out Picking',
    )

    @api.depends('purchase_id', 'sale_id', 'x_stock_transfer_request_id')
    def _compute_is_hide_action_return(self):
        for record in self:
            record.x_is_hide_action_return = bool(
                (record.purchase_id and record.purchase_id.x_stock_transfer_request_id) or
                (record.sale_id and record.sale_id.x_stock_transfer_request_id) or
                record.x_stock_transfer_request_id
            )

    @api.depends('sale_id')
    def _compute_sale_from_transfer_request(self):
        for record in self:
            record.x_sale_from_transfer_request = bool(record.sale_id and record.sale_id.x_stock_transfer_request_id)

    def _check_quantity_with_transfer_request(self):
        for record in self:
            if record.x_stock_transfer_request_id and record.location_dest_id.usage == 'internal':
                err = []
                for line in record.move_ids:
                    if line.quantity != line.product_uom_qty:
                        err.append((line.product_id.name, line.product_uom_qty, line.quantity))
                if err:
                    error_message = (_("The actual quantity of the product does not match the demand \n")) + "\n".join(
                        [_("Product: %s, Expected Quantity: %s, Actual Quantity: %s \n") % (
                            product_name, product_uom_qty, quantity) for product_name, product_uom_qty, quantity in
                         err])
                    raise UserError(error_message)

    def button_validate(self):
        if self.x_stock_transfer_request_id:
            self._check_quantity_with_transfer_request()
            pickings_to_backorder = self._check_backorder()
            if not self.env.context.get('button_validate_picking_ids') and pickings_to_backorder:
                self = pickings_to_backorder.with_context(button_validate_picking_ids=self.ids)
            if pickings_to_backorder:
                res = self._pre_action_done_hook()
                if res is not True:
                    return res

            picking_ids = self.with_context(skip_action_assign_a1=True)._create_inter_company_purchase()

            picking_ids.create_picking_in_for_internal_transfer()
            res = super(StockPicking, picking_ids).button_validate()

            self._check_and_update_transfer_request_state()
        else:
            res = super(StockPicking, self).button_validate()

        return res

    def create_picking_in_for_internal_transfer(self):
        for record in self:
            if (
                    record.x_stock_transfer_request_id
                    and record.x_stock_transfer_request_id.transfer_request_type == 'internal'
                    and record.location_dest_id.usage == 'transit'
            ):
                product_export_quantities = record._get_product_export_total_qty()

                # Validate that we have enough available quantities for the export.
                record._validate_available_qty(product_export_quantities)
                res = record._create_picking_in()
                res.action_assign()

                if record.has_tracking:
                    current_move_line_map = {
                        move.product_id: iter(move.move_line_ids)
                        for move in res.move_ids if move.has_tracking
                    }
                    for move_id in record.move_ids:
                        if not move_id.has_tracking:
                            continue

                        current_move_line_ids = current_move_line_map.get(move_id.product_id)
                        if not current_move_line_ids:
                            continue

                        for move_line_id, current_move_line_id in zip(move_id.move_line_ids, current_move_line_ids):
                            if move_line_id and current_move_line_id:
                                current_move_line_id.sudo().lot_id = move_line_id.lot_id
        return True

    def _check_and_update_transfer_request_state(self):
        for picking in self:
            if picking.x_stock_transfer_request_id and picking.x_stock_transfer_request_id.state != 'done':
                # picking.x_stock_transfer_request_id._check_and_update_state()
                transfer_request = picking.x_stock_transfer_request_id.sudo()

                if picking.location_dest_id.usage == 'transit' and picking.state == 'done':
                    # Đây là picking out vừa done
                    # Picking in sẽ được tạo trong button_validate, sau đó state sẽ là in_transit
                    transfer_request._check_and_update_state()

                elif picking.location_dest_id.usage == 'internal' and picking.state == 'done':
                    # Đây là picking in vừa done → Hoàn thành transfer request
                    transfer_request._check_and_update_state()

    # ------------------------------------------------------
    # HÀM XỬ LÝ LIÊN CÔNG TY
    # ------------------------------------------------------

    def _create_inter_company_purchase(self):
        # Initialize picking_ids to store any pickings that are skipped in the process.
        picking_ids = self.env['stock.picking']

        # Iterate over each picking record.
        for picking in self:
            # Check conditions to decide if we should create an inter-company purchase order.
            if picking.x_stock_transfer_request_id and \
                    picking.x_stock_transfer_request_id.transfer_request_type == 'inter' and \
                    not picking.env.context.get('skip_create_inter_company', False) and \
                    picking.location_dest_id.usage == 'transit':

                # Get the total quantities of products to be exported.
                product_export_quantities = picking._get_product_export_total_qty()

                # Validate that we have enough available quantities for the export.
                picking._validate_available_qty(product_export_quantities)

                # Prepare the purchase order values (header information).
                purchase_vals = picking._prepare_purchase_order_values()

                # Prepare the order lines for the purchase order.
                order_lines = picking._prepare_purchase_order_line(product_export_quantities)

                # Assign the order lines to the purchase order values.
                purchase_vals['order_line'] = order_lines

                # Create the purchase order with the prepared values.
                purchase_order = self.env['purchase.order'].sudo().create(purchase_vals)

                # If the purchase order was created successfully, confirm it.
                if purchase_order:
                    # Confirm the purchase order and trigger the inter-company context (warehouse).
                    # Get serial name you want to get from source company
                    current_move_line_ids = picking.move_line_ids
                    current_name = current_move_line_ids.mapped('lot_name')
                    # for line in current_move_line_ids:
                    #     current_name.append(line.lot_name)
                    # Give context to the picking of sale.order and it will choose from this to create picking out
                    if self.company_id.x_company_type == 'household_company':
                        x_dest_warehouse = picking.x_stock_transfer_request_id.dest_warehouse_id
                        source_company = picking.x_stock_transfer_request_id.sudo().source_company_id
                        context_partner_for_household_company = x_dest_warehouse.partner_id.with_company(source_company)
                    else:
                        context_partner_for_household_company=False
                    purchase_order.sudo().with_context(
                        # skip_sanity_check=True,
                        sale_warehouse_id=picking.x_stock_transfer_request_id.sudo().source_warehouse_id.id,
                        skip_validate_inter_company=True if picking.has_tracking else False,
                        serial_current_name=current_name,
                        skip_assign_move_a1_id=picking.move_ids.ids,
                        context_partner_for_household_company=context_partner_for_household_company,
                        picking_ids_not_to_backorder=False,
                    ).button_confirm()
                    # if any product in picking is tracking by serial, will process this
                    if picking.has_tracking:
                        # Validate the stock picking of so,po
                        purchase_picking = purchase_order.picking_ids
                        purchase_order.with_context(
                            skip_update_voucher_state=True)._validate_sale_order_picking_and_create_invoices()
                        purchase_order._validate_purchase_order_picking_and_create_invoices()

                        # Give serial for current picking

                        current_move_line_map = {
                            move.product_id: iter(move.move_line_ids)
                            for move in picking.move_ids if move.has_tracking
                        }
                        for move_id in purchase_picking.move_ids:
                            if not move_id.has_tracking:
                                continue

                            current_move_line_ids = current_move_line_map.get(move_id.product_id)
                            if not current_move_line_ids:
                                continue

                            for move_line_id, current_move_line_id in zip(move_id.move_line_ids, current_move_line_ids):
                                if move_line_id and current_move_line_id:
                                    current_move_line_id.sudo().lot_id = move_line_id.lot_id

                        # Create the incoming picking for the purchase order.
                        picking_in = picking._create_picking_in()

                        # Validate the stock picking. Skip backorder creation and cancel any backorders.
                        picking.with_context(
                            # skip_backorder=True,
                            # cancel_backorder=True,
                            picking_ids_not_to_backorder=picking.ids,
                            skip_create_inter_company=True,
                        ).button_validate()

                        current_move_line_map = {
                            move.product_id: iter(move.move_line_ids)
                            for move in picking_in.move_ids if move.has_tracking
                        }
                        for move_id in picking.move_ids:
                            if not move_id.has_tracking:
                                continue

                            current_move_line_ids = current_move_line_map.get(move_id.product_id)
                            if not current_move_line_ids:
                                continue

                            for move_line_id, current_move_line_id in zip(move_id.move_line_ids, current_move_line_ids):
                                if move_line_id and current_move_line_id:
                                    current_move_line_id.sudo().lot_id = move_line_id.lot_id
                    else:
                        # Create the incoming picking for the purchase order.
                        picking._create_picking_in()

                        # Validate the stock picking. Skip backorder creation and cancel any backorders.
                        picking.with_context(
                            skip_backorder=True,
                            cancel_backorder=True,
                            skip_create_inter_company=True
                        ).button_validate()
            else:
                # If conditions aren't met, collect the picking in the `picking_ids` recordset.
                picking_ids |= picking

        # Return the picking_ids (which includes any pickings that were skipped).
        return picking_ids

    def _create_picking_in(self):
        location_dest_id = self.move_ids.x_transfer_request_line_id.location_dest_id
        # Get the picking type for the destination location's warehouse
        picking_type_in_id = self.sudo()._get_picking_type(location_dest_id.warehouse_id)
        # Create picking-in
        picking_in = self.sudo().create({
            'location_id': self.location_dest_id.id,
            'location_dest_id': location_dest_id.id,
            'picking_type_id': picking_type_in_id.id,
            'origin': self.x_stock_transfer_request_id.name,
            'x_origin_out_picking_from_transfer_request_id':self.id,
            'x_stock_transfer_request_id': self.x_stock_transfer_request_id.id,
        })
        # Initialize an empty recordset for new moves and a list to store write operations
        new_move_ids = self.env['stock.move']
        move_dest_updates = []
        # Iterate over the moves in the picking out
        for move in self.move_ids:
            # Prepare the values for the new move
            new_move_vals = self._prepare_move_copy_values(move, location_dest_id, picking_type_in_id, picking_in if picking_in else False)
            # Create a copy of the move with the prepared values
            new_move = move.sudo().copy(new_move_vals)
            # Add the new move to the recordset
            new_move_ids |= new_move
            # Accumulate the move_dest_ids updates in memory
            move_dest_updates.append((move.id, new_move.id))
        # Perform a single write operation to update move_dest_ids for all original moves
        if move_dest_updates:
            # Prepare the update values for move_dest_ids
            write_vals = [(4, new_move_id) for move_id, new_move_id in move_dest_updates]
            # Execute the write in a single call for all moves
            self.move_ids.write({'move_dest_ids': write_vals})
        # Confirm the new moves
        new_move_ids._action_confirm()
        # Return the picking related to the new moves
        return new_move_ids.picking_id

    def _prepare_move_copy_values(self, move_to_copy, location_dest_id, picking_type_id, picking_id=False):
        new_move_vals = {
            'origin': move_to_copy.picking_id.x_stock_transfer_request_id.name or move_to_copy.origin or "/",
            'location_id': move_to_copy.location_dest_id.id,
            'location_dest_id': location_dest_id.id,
            'date': move_to_copy.date,
            'date_deadline': move_to_copy.date_deadline,
            'company_id': move_to_copy.company_id.id,
            'product_uom_qty': move_to_copy.quantity,
            'quantity': move_to_copy.quantity,
            'price_unit': move_to_copy.product_id.standard_price,
            'picking_id': picking_id.id if picking_id else False,
            'picking_type_id': picking_type_id.id,
            'warehouse_id': location_dest_id.warehouse_id.id,
            'procure_method': 'make_to_order',
            'x_transfer_request_line_id': move_to_copy.x_transfer_request_line_id.id,
        }
        return new_move_vals

    def _validate_available_qty(self, product_export_quantites):
        warehouse_id = self.x_stock_transfer_request_id.source_warehouse_id
        error_messages = []
        # Use sudo() on the product model once to improve performance
        products = self.env['product.product'].sudo()
        for product_id, total_request_qty in product_export_quantites.items():
            # Get the available quantity in the specified warehouse
            qty_available = products.with_context(warehouse=warehouse_id.id).browse(product_id.id).qty_available
            error_message = False
            if product_id.tracking != 'none':
                if qty_available < 0:
                    error_message = _(
                        "Product %s is out of stock at %s, please check again.",
                        product_id.display_name, warehouse_id.display_name
                    )
                    error_messages.append(error_message)
            else:
            # If the requested quantity exceeds the available quantity, add an error message
                if total_request_qty > qty_available:
                    error_message = _(
                        "Product %s is out of stock at %s, please check again.",
                        product_id.display_name, warehouse_id.display_name
                    )
                    error_messages.append(error_message)
        # If there are any error messages, raise a ValidationError
        if error_messages:
            raise ValidationError("\n".join(error_messages))

    def _prepare_purchase_order_values(self):
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', self.location_id.warehouse_id.id)
        ], limit=1)
        purchase_vals = {
            'partner_id': self.x_stock_transfer_request_id.sudo().source_company_id.partner_id.id,
            'date_planned': self.date,
            'company_id': self.env.company.id,
            'x_stock_transfer_request_id': self.x_stock_transfer_request_id.id,
            'picking_type_id': picking_type_id.id
        }
        return purchase_vals

    def _get_picking_type(self, warehouse_id):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', warehouse_id.id),
        ], limit=1)

    def _prepare_purchase_order_line(self, product_export_quantities):
        order_lines = []  # To store the order lines
        message_error = ''  # To accumulate error messages if any product has no supplier price

        # Retrieve the partner_id for the source company
        company = self.x_stock_transfer_request_id.sudo().source_company_id.partner_id

        for product_id, export_qty in product_export_quantities.items():

            source_company = self.x_stock_transfer_request_id.sudo().source_company_id

            internal_pricelist = self.company_id.partner_id.with_company(source_company).property_product_pricelist

            unit_price = internal_pricelist.with_context(x_warehouse_for_sh_cost=self.x_stock_transfer_request_id.source_warehouse_id.id)._get_product_price(
                product_id,
                export_qty or 1.0,
            )
            # unit_price = False
            if not unit_price and unit_price != 0:
                message_error += _(
                    "Pricelist is not configured for product %s. Cannot create inter-company purchase order.\n",
                    product_id.display_name
                )
                continue

            # Get the applicable taxes for the product based on the company
            taxes = product_id.supplier_taxes_id.filtered(lambda r: r.company_id == self.company_id)
            tax_source_company = product_id.with_company(source_company).taxes_id._filter_taxes_by_company(source_company).filtered(lambda t:t.price_include == True)
            price_unit_exclude_tax = unit_price / (1 + sum(tax_source_company.mapped('amount')) / 100)
            include_tax_price_for_house_hold_company = self.company_id.x_company_type == 'household_company'
            # Append the order line to the list
            order_lines.append((0, 0, {
                'product_id': product_id.id,
                'product_qty': export_qty,
                'taxes_id': [(6, 0, taxes.ids)],  # Linking the taxes
                'price_unit': price_unit_exclude_tax if include_tax_price_for_house_hold_company else unit_price,
                'product_uom': product_id.uom_id.id
            }))

        # If any error message has been accumulated, raise a validation error
        if message_error:
            raise ValidationError(message_error)

        # Return the created order lines
        return order_lines

    def _get_product_export_total_qty(self):
        # Initialize a defaultdict to accumulate quantities by product_id
        product_export_quantities = defaultdict(float)
        # Iterate over the request lines and accumulate the requested quantity for each product_id
        for move in self.move_ids:
            product_export_quantities[move.product_id] += move.quantity
        # Convert the defaultdict to a regular dictionary before returning (optional)
        return dict(product_export_quantities)

    # ------------------------------------------------------
    # HÀM XỬ LÝ LIÊN CÔNG TY: END
    # ------------------------------------------------------

