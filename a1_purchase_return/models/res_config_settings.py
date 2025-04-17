# -*- coding: utf-8 -*-
from odoo import _, api, fields, models



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    x_diff_cog_return_expense_id = fields.Many2one(
        'account.account',
        string='Different COG vendor return – expense account',
        related='company_id.x_diff_cog_return_expense_id',
        readonly=False,
        check_company=True
    )
    x_diff_cog_return_income_id = fields.Many2one(
        'account.account',
        string='Different COG vendor return – income account',
        related='company_id.x_diff_cog_return_income_id',
        readonly=False,
        check_company=True
    )