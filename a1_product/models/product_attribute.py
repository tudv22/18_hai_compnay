# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for product attribute'),
            'template': '/a1_product/static/src/xlsx/template_product_attribute.xlsx'
        }]
