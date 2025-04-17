# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import fields, models
from odoo.tools.misc import format_datetime

class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def open_at_date(self):
        # * Softhealer code Start *

        #  passed warehouse id in the domain when checking report of stock valuation

        # * Softhealer code end *

        active_model = self.env.context.get('active_model')
        if active_model == 'stock.valuation.layer':
            action = self.env["ir.actions.actions"]._for_xml_id( "stock_account.stock_valuation_layer_action")
            action['domain'] = [('create_date', '<=', self.inventory_datetime), ('product_id.type', '=', 'consu')]
            if self.warehouse_id:
                action['domain'] = [('create_date', '<=', self.inventory_datetime), (
                    'product_id.type', '=', 'consu'), ('warehouse_id', '=', self.warehouse_id.id)]
            action['display_name'] = format_datetime(self.env, self.inventory_datetime)
            return action

        return super(StockQuantityHistory, self).open_at_date()