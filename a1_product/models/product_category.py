from odoo import _, api, fields, models
from odoo.exceptions import UserError
import re


class ProductCategory(models.Model):
    _inherit = 'product.category'

    x_attribute_config_ids = fields.One2many(
        comodel_name='product.category.attribute',
        inverse_name='product_category_id',
        string="Attribute config"
    )
    x_property_account_return_id = fields.Many2one(
        'account.account',
        string='Refund Account',
        company_dependent=True
    )
    x_internal_voucher_income_id = fields.Many2one(
        comodel_name='account.account',
        string='Internal Voucher Income Account',
        company_dependent=True,
        check_company=True,
    ) # Tài khoản doanh thu voucher nội bộ
    x_internal_voucher_outgoing_warehouse_cost_id = fields.Many2one(
        comodel_name='account.account',
        string='Internal voucher Outgoing Warehouse Cost Account',
        company_dependent=True,
        check_company=True,
    ) # Tài khoản giá vốn xuất bán nội bộ liên công ty

    @api.onchange('x_attribute_config_ids')
    def _onchange_x_attribute_config_ids(self):
        if self.product_count > 0:
            raise UserError(_("Can not change the attribute when existing product related to current category."))