# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    x_transfer_request_line_id = fields.Many2one(
        'stock.transfer.request.line',
        string='Stock Transfer Request Line',
        ondelete='cascade'
    )

    def _get_in_move_lines(self):
        if self.x_transfer_request_line_id and self.location_id.usage == 'transit' and self.location_dest_id.usage == 'internal':
            return self.move_line_ids
        return super()._get_in_move_lines()

    def _get_out_move_lines(self):
        if self.x_transfer_request_line_id and self.location_id.usage == 'internal' and self.location_dest_id.usage == 'transit':
            return self.move_line_ids
        return super()._get_out_move_lines()

    def _get_dest_account(self, accounts_data):
        if self.x_transfer_request_line_id and self.location_id.usage == 'internal' and self.location_dest_id.usage == 'transit':
            return self._get_src_account(accounts_data)
        return super()._get_dest_account(accounts_data)

    def _search_picking_for_assignation(self):
        if self.x_transfer_request_line_id:
            return False
        return super()._search_picking_for_assignation()

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        if self.x_transfer_request_line_id:
            vals.update({
                'x_stock_transfer_request_id': self.x_transfer_request_line_id.request_id[0].id,
                'origin': self.move_orig_ids.picking_id[0].name,
            })
        return vals

    def _action_assign(self, force_qty=False):
        if self.env.context.get('skip_assign_move_a1_id', False):
            self = self.filtered(lambda move: move.id not in self.env.context.get('skip_assign_move_a1_id', False))
        return super(StockMove, self)._action_assign(force_qty=force_qty)

    def _get_price_unit(self):
        res = super(StockMove, self)._get_price_unit()
        if self.x_transfer_request_line_id:
            warehouse = self.x_transfer_request_line_id.location_id.warehouse_id
            unit_cost = self.product_id.warehouse_cost_lines.filtered(lambda x: x.warehouse_id.id == warehouse.id).cost
            return unit_cost
        return res