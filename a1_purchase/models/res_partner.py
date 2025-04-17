# -*- coding: utf-8 -*-

from odoo import api, models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        domain = domain or []
        if self.env.context.get('filter_x_partnership_po', False):
            domain += [('x_partnership', 'in', ('vendor', 'both'))]
        return super()._name_search(name, domain, operator, limit, order)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        domain = domain or []
        if self.env.context.get('filter_x_partnership_po', False):
            domain += [('x_partnership', 'in', ('vendor', 'both'))]
        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                       count_limit=count_limit)