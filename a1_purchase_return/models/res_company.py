# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    x_diff_cog_return_expense_id = fields.Many2one(
        'account.account',
        string='Different COG vendor return – expense account',
        check_company=True
    )
    x_diff_cog_return_income_id = fields.Many2one(
        'account.account',
        string='Different COG vendor return – income account',
        check_company=True
    )