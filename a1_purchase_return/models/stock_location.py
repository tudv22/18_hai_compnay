# Copyright 2018 ForgeFlow (https://www.forgeflow.com)
# @author Jordi Ballester <jordi.ballester@forgeflow.com.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, api


class StockLocation(models.Model):
    _inherit = "stock.location"

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if self.env.context.get('filter_purchase_return', False):
            purchase_id = self.env.context.get('filter_purchase_return', False)
            purchase_id = self.env['purchase.order'].browse(purchase_id)
            if purchase_id.picking_ids:
                domain += ['|', ('return_location', '=', True),
                           ('id', 'in', purchase_id.picking_ids.mapped('location_id').ids)]
            else:
                domain += [('return_location', '=', True)]
        return super()._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        domain = domain or []
        if self.env.context.get('filter_purchase_return', False):
            purchase_id = self.env.context.get('filter_purchase_return', False)
            purchase_id = self.env['purchase.order'].browse(purchase_id)
            if purchase_id.picking_ids:
                domain += ['|', ('return_location', '=', True),
                           ('id', 'in', purchase_id.picking_ids.mapped('location_id').ids)]
            else:
                domain += [('return_location', '=', True)]
        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                       count_limit=count_limit)
