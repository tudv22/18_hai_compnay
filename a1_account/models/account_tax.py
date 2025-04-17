# coding: utf-8
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    x_tax_authority_id = fields.Many2one(
        comodel_name='res.partner',
        string='Tax Authority'
    )