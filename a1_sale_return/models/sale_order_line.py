# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_returned_qty = fields.Float(
        string="Returned Quantity",
        compute='_compute_returned_qty',
        store=True
    )
    x_origin_sale_line_id = fields.Many2one(
        comodel_name='sale.order.line',
        string='Origin Sale Order Line'
    )
    x_sale_returned_line_ids = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='x_origin_sale_line_id',
        string="Return Lines",
        readonly=True, copy=False
    )

    @api.depends('x_sale_returned_line_ids', 'x_sale_returned_line_ids.product_uom_qty',
                 'x_sale_returned_line_ids.order_id.state')
    def _compute_returned_qty(self):
        for line in self:
            returned_qty = 0
            for returned_line in line.x_sale_returned_line_ids:
                if returned_line.order_id.state != 'cancel':
                    returned_qty += returned_line.product_uom_qty
            line.x_returned_qty = returned_qty

    def _prepare_sale_order_return_line(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.name,
            'product_uom_qty': self.product_qty,
            'qty_delivered': self.qty_delivered,
            'qty_invoiced': self.product_qty,
            'price_unit': self.price_unit,
            'tax_id': [(6, 0, self.tax_id.ids)],
            'price_subtotal': self.price_subtotal,
            'price_total': self.price_total,
            'discount': self.discount,
        }

    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.quantity', 'move_ids.product_uom')
    def _compute_qty_delivered(self):
        res = super(SaleOrderLine, self)._compute_qty_delivered()
        for record in self.filtered(lambda l: l.order_id.x_type == 'return'):
            record.qty_delivered = abs(record.qty_delivered)
        return res

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity')
    def _compute_qty_invoiced(self):
        res = super(SaleOrderLine, self)._compute_qty_invoiced()
        for line in self.filtered(lambda l: l.order_id.x_type == 'return'):
            qty_invoiced = 0.0
            for invoice_line in line._get_invoice_lines():
                if invoice_line.move_id.state != 'cancel' or invoice_line.move_id.payment_state == 'invoicing_legacy':
                    if invoice_line.move_id.move_type == 'out_refund':
                        qty_invoiced += invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
            line.qty_invoiced = qty_invoiced
        return res