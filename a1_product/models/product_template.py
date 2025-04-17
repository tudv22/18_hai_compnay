# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from decimal import Decimal



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def default_get(self, vals):
        res = super(ProductTemplate, self).default_get(vals)
        res['is_storable'] = True
        return res

    x_is_voucher = fields.Boolean(
        string='Voucher',
        default=False
    )
    x_old_code = fields.Char(
        string='Old code',
        copy=False,
    )
    x_product_size = fields.Char(
        string='Product size',
        help='Product size of the product.'
    )
    x_supplier_price = fields.Float(
        string='Supplier price',
        help='Supplier suggestion\'s price of the product.'
    )

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Name must be unique!')
    ]

    # ------------------------------------------------------
    # CRUD / ORM
    # ------------------------------------------------------

    def action_regenerate_default_code(self):
        for template in self:
            template.product_variant_ids.with_context(default_code_from_create=True)._generate_default_code()

    def _prepare_variant_values(self, combination):
        res = super(ProductTemplate, self)._prepare_variant_values(combination)
        res.update({
            'x_old_code': self.x_old_code,
        })
        return res


    def delete_attributes(self):
        CLV_values = (
                [f"C{num:.2f}" for num in [Decimal(i) / 4 for i in range(33, 61)]] +  # C8.25 - C15.00
                [f"L{num:.2f}" for num in [Decimal(i) / 4 for i in range(17, 25)]] +  # L4.25 - L6.00
                [f"V{num:.2f}" for num in [Decimal(i) / 4 for i in range(33, 61)]]  # V8.25 - V15.00
        )
        attribute_value_ids = self.valid_product_template_attribute_line_ids.value_ids.filtered(lambda x: x.name in CLV_values).ids
        self.valid_product_template_attribute_line_ids.write(
            {
                'value_ids': [(3, rec_id) for rec_id in attribute_value_ids]
            }
        )