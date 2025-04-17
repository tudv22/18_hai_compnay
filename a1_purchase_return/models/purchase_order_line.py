# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    x_returned_qty = fields.Float(
        string="Returned Quantity",
        compute='_compute_returned_qty',
        store=True
    )
    x_origin_purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='Origin Purchase Order Line'
    )
    x_purchase_returned_line_ids = fields.One2many(
        'purchase.order.line',
        'x_origin_purchase_line_id',
        string="Return Lines",
        readonly=True,
        copy=False
    )

    @api.depends(
        'x_purchase_returned_line_ids',
        'x_purchase_returned_line_ids.product_qty',
        'x_purchase_returned_line_ids.order_id.state'
    )
    def _compute_returned_qty(self):
        for line in self:
            returned_qty = 0
            for returned_line in line.x_purchase_returned_line_ids:
                if returned_line.order_id.state != 'cancel':
                    returned_qty += returned_line.product_qty
            line.x_returned_qty = returned_qty

    def _prepare_purchase_order_return_line(self):
        self.ensure_one()
        return {
            'product_id': self.product_id.id,
            'name': self.name,
            'product_qty': self.product_qty,
            'product_uom': self.product_uom.id,
            'price_unit': self.price_unit,
            'taxes_id': [(6, 0, self.taxes_id.ids)],
            'price_subtotal': self.price_subtotal,
            'price_total': self.price_total,
        }

    def _prepare_stock_moves(self, picking):
        data = super(PurchaseOrderLine, self)._prepare_stock_moves(picking)
        if self.order_id.x_type == 'return':
            if data:
                for value in data:
                    value.update({
                        'picking_type_id': self.sh_warehouse_id.out_type_id.id,
                        'company_id': self.sh_warehouse_id.company_id.id,
                        'warehouse_id': self.sh_warehouse_id.id,
                        'route_ids': self.sh_warehouse_id and [
                            (6, 0, [x.id for x in self.sh_warehouse_id.route_ids])] or [],
                        'location_id': self.sh_warehouse_id.out_type_id.default_location_src_id.id,
                        'location_dest_id': self.order_id.partner_id.property_stock_supplier.id,
                    })
        return data
