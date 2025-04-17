# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendor',
        related='order_id.partner_id',
    )
    x_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Buyer',
        related='order_id.user_id',
    )
    x_default_code = fields.Char(
        string='Product Default Code',
        related='product_id.default_code',
    )
    x_origin = fields.Char(
        string='PO Origin',
        related='order_id.origin',
    )

    @api.onchange('product_id')
    def x_onchange_product_id_for_unit_price(self):
        for record in self:
            if record.price_unit == 0.0 and record.product_id:
                record.price_unit = record.product_id._select_seller(quantity=record.product_qty).price

    @api.depends('product_qty', 'product_uom', 'company_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        return super(PurchaseOrderLine, self.with_context(x_exchange_rate=1/self[0].order_id.x_exchange_rate))._compute_price_unit_and_date_planned_and_name()