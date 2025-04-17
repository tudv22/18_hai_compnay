# -*- coding: utf-8
from odoo import models, _, fields, api


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    x_select_all = fields.Boolean(
        string='Select All',
        default=False,
    )
    x_has_purchase_sale_order = fields.Boolean(
        string='Has PO/SO',
        compute='_compute_x_has_purchase_sale_order',
    )

    @api.depends('picking_id.purchase_id', 'picking_id.sale_id')
    def _compute_x_has_purchase_sale_order(self):
        for record in self:
            if (record.picking_id.purchase_id
                    or record.picking_id.sale_id
                    or record.picking_id.move_ids.move_orig_ids.purchase_line_id):
                record.x_has_purchase_sale_order = True
            else:
                record.x_has_purchase_sale_order = False

    @api.onchange('x_select_all')
    def _onchange_x_select_all(self):
        self.product_return_moves.write({'x_is_selected': self.x_select_all})




class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    x_is_selected = fields.Boolean(string='Selected')

    x_remaining_qty = fields.Float(
        string="Khả dụng",
        compute='_compute_x_remaining_qty'
    )

    @api.depends('move_id.quantity', 'move_id.state')
    def _compute_x_remaining_qty(self):
        for record in self:
            if record.move_id.state == 'done':
                record.x_remaining_qty = record.move_id.quantity
            else:
                record.x_remaining_qty = 0