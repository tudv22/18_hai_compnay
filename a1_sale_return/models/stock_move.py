# -*- coding: utf-8 -*-
from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        # Kiểm tra xem nếu move được tạo từ sale order line, sao chép giá trị price_unit
        if 'sale_line_id' in vals:
            sale_order_line = self.env['sale.order.line'].browse(vals['sale_line_id'])
            vals['price_unit'] = sale_order_line.price_unit  # Sao chép price_unit từ sale.order.line

        return super(StockMove, self).create(vals)

    def _is_sale_return(self):
        if self.sale_line_id and self.sale_line_id.order_id.x_type == 'return':
            return False
        return super()._is_sale_return()

    def _prepare_common_svl_vals(self):
        res = super()._prepare_common_svl_vals()
        # Return early if there is no sale or return associated with the picking
        if (not self.picking_id.sale_id and not self.picking_id.return_id) or self.picking_id.sale_id.x_type=='sale':
            return res

        # Handle cases where there is a return or an original picking associated with the sale, base on picking
        if self.picking_id.return_id or self.picking_id.sale_id.x_origin_picking_id:
            if self.picking_id.return_id:
                unit_cost = abs(self.move_orig_ids.stock_valuation_layer_ids[0].value)/self.move_orig_ids.quantity
            else:
                origin_picking_id = self.picking_id.sale_id.x_origin_picking_id
                origin_move = self.sale_line_id.x_origin_sale_line_id.move_ids.filtered(lambda m: m.picking_id == origin_picking_id)
                unit_cost = abs(origin_move.stock_valuation_layer_ids[0].value)/origin_move.quantity
        # Handle cases where the sale is a return base on sale order
        elif self.picking_id.sale_id and self.picking_id.sale_id.x_type == 'return' and not self.picking_id.sale_id.x_origin_picking_id:
            warehouse_cost = self.product_id.get_warehouse_wise_cost(self.location_dest_id.warehouse_id.id)
            unit_cost = warehouse_cost.cost if warehouse_cost else 0
        res.update({
            'value': unit_cost * self.quantity,
            'unit_cost': unit_cost,
        })
        return res