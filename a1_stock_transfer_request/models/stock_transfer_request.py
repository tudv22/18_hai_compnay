# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date
from collections import defaultdict

STATES = [
    ('draft', 'Draft'),
    ('posted', 'Posted'),
    ('manager_approved', 'Manager approved'),
    ('am_wh_approved', 'AM-Warehouse approved'),
    ('in_transit', 'Trung chuyển'),
    ('done', 'Done'),
    ('reject', 'Reject'),
    ('cancel', 'Cancel')
]

TRANSFER_REQUEST_TYPES = [
    ('internal', 'Internal'),
]

class StockTransferRequest(models.Model):
    _name = 'stock.transfer.request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = 'Stock Transfer Request'
    _check_company_auto = True
    _rec_name = 'name'

    @api.model
    def _update_data_sequence(self):
        # Tạo data cho ir.sequence
        self.create_sequence('transfer request internal-company',
                             'transfer.request.internal.company',
                             'YCĐC-NB')

    def create_sequence(self, sequence_name, code, prefix):
        companies = self.env['res.company'].search([])
        existing_sequences = self.env['ir.sequence'].search([
            ('code', '=', code),
            ('company_id', 'in', companies.ids)
        ])
        existing_codes = {(sequence.company_id.id, sequence.code) for sequence in existing_sequences}
        sequence = [
            {
                'name': sequence_name,
                'code': code,
                'company_id': rec.id,
                'prefix': prefix + '/%(year)s/%(month)s/',
                'number_increment': 5,
                'padding': 5,
                'use_date_range': True,
                'active': True
            } for rec in companies if (rec.id, code) not in existing_codes
        ]
        self.env['ir.sequence'].create(sequence)
    # region field
    name = fields.Char(
        string="Name",
        default="New",
        copy=False
    )
    request_date = fields.Datetime(
        string="Request Date",
        default=lambda self: fields.datetime.now(),
    )
    expected_date = fields.Datetime(
        string='Expected date',
        required=True,
    )
    requester_id = fields.Many2one(
        'res.users',
        string="Requester",
        default=lambda self: self.env.user,
        copy=False,
    )
    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        copy=False,
    )
    priority = fields.Selection([('0','Low'),('1','High')])
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    source_company_id = fields.Many2one(
        'res.company',
        string='Source company'
    )
    state = fields.Selection(
        STATES,
        string="Status",
        default='draft',
        copy=False,
        tracking=True
    )
    transfer_request_type = fields.Selection(
        TRANSFER_REQUEST_TYPES,
        string="Transfer request type",
        default='internal',
        tracking=True
    )
    source_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Source warehouse',
    )
    transfer_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Transfer warehouse',
        required=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        related='transfer_warehouse_id.lot_stock_id',
    )
    dest_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Dest warehouse',
        required=True,
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Location dest',
        related='dest_warehouse_id.lot_stock_id',
    )
    reject_reason = fields.Text(
        string='Reject Reason',
        copy=False,
        tracking=True
    )
    note = fields.Text(
        string='Note',
        tracking=True,
        copy=False
    )
    is_processing = fields.Boolean(
        string='Is processing',
        copy=False,
        default=False
    )
    no_create_einvoice = fields.Boolean(
        string='No create Einvoice',
        copy=False,
        default=False
    )
    description = fields.Text(string='Description')
    import_line_file = fields.Binary(
        attachment=False,
        string='Template Import File'
    )
    import_line_file_name = fields.Char()
    request_line_ids = fields.One2many(
        'stock.transfer.request.line',
        'request_id',
        string='Request line',
        copy=True
    )
    total_request_qty = fields.Float(
        string="Total request quantity",
        default=1,
        compute='_compute_total_quantity',
        store=True,
        copy=False
    )
    total_export_qty = fields.Float(
        string="Total export quantity",
        compute='_compute_total_quantity',
        store=True,
        copy=False
    )
    total_receive_qty = fields.Float(
        string="Total receive quantity",
        compute='_compute_total_quantity',
        store=True,
        copy=False
    )
    purchase_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='x_stock_transfer_request_id',
        string='Purchase order',
        check_company=True
    )
    purchase_order_count = fields.Integer(
        compute="_compute_po_count",
        string='Purchase Order Count'
    )
    picking_ids = fields.One2many(
        comodel_name='stock.picking',
        inverse_name='x_stock_transfer_request_id',
        string='Stock picking',
        copy=False
    )
    picking_out_count = fields.Integer(
        compute='_compute_picking_out_count'
    )
    picking_in_count = fields.Integer(
        compute='_compute_picking_in_count'
    )
    x_hide_am_approve = fields.Boolean(
        compute='_compute_x_hide_am_approve',
        string='Hide Button AM Approve'
    )
    # endregion
    # region onchange
    @api.onchange('requester_id')
    def _onchange_department(self):
        for record in self:
            record.department_id = record.requester_id.department_id
            record.transfer_warehouse_id = record.requester_id.property_warehouse_id

    @api.onchange('transfer_request_type', 'transfer_warehouse_id')
    def onchange_transfer_warehouse_id(self):
        for record in self:
            if record.transfer_request_type == 'internal':
                record.source_company_id = record.transfer_warehouse_id.company_id
                record.source_warehouse_id = record.transfer_warehouse_id

    @api.onchange('location_id')
    def _onchange_location_id(self):
        for record in self:
            for line in record.request_line_ids:
                line.location_id = record.location_id

    @api.onchange('dest_warehouse_id')
    def _onchange_dest_warehouse_id(self):
        for record in self:
            for line in record.request_line_ids:
                line.dest_warehouse_id = record.dest_warehouse_id

    @api.onchange('transfer_warehouse_id')
    def _onchange_transfer_warehouse_id(self):
        for record in self:
            for line in record.request_line_ids:
                line.transfer_warehouse_id = record.transfer_warehouse_id
    # endregion
    # region depend
    def _compute_x_hide_am_approve(self):
        for record in self:
            record.x_hide_am_approve = False

    @api.depends('purchase_ids')
    def _compute_po_count(self):
        for r in self:
            r.purchase_order_count = len(r.purchase_ids)

    @api.depends('request_line_ids.request_qty', 'request_line_ids.export_qty', 'request_line_ids.receive_qty')
    def _compute_total_quantity(self):
        for record in self:
            record.total_request_qty = sum(line.request_qty for line in record.request_line_ids)
            record.total_export_qty = sum(line.export_qty for line in record.request_line_ids)
            record.total_receive_qty = sum(line.receive_qty for line in record.request_line_ids)

    def _compute_picking_out_count(self):
        for record in self:
            record.picking_out_count = len(record.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'transit'))

    def _compute_picking_in_count(self):
        for record in self:
            record.picking_in_count = len(record.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'internal'))
    # endregion
    # region button action
    def action_view_picking_out(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'transit'))

    def action_view_picking_in(self):
        return self._get_action_view_picking(
            self.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'internal'))

    def _get_action_view_picking(self, pickings):
        """
        This function returns an action that display existing picking orders of given purchase order ids.
        When only one found, show the picking immediately.
        """
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')
        if not pickings or len(pickings) > 1:
            result['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = pickings.id
        return result

    def action_view_source_purchase_orders(self):
        self.ensure_one()
        source_orders = self.purchase_ids
        result = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')
        if len(source_orders) > 1:
            result['domain'] = [('id', 'in', source_orders.ids)]
        elif len(source_orders) == 1:
            result['views'] = [(self.env.ref('purchase.purchase_order_form', False).id, 'form')]
            result['res_id'] = source_orders.id
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result
    # endregion
    # region status
    def _check_and_update_state(self):
        for record in self:
            picking_out_ids = record.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'transit')

            # Lấy picking in (những picking có location_dest_id.usage == 'internal')
            picking_in_ids = record.picking_ids.filtered(lambda x: x.location_dest_id.usage == 'internal')

            # Logic: picking out done → tạo picking in → picking in done → hoàn thành

            # Nếu tất cả picking in đã done → Transfer request hoàn thành
            if picking_in_ids and all(picking.state == 'done' for picking in picking_in_ids):
                record.state = 'done'
            # Nếu có picking out done nhưng picking in chưa done → Đang vận chuyển
            elif (picking_out_ids and all(picking.state == 'done' for picking in picking_out_ids) and
                  picking_in_ids and not all(picking.state == 'done' for picking in picking_in_ids)):
                record.state = 'in_transit'
            # Nếu picking out done nhưng chưa có picking in (đang tạo picking in)
            elif (picking_out_ids and all(picking.state == 'done' for picking in picking_out_ids) and
                  not picking_in_ids):
                record.state = 'in_transit'

    def action_draft(self):
        for record in self:
            record.write({
                'state': 'draft'
            })

    def action_manager_approve(self):
        for record in self:
            record.write({
                'state': 'manager_approved'
            })

    def action_cancel(self):
        for record in self:
            record.write({
                'state': 'cancel',
            })

    def action_post(self):
        self.validate_request_line_ids_items()
        for record in self:
            record.write({
                'state': 'posted',
            })

    def _check_approve_state(self):
        err = []
        for record in self:
            if record.state != 'manager_approved':
                err.append(record.name)
        if err:
            raise ValidationError(_('Only Request in Manager approved state can approve!') + "\n" + "\n".join(err))
    # endregion
    @api.model
    def load(self, fields, data):
        self._validate_required_field(fields, data)
        return super(StockTransferRequest, self).load(fields, data)

    def _validate_required_field(self, fields, data):
        if self.env.context.get('import_file', False) and self.env.context.get('default_transfer_request_type', False) == 'inter':
            for line_number, mouse in enumerate(data, start=2):
                if len(mouse) > 0 and mouse[0]:
                    # Check if 'source_company_id' is missing or invalid
                    source_company_id = mouse[fields.index('source_company_id')]
                    if not source_company_id:
                        raise ValidationError(
                            _("Missing required value for Source Company field in line %s", line_number))

                    # Check if 'source_warehouse_id' is missing or invalid
                    source_warehouse_id = mouse[fields.index('source_warehouse_id')]
                    if not source_warehouse_id:
                        raise ValidationError(
                            _("Missing required value for Source Warehouse field in line %s", line_number))

    @api.model_create_multi
    def create(self, vals_list):
        self._update_fields_value_before_create(vals_list)
        return super(StockTransferRequest, self).create(vals_list)

    def _update_fields_value_before_create(self, vals_list):
        for vals in vals_list:
            if self.env.context.get('import_file', False):
                transfer_request_type = self.env.context.get('default_transfer_request_type', False)
                vals['transfer_request_type'] = transfer_request_type
                if transfer_request_type == 'inter':
                    # Update lại giá trị trường Kho nguồn
                    source_company_id = self.env['res.company'].browse(
                        vals.get('source_company_id', False)) if vals.get('source_company_id', False) else False
                    if source_company_id:
                        source_warehouse_id = self.env['stock.warehouse'].sudo().browse(
                            vals.get('source_warehouse_id', False)) if vals.get('source_warehouse_id', False) else False
                        new_warehouse_id = self.env['stock.warehouse'].sudo().search(
                            [('name', '=', source_warehouse_id.name), ('company_id', '=', source_company_id.id)],
                            limit=1)
                        vals.update({
                            'source_warehouse_id': new_warehouse_id.id
                        })
            if vals.get("name", _("New")) == _("New"):
                sequence_code = "transfer.request.inter.company" if vals.get('transfer_request_type',
                                                                             '') == 'inter' else "transfer.request.internal.company"
                vals['name'] = self.env["ir.sequence"].next_by_code(sequence_code)

    def unlink(self):
        for record in self:
            if record.state not in ['draft', 'cancel']:
                message = _("You can only delete transfer requests in 'draft' or 'cancel' state.")
                raise UserError(message)
        return super(StockTransferRequest, self).unlink()

    def action_am_approve(self):
        self._check_approve_state()
        self.sudo()._check_source_company_and_warehouse()
        for record in self:
            record._create_picking_incoming_outgoing()
            record.write({
                'state': 'am_wh_approved',
            })

    def _create_purchase_order_inter_company(self):
        self.ensure_one()
        product_request_quantites = self._get_product_request_total_qty()
        self._validate_available_qty(product_request_quantites)
        purchase_vals = self._prepare_purchase_order_values()
        order_lines = self._prepare_purchase_order_line(product_request_quantites)
        purchase_vals['order_line'] = order_lines
        purchase_id = self.env['purchase.order'].sudo().create(purchase_vals)
        if purchase_id:
            purchase_id.sudo().with_context(sale_warehouse_id=self.source_warehouse_id.id).button_confirm()

    def _validate_available_qty(self, product_request_quantities):
        warehouse_id = self.source_warehouse_id
        error_messages = []
        products = self.env['product.product'].sudo()
        for product_id, total_request_qty in product_request_quantities.items():
            qty_available = products.with_context(warehouse=warehouse_id.id).browse(product_id.id).qty_available
            if total_request_qty > qty_available:
                error_message = f"Sản phẩm {product_id.display_name} không đủ tồn kho tại {warehouse_id.display_name}, vui lòng bổ sung thêm tồn kho."
                error_messages.append(error_message)
        if error_messages:
            raise ValidationError("\n".join(error_messages))

    def _get_product_request_total_qty(self):
        product_request_quantities = defaultdict(float)
        for line in self.request_line_ids:
            product_request_quantities[line.product_id] += line.request_qty
        return dict(product_request_quantities)

    def _prepare_purchase_order_values(self):
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', self.location_id.warehouse_id.id)
        ], limit=1)
        purchase_vals = {
            'partner_id': self.source_company_id.partner_id.id,
            'date_planned': self.request_date,
            'company_id': self.env.company.id,
            'x_stock_transfer_request_id': self.id,
            'picking_type_id': picking_type_id.id
        }
        return purchase_vals

    def _prepare_purchase_order_line(self, product_request_quantites):
        order_lines = []
        message_error = ''
        for product_id, request_qty in product_request_quantites.items():
            seller = product_id._select_seller(
                partner_id=self.source_company_id.partner_id,
                quantity=request_qty,
                date=self.request_date.date() and date.today(),
                uom_id=product_id.uom_id
            )
            if not seller:
                message_error += f'Chưa cấu hình giá nhà cung cấp cho sản phẩm {product_id.display_name}. Không thể tạo đơn mua liên công ty\n'
                continue
            taxes = product_id.supplier_taxes_id.filtered(lambda r: r.company_id == self.env.company)
            order_lines.append((0, 0, {
                'product_id': product_id.id,
                'product_qty': request_qty,
                'taxes_id': [(6, 0, taxes.ids)],
                'price_unit': seller.price,
                'product_uom': product_id.uom_id.id
            }))
        if message_error != '':
            raise ValidationError(message_error)
        return order_lines

    def _create_picking_incoming_outgoing(self):
        picking_data_foreach_location = self._get_picking_data_foreach_location()
        domain = [('usage', '=', 'transit'), ('company_id', '=', self.env.company.id)]
        location_transit_id = self.env['stock.location'].search(domain, limit=1)
        if not location_transit_id:
            raise ValidationError(_('Please active transit location'))
        for key_line, move_vals in picking_data_foreach_location.items():
            self._create_stock_picking_in_out(key_line, location_transit_id, move_vals)

    def _create_stock_picking_in_out(self, key_line, location_transit_id, move_vals):
        location_id, location_dest_id, dest_warehouse_id = key_line.split('-')
        location_id = self.env['stock.location'].browse(int(location_id))
        picking_type_out_id = self.sudo()._get_picking_type(location_id.warehouse_id)
        if not picking_type_out_id:
            raise UserError(
                f"No internal picking type found for warehouse {location_id.warehouse_id.name} (outgoing)"
            )
        picking_out_id = self.sudo()._create_picking_out(picking_type_out_id, location_id, location_transit_id, dest_warehouse_id, move_vals)

    def _create_picking_out(self, picking_type_out_id, location_id, location_transit_id, dest_warehouse_id, move_vals):
        picking_out_val = self._prepare_picking(picking_type_out_id, location_id, location_transit_id, dest_warehouse_id=dest_warehouse_id)
        move_values = self._prepare_stock_move_values(picking_type_out_id, location_id, location_transit_id, move_vals)
        picking_out_val['move_ids'] = move_values
        picking_out_id = self.env['stock.picking'].create(picking_out_val)
        return picking_out_id

    def _create_picking_in(self, location_dest_id, picking_out_id):
        picking_type_in_id = self._get_picking_type(location_dest_id.warehouse_id)
        new_move_ids = self.env['stock.move']
        move_dest_updates = []
        for move in picking_out_id.move_ids:
            new_move_vals = self._prepare_move_copy_values(move, location_dest_id, picking_type_in_id)
            new_move = move.sudo().copy(new_move_vals)
            new_move_ids |= new_move
            move_dest_updates.append((move.id, new_move.id))
        if move_dest_updates:
            write_vals = [(4, new_move_id) for move_id, new_move_id in move_dest_updates]
            picking_out_id.move_ids.write({'move_dest_ids': write_vals})
        new_move_ids._action_confirm()
        return new_move_ids.picking_id

    def _get_picking_type(self, warehouse_id):
        return self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', warehouse_id.id),
        ], limit=1)

    def _get_picking_data_foreach_location(self):
        picking_data_foreach_location = defaultdict(list)
        for line in self.request_line_ids:
            key_line = f'{line.location_id.id}-{line.location_dest_id.id}-{line.dest_warehouse_id.id}'
            move_vals = line._prepare_stock_move_vals()
            picking_data_foreach_location[key_line].append(move_vals)
        return dict(picking_data_foreach_location)

    def _prepare_picking(self, picking_type_id, location_id, location_dest_id, picking_id=False, dest_warehouse_id=False):
        picking_vals = {
            'picking_type_id': picking_type_id.id,
            'date': date.today(),
            'origin': picking_id.name if picking_id else self.name,
            'location_dest_id': location_dest_id.id,
            'location_id': location_id.id,
            'company_id': self.company_id.id,
            'x_stock_transfer_request_id': self.id,
            'state': 'draft',
            'move_ids': []
        }
        if dest_warehouse_id:
            picking_vals['x_destination_warehouse_id'] = dest_warehouse_id
        return picking_vals

    def _prepare_stock_move_values(self, picking_type_id, location_id, location_dest_id, move_vals):
        stock_move_list = move_vals.copy() if move_vals else []
        move_values = [
            (0, 0, {
                **val,
                'picking_type_id': picking_type_id.id,
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id
            })
            for val in stock_move_list
        ]
        return move_values

    def _prepare_move_copy_values(self, move_to_copy, location_dest_id, picking_type_id):
        new_move_vals = {
            'origin': move_to_copy.origin or move_to_copy.picking_id.name or "/",
            'location_id': move_to_copy.location_dest_id.id,
            'location_dest_id': location_dest_id.id,
            'date': move_to_copy.date,
            'date_deadline': move_to_copy.date_deadline,
            'company_id': move_to_copy.company_id.id,
            'picking_id': False,
            'picking_type_id': picking_type_id.id,
            'warehouse_id': location_dest_id.warehouse_id.id,
            'procure_method': 'make_to_order',
            'x_transfer_request_line_id': move_to_copy.x_transfer_request_line_id.id,
        }
        return new_move_vals

    def _check_source_company_and_warehouse(self):
        err = []
        for record in self:
            if record.transfer_request_type == 'inter':
                if not record.source_company_id or not record.source_warehouse_id or not record.expected_date:
                    err.append(record.name)
            else:
                if not record.expected_date:
                    err.append(record.name)
        if err:
            raise ValidationError(_('Source Warehouse or Source Company or Expected date is missing!') + "\n" + "\n".join(err))

    def write(self, vals):
        res = super(StockTransferRequest, self).write(vals)
        if 'request_line_ids' in vals:
            self.validate_request_line_ids_items()
        return res

    def validate_request_line_ids_items(self):
        for record in self:
            validate_dict = {}
            duplicated_items = []
            for line in record.request_line_ids:
                key = (line.product_id.id, line.dest_warehouse_id.id)
                if key in validate_dict:
                    duplicated_items.append((line.product_id.display_name, line.dest_warehouse_id.display_name))
                else:
                    validate_dict[key] = True
            if duplicated_items:
                error_message = '\n'.join(
                    [_("Product %s at warehouse %s") % (product, warehouse) for product, warehouse in
                     duplicated_items]) + '\n' + _('Are duplicated. Please check again!')
                raise ValidationError(error_message)
    # region report
    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for transfer request internal'),
            'template': '/a1_stock_transfer_request/static/src/xlsx/Template_import_YCDC_lien_kho.xlsx'
        }]

    def anna_print_stock_transfer_request(self):
        self.ensure_one().sudo()
        action = 'a1_stock_transfer_request.anna_print_stock_transfer_request'
        url = 'report/pdf/%s/%s' % (action, self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
            'res_id': self.id,
        }
    # endregion