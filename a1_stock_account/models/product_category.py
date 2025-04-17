from odoo import _, api, fields, models
from odoo.exceptions import UserError
import re


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model
    def default_get(self, vals):
        res = super(ProductCategory, self).default_get(vals)
        res['property_cost_method'] = 'average'
        res['property_valuation'] = 'real_time'
        return res