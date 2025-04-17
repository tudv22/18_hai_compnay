# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import _, fields, models
from collections import defaultdict
from odoo.tools.float_utils import float_round, float_is_zero, float_compare


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse",store=True)


class WarehouseStockMove(models.Model):
    _inherit = "stock.move"

    sh_in_replenshment = fields.Boolean("Is Replenishment")

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if not self.origin_returned_move_id and self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id
            received_qty = line.qty_received
            if self.state == 'done':
                received_qty -= self.product_uom._compute_quantity(self.quantity, line.product_uom, rounding_method='HALF-UP')
            if float_compare(line.qty_invoiced, received_qty, precision_rounding=line.product_uom.rounding) > 0:
                move_layer = line.move_ids.stock_valuation_layer_ids
                invoiced_layer = line.invoice_lines.stock_valuation_layer_ids
                receipt_value = sum(move_layer.mapped('value')) + sum(invoiced_layer.mapped('value'))
                invoiced_value = 0
                invoiced_qty = 0
                for invoice_line in line.invoice_lines:
                    if invoice_line.tax_ids:
                        invoiced_value += invoice_line.tax_ids.with_context(round=False).compute_all(
                            invoice_line.price_unit, currency=invoice_line.account_id.currency_id, quantity=invoice_line.quantity)['total_void']
                    else:
                        invoiced_value += invoice_line.price_unit * invoice_line.quantity
                    invoiced_qty += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_id.uom_id)
                # TODO currency check
                remaining_value = invoiced_value - receipt_value
                # TODO qty_received in product uom
                remaining_qty = invoiced_qty - line.product_uom._compute_quantity(received_qty, line.product_id.uom_id)
                price_unit = float_round(remaining_value / remaining_qty, precision_digits=price_unit_prec)
            else:
                price_unit = line.price_unit
                if line.taxes_id:
                    qty = line.product_qty or 1
                    price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
                    price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
                if line.product_uom.id != line.product_id.uom_id.id:
                    price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                # The date must be today, and not the date of the move since the move move is still
                # in assigned state. However, the move date is the scheduled date until move is
                # done, then date of actual move processing. See:
                # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                price_unit = order.currency_id._convert(
                    price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)
            return price_unit
        self.ensure_one()
        price_unit = self.price_unit
        precision = self.env['decimal.precision'].precision_get('Product Price')
        # If the move is a return, use the original move's price unit.
        if self.origin_returned_move_id and self.origin_returned_move_id.sudo().stock_valuation_layer_ids:
            layers = self.origin_returned_move_id.sudo().stock_valuation_layer_ids
            layers |= layers.stock_valuation_layer_ids
            quantity = sum(layers.mapped("quantity"))
            return layers.currency_id.round(sum(layers.mapped("value")) / quantity) if not float_is_zero(quantity, precision_rounding=layers.uom_id.rounding) else 0
        # Custom Code update cost price as per warehouse rather than product standard price
        price = self.product_id.warehouse_cost_lines.filtered(
                lambda x: x.warehouse_id.id == self.location_dest_id.warehouse_id.id).cost
        if price:
            return price
        # Custom Code update cost price as per warehouse rather than product standard price
        return price_unit if not float_is_zero(price_unit, precision) or self._should_force_price_unit() else self.product_id.standard_price


    def _prepare_common_svl_vals(self):
        # * Softhealer code Start *

        # Added warehouse in the returning dict

        # * Softhealer code end *

        self.ensure_one()
        return {
            'stock_move_id': self.id,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'description': self.reference and '%s - %s' % (self.reference, self.product_id.name) or self.product_id.name,
            'warehouse_id': self.location_dest_id.warehouse_id.id
        }

    def product_price_update_before_done(self, forced_qty=None):
        res = super(WarehouseStockMove,
                    self).product_price_update_before_done()
        # * Softhealer code Start *

        #  Below code is used to compute the quantity and create/update the price based
        #  on warehouse in the product

        # * Softhealer code end *
        if self:
            tmpl_dict = defaultdict(lambda: 0.0)
            for move in self.filtered(lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'):
                group_quantity = self.get_quantity_from_valuation(
                    move.product_id.id, self.location_dest_id.warehouse_id.id) + tmpl_dict[move.product_id.id]
                valued_move_lines = move._get_in_move_lines()
                qty_done = 0
                for valued_move_line in valued_move_lines:
                    qty_done += valued_move_line.product_uom_id._compute_quantity(
                        valued_move_line.quantity, move.product_id.uom_id)
                    # qty_done += valued_move_line.product_uom_id._compute_quantity(
                    #     valued_move_line.qty_done, move.product_id.uom_id)
                qty = forced_qty or qty_done
                amount_unit = 0.0
                warehouse = False
                warehouse = move.product_id.with_company(move.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == self.location_dest_id.warehouse_id.id)
                if warehouse:
                    amount_unit = warehouse.cost
                    new_std_price = ((amount_unit * group_quantity) +
                                     (move._get_price_unit() * qty)) / (group_quantity + qty)
                    warehouse.write({'cost': new_std_price})
                else:
                    new_std_price = ((amount_unit * group_quantity) +
                                     (move._get_price_unit() * qty)) / (group_quantity + qty)
                    self.env['sh.warehouse.cost'].create({
                        'product_id': move.product_id.id,
                        'warehouse_id': self.location_dest_id.warehouse_id.id,
                        'cost': new_std_price
                    })
                tmpl_dict[move.product_id.id] += qty_done
        return res

    def get_quantity_from_valuation(self, productid, warehouseid):
        # * Softhealer code Start *

        #   New Methpd (accepts the product and warehouse and returns the quantity warehouse wise drom svl)

        # * Softhealer code end *
        company_id = self.env.company.id
        domain = [
            ('product_id', '=', productid),
            ('company_id', '=', company_id),
            ('warehouse_id', '=', warehouseid)
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        groups = self.env['stock.valuation.layer'].read_group(
            domain, ['value:sum', 'quantity:sum'], ['product_id'])
        if groups:
            for group in groups:
                return group['quantity']
        else:
            return 0

    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        # * Softhealer code Start *

        # Passsed warehouse id in _prepare_out_svl_vals

        # * Softhealer code end *
        svl_vals_list = []
        for move in self:            
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_out_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity, move.product_id.uom_id)
                # valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move._prepare_common_svl_vals()
            svl_vals.update(move.product_id._prepare_out_svl_vals(
                forced_quantity or valued_quantity, move.company_id, move.location_id.warehouse_id))
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)       
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
    
    def _get_in_svl_vals(self, forced_quantity):
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines()
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.quantity, move.product_id.uom_id)
                # valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = move.product_id.standard_price
            if move.product_id.cost_method != 'standard':
                unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).

            # Custom Code update cost price as per warehouse rather than product standard price
            # price = move.product_id.warehouse_cost_lines.filtered(
            #         lambda x: x.warehouse_id.id == move.location_dest_id.warehouse_id.id).cost
            # if price:
            #     unit_cost = price
            # Custom Code update cost price as per warehouse rather than product standard price

            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return svl_vals_list

    def _action_done(self, cancel_backorder=False):
        # * Softhealer code Start *

        # Called Super used to create svl when internal transfer is done

        # * Softhealer code end *
        for rec in self:
            if rec.sh_in_replenshment and rec.picking_id.group_id:
                qty = rec.quantity
                amount_unit = 0.0
                warehouse = False
                warehouse = rec.product_id.with_company(rec.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == rec.picking_id.location_dest_id.warehouse_id.id)
                source_picking = self.env['stock.picking'].search([('origin','=',rec.picking_id.group_id.name)])
                source_warehouse = rec.product_id.with_company(rec.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == source_picking.location_id.warehouse_id.id)
                if warehouse:
                    amount_unit = warehouse.cost
                    new_std_price = ((amount_unit * warehouse.sh_onhand_qty) +
                                        (source_warehouse.cost * qty)) / (warehouse.sh_onhand_qty + qty)
                    warehouse.write({'cost': new_std_price})
                elif source_warehouse:
                    source_Warehouse_cost = 0.0
                    if source_warehouse:
                        source_Warehouse_cost = source_warehouse.cost
                    new_std_price = ((amount_unit * warehouse.sh_onhand_qty) +
                                        (source_Warehouse_cost)) / (warehouse.sh_onhand_qty + qty)
                    self.env['sh.warehouse.cost'].create({
                        'product_id': rec.product_id.id,
                        'warehouse_id': rec.picking_id.location_dest_id.warehouse_id.id,
                        'cost': new_std_price
                    })
        res = super(WarehouseStockMove, self)._action_done(cancel_backorder)
        # for rec in self:
        #     if rec.picking_type_id.code == 'internal':
        #         if rec.location_id.warehouse_id.id != rec.location_dest_id.warehouse_id.id:
        #             rec.create_manually_svl_in_out_vals()
        
        return res

    def create_manually_svl_in_out_vals(self):
        # * Softhealer code Start *

        # Update warehouse wise price when internal transfer is made and added in and out svl lines

        # * Softhealer code end *
        tmpl_dict = defaultdict(lambda: 0.0)
        for move in self:
            for lines in move.move_line_ids:
                price = lines.product_id.warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_id.warehouse_id.id).cost
                group_quantity = self.get_quantity_from_valuation(
                    move.product_id.id, move.location_dest_id.warehouse_id.id)
                group_quantity_from = self.get_quantity_from_valuation(
                    move.product_id.id, move.location_id.warehouse_id.id)
                amount_unit = 0.0
                amount_unit_from = 0.0
                warehouse = False
                warehouse_from = False
                warehouse = move.product_id.with_company(move.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_dest_id.warehouse_id.id)
                warehouse_from = move.product_id.with_company(move.company_id).warehouse_cost_lines.filtered(
                    lambda x: x.warehouse_id.id == move.location_id.warehouse_id.id)
                valued_quantity = 0
                valued_quantity = lines.product_uom_id._compute_quantity(
                    lines.quantity, move.product_id.uom_id)
                # valued_quantity = lines.product_uom_id._compute_quantity(
                #     lines.qty_done, move.product_id.uom_id)
                if warehouse_from:
                    amount_unit_from = warehouse_from.cost
                    if group_quantity_from - valued_quantity == 0:
                        new_std_price_from = (
                            (amount_unit_from * group_quantity_from) - (price * valued_quantity))
                    else:
                        new_std_price_from = (
                            (amount_unit_from * group_quantity_from) - (price * valued_quantity)) / (group_quantity_from - valued_quantity)
                    warehouse_from.write({'cost': new_std_price_from})
                if warehouse:
                    amount_unit = warehouse.cost
                    if group_quantity + valued_quantity == 0:
                        new_std_price = (
                            (amount_unit * group_quantity) + (price * valued_quantity))
                    else:
                        new_std_price = (
                            (amount_unit * group_quantity) + (price * valued_quantity)) / (group_quantity + valued_quantity)
                    warehouse.write({'cost': new_std_price})
                else:
                    self.env['sh.warehouse.cost'].create({
                        'product_id': move.product_id.id,
                        'warehouse_id': self.location_dest_id.warehouse_id.id,
                        'cost': price
                    })
                out_vals = {
                    'product_id': lines.product_id.id,
                    'value': price * (-valued_quantity),
                    'unit_cost': price,
                    'quantity': (-valued_quantity),
                }
                out_vals.update(move._prepare_common_svl_vals())
                out_vals.update({
                    'warehouse_id': self.location_id.warehouse_id.id
                })
                self.env['stock.valuation.layer'].sudo().create(out_vals)
                in_vals = {
                    'product_id': lines.product_id.id,
                    'value': price * valued_quantity,
                    'unit_cost': price,
                    'quantity': valued_quantity,
                }
                if lines.product_id.cost_method in ('average', 'fifo'):
                    in_vals['remaining_qty'] = valued_quantity
                in_vals.update(move._prepare_common_svl_vals())
                self.env['stock.valuation.layer'].sudo().create(in_vals)


