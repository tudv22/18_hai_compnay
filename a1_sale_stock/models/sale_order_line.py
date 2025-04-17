# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_free_qty = fields.Float(
        string="Free quantity",
        compute='_compute_qty_free',
        copy=False
    )

    @api.depends('product_id', 'warehouse_id')
    def _compute_qty_free(self):
        for line in self:
            line.x_free_qty = line.product_id.with_context(warehouse=line.warehouse_id.id).free_qty

    @api.onchange('product_id')
    def _onchange_product_id_qty_free(self):
        if not self.product_id:
            return
        self._compute_qty_free()
