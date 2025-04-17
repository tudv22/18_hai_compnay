# -*- coding: utf-8 -*-
from odoo import models, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        move = super(StockMove, self).create(vals)
        if move.purchase_line_id:  # Nếu có liên kết với đơn mua hàng
            move.price_unit = move.purchase_line_id.price_unit
        return move

    def _is_purchase_return(self):
        if self.purchase_line_id and self.purchase_line_id.order_id.x_type == 'return':
            return False
        return super()._is_purchase_return()
