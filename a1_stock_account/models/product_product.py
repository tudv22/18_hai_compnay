from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _prepare_out_svl_vals(self, quantity, company, warehouse=False):
        res = super()._prepare_out_svl_vals(quantity, company, warehouse)
        check_value_equal_to_zero = self.env.context.get('check_value_equal_to_zero', False)
        if check_value_equal_to_zero:
            company_id = self.env.context.get('force_company', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            currency = company.currency_id
            price = currency.round(res['quantity'] * res['unit_cost'])
            res['value'] = price
        return res

    def _prepare_in_svl_vals(self, quantity, unit_cost):
        res = super()._prepare_in_svl_vals(quantity, unit_cost)
        check_value_equal_to_zero = self.env.context.get('check_value_equal_to_zero', False)
        if check_value_equal_to_zero:
            company_id = self.env.context.get('force_company', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            currency = company.currency_id
            price = currency.round(res['quantity'] * res['unit_cost'])
            res['value'] = price
        return res