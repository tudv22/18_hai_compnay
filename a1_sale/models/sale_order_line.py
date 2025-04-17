# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('product_id')
    def _compute_name(self):
        res = super(SaleOrderLine, self)._compute_name()
        for line in self:
            if not line.product_id:
                line.name = " "
        return res

    @api.depends('display_type', 'product_id', 'product_packaging_qty')
    def _compute_product_uom_qty(self):
        res = super(SaleOrderLine, self)._compute_product_uom_qty()
        for line in self:
            if not line.product_id:
                line.product_uom_qty = 0.0
        return res