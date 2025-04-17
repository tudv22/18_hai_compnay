# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

MAP_STATE = {
    'draft': 'draft',
    'sent': 'draft',
    'to approve': 'to_approve',
    'purchase': 'purchase',
    'done': 'done',
    'cancel': 'cancel'
}


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_type = fields.Selection(
        selection_add=[
        ('return', 'Return')
    ],
        ondelete={'return': 'set default'},
        default='purchase',
        string='Type')
    x_origin_purchase_id = fields.Many2one(
        'purchase.order',
        string='Origin Purchase Order',
    )
    x_return_purchase_ids = fields.One2many(
        'purchase.order',
        'x_origin_purchase_id',
        string="Return Purchases",
        copy=False
    )
    x_count_return_purchase = fields.Integer(
        compute="_compute_count_return_purchase",
        store=True,
        copy=False
    )
    x_origin_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Origin Picking'
    )
    x_return_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To Approve'),
        ('purchase', 'Purchase Order Return'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ],
        compute='_compute_x_return_state',
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
        tracking=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('name', 'New') == 'New' or vals.get('name') == '/' or not vals.get('name')) and (
                    vals.get('x_type') == 'return' or self.env.context.get('default_x_type') == 'return'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.return') or '/'
        return super(PurchaseOrder, self).create(vals_list)

    def _prepare_picking(self):
        vals = super()._prepare_picking()
        if self.x_type == 'return':
            vals.update({
                'picking_type_code': 'outgoing',
                'location_id': self.picking_type_id.default_location_src_id.id,
                'picking_type_id': self.picking_type_id.id,
                'location_dest_id': self.partner_id.property_stock_supplier.id
            })
        return vals

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.x_type == 'return':
            res['move_type'] = 'in_refund'
        return res

    @api.depends('state', 'x_return_purchase_ids', 'x_return_purchase_ids.state')
    def _compute_x_return_state(self):
        for order in self:
            order.x_return_state = MAP_STATE.get(order.state, 'draft')

    @api.depends('x_return_purchase_ids', 'x_return_purchase_ids.state')
    def _compute_count_return_purchase(self):
        for order in self:
            order.x_count_return_purchase = len(order.x_return_purchase_ids.filtered(lambda por: por.state != 'cancel'))

    def button_confirm(self):
        x_types = self.mapped('x_type')
        if 'return' in x_types and 'purchase' in x_types:
            raise UserError(_("You cannot process both Purchase Orders (PO) and Purchase Returns (POR) together."))
        if 'return' not in x_types:
            return super(PurchaseOrder, self).button_confirm()
        self.filtered(lambda order: order.x_type == 'return').write({'state': 'to approve'})

    def action_view_purchase_return(self):
        if self.x_return_purchase_ids:
            context = {'create': True, 'delete': True, 'edit': True}
            view_id = self.env.ref('a1_purchase_return.purchase_order_tree_inherit_a1_purchase_return').id
            view_form_id = self.env.ref('a1_purchase_return.a1_purchase_order_return_form').id
            return {
                'name': _('Purchase Return'),
                'view_mode': 'list,form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', self.x_return_purchase_ids.ids)],
                'context': context,
                'views': [
                    (view_id, 'list'),
                    (view_form_id, 'form')
                ]
            }

    def action_wizard_purchase_order_return(self):
        view_id = self.env.ref('a1_purchase_return.purchase_return_wizard_form_view').id
        ctx = self.env.context
        default_location_id = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
        ctx = {**ctx, 'default_purchase_id': self.id, 'default_location_id': default_location_id.id}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Return Wizard'),
            'res_model': 'purchase.return.wizard',
            'target': 'new',
            'view_mode': 'form',
            'context': ctx,
            'views': [[view_id, 'form']]
        }

    @api.model
    def _get_picking_type(self, company_id):
        if self.env.context.get('default_x_type') == 'return':
            PickingType = self.env['stock.picking.type']
            picking_type = PickingType.search([('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', company_id)])
            if not picking_type:
                picking_type = PickingType.search([('code', '=', 'outgoing'), ('warehouse_id', '=', False)])
            return picking_type[:1]
        return super(PurchaseOrder, self)._get_picking_type(company_id)

    @api.onchange('x_origin_purchase_id')
    def _onchange_x_origin_purchase_id(self):
        for record in self:
            if record.x_origin_purchase_id:
                # related currency and exchange_rate from origin po
                record.currency_id = record.x_origin_purchase_id.currency_id
                record.x_exchange_rate = record.x_origin_purchase_id.x_exchange_rate
                #
                record.order_line.unlink()
                if record.x_origin_purchase_id.order_line:
                    for line in record.x_origin_purchase_id.order_line:
                        vals = line._prepare_purchase_order_return_line()
                        record.write({
                            'order_line': [(0, 0, vals)]
                        })
                record.partner_id = record.x_origin_purchase_id.partner_id

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if self.env.context.get('filter_partner_id', False):
            partner_id = self.env.context.get('filter_partner_id', False)
            domain += [('partner_id', '=', partner_id)]
        return super()._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        domain = domain or []
        if self.env.context.get('filter_partner_id', False):
            partner_id = self.env.context.get('filter_partner_id', False)
            domain += [('partner_id', '=', partner_id)]
        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                       count_limit=count_limit)

    @api.depends('order_line.move_ids.picking_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = order.order_line.move_ids.picking_id

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        self._check_order_lines_match_origin()
        return res

    def _check_order_lines_match_origin(self):
        for record in self:
            if record.x_origin_purchase_id:
                origin_line_ids = set(record.x_origin_purchase_id.order_line.mapped('product_id.id'))
                current_lines = record.order_line.filtered(lambda l: l.product_id.id not in origin_line_ids)

                if current_lines:
                    product_names = ', '.join(current_lines.mapped('product_id.name'))
                    raise UserError(_(
                        "Existing the following products not in the original purchase order: %s"
                    ) % product_names)

    def _message_track(self, tracked_fields, initial):
        """ Kiểm tra nếu x_types là 'return' hay 'purchase' thì không ghi log tracking tương ứng """
        self.ensure_one()
        if isinstance(tracked_fields, set):
            tracked_fields = {field_name: self._fields[field_name] for field_name in tracked_fields}
        x_types = self.mapped('x_type')
        if 'x_return_state' in tracked_fields and 'return' in x_types:
            tracked_fields = {k: v for k, v in tracked_fields.items() if k == 'x_return_state'}
        elif 'state' in tracked_fields and 'purchase' in x_types:
            tracked_fields = {k: v for k, v in tracked_fields.items() if k == 'state'}
        else:
            return {}
        return super(PurchaseOrder, self)._message_track(tracked_fields, initial)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for POR'),
            'template': '/a1_purchase_return/static/src/xlsx/template_import_por.xlsx'
        }]

    def action_preview_print_return(self):
        action = 'a1_purchase_return.action_print_purchase_return'
        url = 'report/pdf/%s/%s' % (action, self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
            'res_id': self.id,
        }