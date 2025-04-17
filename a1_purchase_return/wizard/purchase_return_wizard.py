from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseReturnWizard(models.TransientModel):
    _name = "purchase.return.wizard"
    _description = "Purchase Return Wizard"

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase Order',
        required=True
    )
    return_line_ids = fields.One2many(
        comodel_name='purchase.return.line.wizard',
        inverse_name='wizard_id',
        string='Lines'
    )
    company_id = fields.Many2one(related='purchase_id.company_id', string='Company')
    selected_all = fields.Boolean(string='Selected all')
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Return Location',
    )
    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Picking type')
    origin_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
    )

    @api.onchange('selected_all')
    def _onchange_selected_all(self):
        self.return_line_ids.write({'is_selected': self.selected_all})

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id', '=', self.location_id.warehouse_id.id)
            ], limit=1)
            self.picking_type_id = picking_type_id

    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        self.ensure_one()
        if self.purchase_id:
            # self.location_id = self.purchase_id.picking_type_id.return_picking_type_id.default_location_src_id
            self.picking_type_id = self.purchase_id.picking_type_id.return_picking_type_id
            self.return_line_ids = [(5, 0, 0)]
            for line in self.purchase_id.order_line:
                self.return_line_ids |= self.return_line_ids.new({
                    'product_id': line.product_id.id,
                    'uom_id': line.product_uom.id,
                    'received_qty': line.qty_received,
                    'returned_qty': line.x_returned_qty,
                    'remaining_qty': line.qty_received - line.x_returned_qty,
                    'return_qty': 0,
                    'purchase_line_id': line.id,
                })

    def _get_return_line_vals(self, line):
        return {
            'product_id': line.product_id.id,
            'uom_id': line.product_uom.id,
            'received_qty': line.qty_received,
            'returned_qty': 0,
            'remaining_qty': line.qty_received,
            'return_qty': 0,
            'purchase_line_id': line.id,
        }

    def button_create_return(self):
        self.ensure_one()
        return_line_ids = self.return_line_ids.filtered('is_selected')
        if not return_line_ids:
            raise UserError(_("Please select at least one line to return."))
        line_vals = []
        for return_line_id in return_line_ids:
            if return_line_id.return_qty > 0:
                line_vals.append((0, 0, self._prepare_purchase_line_default_values(return_line_id)))
        if not line_vals:
            raise UserError(_("Please enter quantity to return."))
        purchase_vals = self._prepare_purchase_default_values(line_vals)
        purchase = self.env['purchase.order'].create(purchase_vals)
        ctx = dict(self.env.context)
        return {
            'name': _('Returned Purchase'),
            'view_mode': 'form,list',
            'res_model': 'purchase.order',
            'res_id': purchase.id,
            'type': 'ir.actions.act_window',
            'context': ctx,
            'views': [(self.env.ref('a1_purchase_return.a1_purchase_order_return_form').id, "form")],
        }

    def _prepare_purchase_default_values(self, line_vals):
        vals = {
            'x_type': 'return',
            'x_origin_purchase_id': self.purchase_id.id,
            'partner_id': self.purchase_id.partner_id.id,
            'currency_id': self.purchase_id.currency_id.id,
            'x_exchange_rate': self.purchase_id.x_exchange_rate,
            'x_origin_picking_id': self.origin_picking_id.id,
            'order_line': line_vals,
            'picking_type_id': self.picking_type_id.return_picking_type_id.id if self.picking_type_id else self.purchase_id.picking_type_id.return_picking_type_id.id,
            'state': 'draft',
        }
        return vals

    def _prepare_purchase_line_default_values(self, return_line):
        vals = {
            'product_id': return_line.product_id.id,
            'name': return_line.product_id.name,
            'product_uom': return_line.uom_id.id,
            'product_qty': return_line.return_qty,
            'price_unit': return_line.purchase_line_id.price_unit,
            'x_origin_purchase_line_id': return_line.purchase_line_id.id,
            'taxes_id': [(6, 0, return_line.purchase_line_id.taxes_id.ids)],
            'discount': return_line.purchase_line_id.discount,
        }
        return vals


class PurchaseReturnLineWizard(models.TransientModel):
    _name = "purchase.return.line.wizard"
    _description = 'Purchase Return Wizard Line'

    wizard_id = fields.Many2one('purchase.return.wizard', string="Purchase Return Wizard")
    wizard_bill_id = fields.Many2one('purchase.bill.return.wizard', string="Purchase Bill Return Wizard")
    product_id = fields.Many2one('product.product', string="Product", required=True, domain="[('id', '=', product_id)]")
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    received_qty = fields.Float(string="Received Quantity", required=True)
    returned_qty = fields.Float(string="Returned Quantity")
    remaining_qty = fields.Float(string="Remaining Quantity")
    return_qty = fields.Float(string="Quantity")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Purchase Order Line")
    is_selected = fields.Boolean(string='Selected')
