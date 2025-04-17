from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SaleReturnWizard(models.TransientModel):
    _name = "sale.return.wizard"
    _description = "Sale Return Wizard"

    sale_id = fields.Many2one(
        comodel_name='sale.order',
        string='sale Order',
        required=True
    )
    return_line_ids = fields.One2many(
        comodel_name='sale.return.line.wizard',
        inverse_name='wizard_id',
        string='Lines'
    )
    partner_id = fields.Many2one(related='sale_id.partner_id', string='Customer')
    selected_all = fields.Boolean(string='Selected all')
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Return Location',
    )
    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Return to')
    origin_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
    )
    total_remaining_qty = fields.Float(
        compute='_compute_total_remaining_qty',
    )
    has_selected_lines = fields.Boolean(
        string="Has Selected Lines",
        compute="_compute_has_selected_lines",
        store=False)

    @api.depends('return_line_ids.is_selected', 'return_line_ids.remaining_qty')
    def _compute_total_remaining_qty(self):
        for wizard in self:
            total_qty = 0
            for line in wizard.return_line_ids:
                if line.is_selected:
                    total_qty += line.remaining_qty
            wizard.total_remaining_qty = total_qty

    @api.depends('return_line_ids.is_selected')
    def _compute_has_selected_lines(self):
        for wizard in self:
            wizard.has_selected_lines = any(line.is_selected for line in wizard.return_line_ids)

    @api.onchange('selected_all')
    def _onchange_selected_all(self):
        self.return_line_ids.write({'is_selected': self.selected_all})

    @api.onchange('sale_id')
    def _onchange_sale_id(self):
        self.ensure_one()
        if self.sale_id:
            self.return_line_ids = [(5, 0, 0)]
            for line in self.sale_id.order_line:
                self.return_line_ids |= self.return_line_ids.new(
                    self._get_return_line_vals(line)
                )

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', self.location_id.warehouse_id.id)
            ], limit=1)
            self.picking_type_id = picking_type_id

    def _get_return_line_vals(self, line):
        return {
            'product_id': line.product_id.id,
            'uom_id': line.product_uom.id,
            'delivered_qty': line.qty_delivered,
            'returned_qty': line.x_returned_qty,
            'remaining_qty': line.qty_delivered - line.x_returned_qty,
            'return_qty': 0,
            'sale_line_id': line.id,
        }

    def button_create_return(self):
        self.ensure_one()
        return_line_ids = self.return_line_ids.filtered('is_selected')
        if not return_line_ids:
            raise UserError(_("Please select at least one line to return."))
        line_vals = []
        for return_line_id in return_line_ids:
            if return_line_id.return_qty > return_line_id.remaining_qty:
                raise UserError(
                    f"Số lượng trả không thể vượt quá số lượng còn lại cho sản phẩm {return_line_id.product_id.name}.")
            if return_line_id.return_qty <= 0:
                raise UserError(
                    f"Số lượng trả phải lớn hơn 0 cho sản phẩm {return_line_id.product_id.name}.")
            if return_line_id.return_qty > 0:
                line_vals.append((0, 0, self._prepare_sale_line_default_values(return_line_id)))
        if not line_vals:
            raise UserError(_("Please enter quantity to return."))
        sale_vals = self._prepare_sale_default_values(line_vals)
        sale = self.env['sale.order'].create(sale_vals)
        ctx = dict(self.env.context)
        return {
            'name': _('Returned sale'),
            'view_mode': 'form,list',
            'res_model': 'sale.order',
            'res_id': sale.id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'views': [(self.env.ref('a1_sale_return.a1_sale_return_form').id, "form")],
        }

    def _prepare_sale_default_values(self, line_vals):
        vals = {
            'x_type': 'return',
            'x_origin_sale_id': self.sale_id.id,
            'partner_id': self.sale_id.partner_id.id,
            'currency_id': self.sale_id.currency_id.id,
            'x_exchange_rate': self.sale_id.x_exchange_rate,
            'x_origin_picking_id': self.origin_picking_id.id,
            'commitment_date': self.sale_id.date_order,
            'warehouse_id': self.location_id.warehouse_id.id,
            'order_line': line_vals,
            'state': 'draft',
            'x_location_id': self.location_id.id,
        }
        return vals

    def _prepare_sale_line_default_values(self, return_line):
        vals = {
            'product_id': return_line.product_id.id,
            'name': return_line.product_id.name,
            'product_uom': return_line.uom_id.id,
            'product_uom_qty': return_line.return_qty,
            'price_unit': return_line.sale_line_id.price_unit,
            'x_origin_sale_line_id': return_line.sale_line_id.id,
            'tax_id': [(6, 0, return_line.sale_line_id.tax_id.ids)],
            'discount': return_line.sale_line_id.discount,
        }
        return vals


class SaleReturnLineWizard(models.TransientModel):
    _name = "sale.return.line.wizard"
    _description = 'Sale Return Wizard Line'

    wizard_id = fields.Many2one('sale.return.wizard', string="Sale Return Wizard")
    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', '=', product_id)]")
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    delivered_qty = fields.Float(string="Delivered Quantity", required=True)
    returned_qty = fields.Float(string="Returned Quantity")
    remaining_qty = fields.Float(string="Remaining Quantity")
    return_qty = fields.Float(string="Quantity")
    sale_line_id = fields.Many2one('sale.order.line', string="Sale Order Line")
    is_selected = fields.Boolean(string='Selected')