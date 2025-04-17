# -*- coding: utf-8 -*-

from odoo import api, Command, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_property_tax_payment_substitute_account_id = fields.Many2one(
        'account.account',
        company_dependent=True,
        string="Tax payment substitute account",
        tracking=True
    )
