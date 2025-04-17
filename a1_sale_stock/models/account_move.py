# -*- coding: utf-8 -*-

from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_invoice_address = fields.Char(
        string="Invoice address"
    )