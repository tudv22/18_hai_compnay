# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _prepare_cog_return_move_line(self):
        aml_vals_list = []
        expense_account_id = self.company_id.x_diff_cog_return_expense_id
        if not expense_account_id:
            raise UserError(_('Missing different COG return expense account config. '
                              'Please go to Accounting -> configuration -> "different COG return expense account" to select an account.'))
        income_account_id = self.company_id.x_diff_cog_return_income_id
        if not income_account_id:
            raise UserError(_('Missing different COG return income account config. '
                              'Please go to Accounting -> configuration -> "different COG return income account" to select an account.'))
        for line in self:
            line = line.with_company(line.company_id)
            uom = line.product_uom_id or line.product_id.uom_id
            quantity = line.quantity
            if float_is_zero(quantity, precision_rounding=uom.rounding):
                continue
            layers = line._get_valued_in_moves().stock_valuation_layer_ids.filtered(lambda svl: svl.product_id == line.product_id and not svl.stock_valuation_layer_id)
            if not layers:
                continue

            aml_gross_price_unit = abs(line._get_gross_unit_price())
            # convert from aml currency to company currency
            aml_price_unit = aml_gross_price_unit / line.currency_rate
            product_uom = line.product_id.uom_id
            aml_price_unit = line.product_uom_id._compute_price(aml_price_unit, product_uom)
            aml_qty = line.product_uom_id._compute_quantity(line.quantity, product_uom)
            layer_price_unit = abs(layers[0]._get_layer_price_unit())
            unit_valuation_difference = layer_price_unit - aml_price_unit
            if not unit_valuation_difference:
                continue
            unit_valuation_difference_curr = unit_valuation_difference * line.currency_rate
            unit_valuation_difference_curr = product_uom._compute_price(unit_valuation_difference_curr, line.product_uom_id)
            account_id = expense_account_id if unit_valuation_difference_curr > 0 else income_account_id
            aml_vals_list += line._prepare_pdiff_cog_aml_vals(aml_qty, unit_valuation_difference_curr, account_id)
        return aml_vals_list

    def _prepare_pdiff_cog_aml_vals(self, aml_qty, unit_valuation_difference_curr, account_id):
        self.ensure_one()
        balance = self.company_id.currency_id.round((aml_qty * unit_valuation_difference_curr) / self.currency_rate)
        product_account_id = self.product_id.categ_id.with_company(self.company_id).property_stock_account_input_categ_id
        debit_account_id = account_id.id if balance >= 0 else product_account_id.id
        credit_account_id = account_id.id if balance < 0 else product_account_id.id
        vals_list = [
            (0, 0, {
                'name': self.product_id.display_name,
                'partner_id': self.partner_id.id or self.move_id.commercial_partner_id.id,
                'currency_id': self.currency_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'debit': abs(balance),
                'account_id': debit_account_id,
                'purchase_line_id': self.purchase_line_id.id,
                'display_type': 'cogs',
            }),
            (0, 0, {
                'name': self.product_id.display_name,
                'partner_id': self.partner_id.id or self.move_id.commercial_partner_id.id,
                'currency_id': self.currency_id.id,
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'credit': abs(balance),
                'account_id': credit_account_id,
                'purchase_line_id': self.purchase_line_id.id,
                'display_type': 'cogs',
            })
        ]
        return vals_list