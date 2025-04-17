# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"
    _description = "Supplier Pricelist"

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Vendor Pricelists'),
            'template': '/a1_product/static/src/xlsx/template_import_product_supplierinfo.xlsx'
        }]