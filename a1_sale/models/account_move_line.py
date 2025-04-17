from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_account_id(self):
        res = super()._compute_account_id()
        for line in self:
            if line.product_id.x_is_voucher and line.move_id.partner_id.x_is_internal_partner and line.balance <= 0 and line.product_id and line.move_id.move_type == 'out_invoice':
                voucher_income_account = line.product_id.categ_id.x_internal_voucher_income_id
                if not voucher_income_account:
                    raise UserError(_('Please set Internal Voucher Income Account for product category %s of company %s') % line.product_id.categ_id.name, line.move_id.company_id.name)
                else:
                    line.account_id = voucher_income_account
        return res