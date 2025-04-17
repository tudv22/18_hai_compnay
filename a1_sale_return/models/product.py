# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def get_product_accounts(self, fiscal_pos=None):
        accounts = super().get_product_accounts(fiscal_pos=fiscal_pos)
        if self.env.context.get('return_invoice'):
            if not self.categ_id.x_property_account_return_id:
                raise ValidationError(_("The Refund Account is empty. Please configure it before proceeding."))
            accounts.update({'income': self.categ_id.x_property_account_return_id or False})
        return accounts