# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values):
        res = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values)
        x_sale_return_for_picking = self.env.context.get('x_sale_return_for_picking', False)
        if x_sale_return_for_picking:
            location_id = res['location_id']
            location_dest_id = res['location_final_id']
            res.update({
                'date': x_sale_return_for_picking.date_order,
                'date_deadline': x_sale_return_for_picking.date_order,
                'location_id': location_dest_id,
                'location_dest_id': location_id,
                'picking_type_id': x_sale_return_for_picking.warehouse_id.in_type_id.id,
                'to_refund': True,
            })
        return res