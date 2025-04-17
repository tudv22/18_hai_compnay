from odoo import models, fields, api, _
from odoo.exceptions import UserError

MAP_STATE = {
    'draft': 'draft',
    'sent': 'draft',
    'sale': 'sale',
    'cancel': 'cancel'
}

RETURN_STATE = [
    ('draft', 'Draft'),
    ('sale', 'Sale Order Return'),
    ('done', 'Locked'),
    ('cancel', 'Cancelled')
]


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_type = fields.Selection(
        selection_add=[
        ('return', 'Return')
    ],
        ondelete={'return': 'set default'},
        default='sale',
        string='Type'
    )
    x_origin_sale_id = fields.Many2one(
        'sale.order',
        string='Origin sale Order',
        copy=False,
    )
    x_return_sale_ids = fields.One2many(
        'sale.order',
        'x_origin_sale_id',
        string="Return sales",
        copy=False
    )
    x_count_return_sale = fields.Integer(
        compute="_compute_count_return_sale",
        store=True,
        copy=False
    )
    x_origin_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Origin Picking',
        copy=False,
    )
    x_return_state = fields.Selection(
        selection=RETURN_STATE,
        compute='_compute_x_return_state',
        string='Status',
        readonly=True,
        index=True,
        copy=False,
        default='draft',
        tracking=True,
    )
    x_location_id = fields.Many2one(
        comodel_name='stock.location',
        compute='_compute_location_id',
        string='Return Location',
        copy=False,
    )
    x_picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Return to',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('name', 'New') == 'New' or vals.get('name') == '/' or not vals.get('name')) and (
                    vals.get('x_type') == 'return' or self.env.context.get('default_x_type') == 'return'):
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order.return') or '/'
        return super(SaleOrder, self).create(vals_list)

    @api.onchange('x_location_id')
    def _onchange_x_location_id(self):
        if self.x_location_id:
            x_picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', self.x_location_id.warehouse_id.id)
            ], limit=1)
            self.x_picking_type_id = x_picking_type_id

    @api.depends('state', 'x_return_sale_ids', 'x_return_sale_ids.state')
    def _compute_x_return_state(self):
        for order in self:
            if order.x_type == 'return':
                order.x_return_state = MAP_STATE.get(order.state, 'draft')
                continue
            order.x_return_state = False

    @api.depends('x_return_sale_ids', 'x_return_sale_ids.state')
    def _compute_count_return_sale(self):
        for order in self:
            order.x_count_return_sale = len(order.x_return_sale_ids.filtered(lambda sor: sor.state != 'cancel'))

    @api.depends('warehouse_id')
    def _compute_location_id(self):
        for order in self:
            order.x_location_id = order.warehouse_id.lot_stock_id

    def action_confirm(self):
        # Lấy danh sách các giá trị của x_type từ các bản ghi
        x_types = self.mapped('x_type')

        # Kiểm tra nếu cả 'return' và 'sale' đều có trong danh sách x_types
        if 'return' in x_types and 'sale' in x_types:
            raise UserError(_("You cannot process both Sale Orders (SO) and Sale Returns (SOR) together."))

        # Nếu không có 'return' trong x_types, gọi phương thức gốc của lớp cha
        if 'return' not in x_types:
            return super(SaleOrder, self).action_confirm()

        # Xử lý các bản ghi có x_type là 'return'
        for record in self.filtered(lambda l: l.x_type == 'return'):
            super(SaleOrder, record.with_context(x_sale_return_for_picking=record)).action_confirm()

    def action_view_sale_return(self):
        if self.x_return_sale_ids:
            context = {'create': True, 'delete': True, 'edit': True}
            view_id = self.env.ref('a1_sale_return.sale_order_tree_inherit_a1_sale_return').id
            view_form_id = self.env.ref('a1_sale_return.a1_sale_return_form').id
            return {
                'name': _('Sale Return'),
                'view_mode': 'list,form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', self.x_return_sale_ids.ids)],
                'context': context,
                'views': [
                    (view_id, 'list'),
                    (view_form_id, 'form')
                ]
            }

    def action_wizard_sale_order_return(self):
        view_id = self.env.ref('a1_sale_return.sale_return_wizard_form_view').id
        ctx = self.env.context
        ctx = {**ctx, 'default_sale_id': self.id, 'default_location_id': self.warehouse_id.lot_stock_id.id}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Return Wizard'),
            'res_model': 'sale.return.wizard',
            'target': 'new',
            'view_mode': 'form',
            'context': ctx,
            'views': [[view_id, 'form']]
        }

    @api.onchange('x_origin_sale_id')
    def _onchange_x_origin_sale_id(self):
        for record in self:
            if record.x_origin_sale_id:
                record.commitment_date = record.x_origin_sale_id.commitment_date
                record.order_line.unlink()
                if record.x_origin_sale_id.order_line:
                    for line in record.x_origin_sale_id.order_line:
                        vals = line._prepare_sale_order_return_line()
                        record.write({
                            'order_line': [(0, 0, vals)]
                        })
                record.partner_id = record.x_origin_sale_id.partner_id

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if self.env.context.get('filter_x_type', False):
            if hasattr(self, 'x_type'):
                domain += [('x_type', '=', 'sale')]

        if self.env.context.get('filter_partner_id', False):
            partner_id = self.env.context.get('filter_partner_id', False)
            domain += [('partner_id', '=', partner_id)]
        return super()._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        domain = domain or []
        if self.env.context.get('filter_x_type', False):
            if hasattr(self, 'x_type'):
                domain += [('x_type', '=', 'sale')]

        if self.env.context.get('filter_partner_id', False):
            partner_id = self.env.context.get('filter_partner_id', False)
            domain += [('partner_id', '=', partner_id)]
        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                       count_limit=count_limit)

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.x_type == 'return':
            res['move_type'] = 'out_refund'
        return res

    @api.depends('x_origin_sale_id')
    def _depend_x_origin_sale_id(self):
        for record in self:
            if record.x_origin_sale_id:
                record.date_order = record.x_origin_sale_id.date_order


    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self._check_order_lines_match_origin()
        return res

    def _check_order_lines_match_origin(self):
        for record in self:
            if record.x_origin_sale_id:
                origin_line_ids = set(record.x_origin_sale_id.order_line.mapped('product_id.id'))
                current_lines = record.order_line.filtered(lambda l: l.product_id.id not in origin_line_ids)

                if current_lines:
                    product_names = ', '.join(current_lines.mapped('product_id.name'))
                    raise UserError(_(
                        "Existing the following products not in the original purchase order: %s"
                    ) % product_names)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Sale Order'),
            'template': '/a1_sale_return/static/src/xlsx/Template_SOR.xlsx'
        }]

    def action_preview_print_sor(self):
        action = 'a1_sale_return.action_print_sale_order_return'
        url = 'report/pdf/%s/%s' % (action, self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
            'res_id': self.id,
        }
