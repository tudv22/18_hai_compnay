# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_from_stock_transfer_request = fields.Boolean(
        compute='_compute_x_from_stock_transfer_request',
        string='From stock transfer request'
    )

    @api.depends('line_ids.purchase_line_id')
    def _compute_x_from_stock_transfer_request(self):
        for move in self:
            purchase_orders = move.mapped("line_ids.purchase_line_id.order_id")
            move.x_from_stock_transfer_request = any(purchase_orders.mapped("x_stock_transfer_request_id"))
