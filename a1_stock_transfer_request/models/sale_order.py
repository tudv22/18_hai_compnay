# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_stock_transfer_request_id = fields.Many2one(
        string='Stock Transfer Request',
        related='auto_purchase_order_id.x_stock_transfer_request_id',
        copy=False,
    )