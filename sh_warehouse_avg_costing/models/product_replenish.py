# -*- coding: utf-8 -*-
from odoo import models,_

from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class ProductReplenishs(models.TransientModel):
    _inherit = 'product.replenish'

    def launch_replenishment(self):
        if not self.route_id:
            raise UserError(_("You need to select a route to replenish your products"))
        uom_reference = self.product_id.uom_id
        self.quantity = self.product_uom_id._compute_quantity(self.quantity, uom_reference, rounding_method='HALF-UP')
        try:
            now = self.env.cr.now()
            self.env['procurement.group'].with_context(clean_context(self.env.context)).run([
                self.env['procurement.group'].Procurement(
                    self.product_id,
                    self.quantity,
                    uom_reference,
                    self.warehouse_id.lot_stock_id,  # Location
                    _("Manual Replenishment"),  # Name
                    _("Manual Replenishment"),  # Origin
                    self.warehouse_id.company_id,
                    self._prepare_run_values()  # Values
                )
            ])
            move = self._get_record_to_notify(now)
            if move._name == 'stock.move':
                move.write({
                    'sh_in_replenshment' : True
                })
            notification = self._get_replenishment_order_notification(move)
            act_window_close = {
                'type': 'ir.actions.act_window_close',
                'infos': {'done': True},
            }
            if notification:
                notification['params']['next'] = act_window_close
                return notification
            return act_window_close
        except UserError as error:
            raise UserError(error)