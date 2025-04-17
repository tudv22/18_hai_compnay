# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError
from odoo.tools import format_datetime, formatLang


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    def _compute_price(self, product, quantity, uom, date, currency=None):
        if not self:
            return product.list_price
        else:
            return super(PricelistItem, self)._compute_price(product, quantity, uom, date, currency)