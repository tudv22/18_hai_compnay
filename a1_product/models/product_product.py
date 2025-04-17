# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    default_code = fields.Char(
        string='Internal Reference',
        index=True,
        tracking=True
    )
    barcode = fields.Char(
        'Barcode',
        copy=False,
        index='btree_not_null',
        tracking=True,
        help="International Article Number used for product identification."
    )
    x_old_code = fields.Char(
        string='Old code',
        copy=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        # self._update_barcode_create(vals_list)
        res = super(ProductProduct, self).create(vals_list)
        res.with_context(default_code_from_create=True)._generate_default_code()
        return res

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if 'default_code' in vals and not self.env.context.get('default_code_from_create', False):
            self._check_unique_default_code()
        return res

    def _check_unique_default_code(self):
        list_default_code = self._get_all_default_code()
        for product in self:
            if product.default_code in list_default_code:
                raise ValidationError(_("Default code '%s' already existed. Try again!") % product.default_code)

    def _generate_default_code(self):
        list_default_code = self._get_all_default_code()
        for product in self:
            if product.type != 'consu':
                continue
            default_code = product._get_default_code() or product.default_code
            if default_code in list_default_code:
                raise ValidationError(_("Default code '%s' already existed. Try again!") % default_code)
            product.default_code = default_code

    def _update_barcode_create(self, vals_list):
        for val in vals_list:
            barcode = self._get_barcode()
            val.update({
                'barcode': barcode
            })

    def _get_all_default_code(self):
        query = """
            SELECT default_code
                FROM product_product
            WHERE default_code IS NOT NULL
        """
        if self.env.context.get('default_code_from_create'):
            query += f""" AND id not in {tuple(self.ids + [0])}"""
        self._cr.execute(query)
        results = self._cr.dictfetchall()
        list_default_code = [x['default_code'] for x in results]
        return list_default_code

    def _get_default_code(self):
        default_code = ''

        # contents = []
        # # Add non-optional attributes to the default code
        # for attr in ['x_content_1', 'x_content_2', 'x_content_3', 'x_content_4', 'x_content_5']:
        #     value = getattr(self, attr)
        #     if value:
        #         contents.append(value.replace(" ", ""))
        #         # default_code += value.replace(" ", "")
        # default_code += "-".join(contents)
        # if default_code:
        #     default_code += '.'

        error_messages = []
        attribute_names = []

        # Ensure that all required category attributes are present in the product
        for attribute_config_id in self.categ_id.x_attribute_config_ids.sorted(key=lambda x: x.sequence):
            attribute_value = self.product_template_attribute_value_ids.filtered(
                lambda x: x.attribute_id == attribute_config_id.product_attribute_id)
            if not attribute_value:
                error_messages.append(attribute_config_id.product_attribute_id.name)
            else:
                attribute_names.append(attribute_value.name.replace(" ", ""))
        default_code += "-".join(attribute_names)

        # Check for extra attributes that are not configured in the category
        if not error_messages:
            extra_attributes = self.product_template_attribute_value_ids.filtered(
                lambda x: x.attribute_id not in self.categ_id.x_attribute_config_ids.product_attribute_id)
            if extra_attributes:
                error_messages = extra_attributes.attribute_id.mapped('name')

        # Raise error if there are any mismatches
        if error_messages and not self.env.context.get('install_mode'):
            raise UserError(
                _('Product attribute config in product category and product do not match: %s. Please check again!',
                  ', '.join(error_messages)))

        return default_code or "DEFAULT_%s" % self.id

    def action_regenerate_default_code(self):
        self.with_context(default_code_from_create=True)._generate_default_code()

    def _generate_barcode(self):
        for product in self:
            if product.barcode:
                continue
            barcode = self.env['ir.sequence'].next_by_code('product.barcode')
            if len(barcode) != 12:
                continue
            product.barcode = self.generate_ean13(barcode)

    def _get_barcode(self):
        barcode = self.env['ir.sequence'].next_by_code('product.barcode')
        if len(barcode) != 12:
            return ''
        return self.generate_ean13(barcode)

    def generate_ean13(self, barcode):
        # Convert the 12-digit string to a list of integers
        digits = list(map(int, barcode))

        # Calculate the sum of the digits in odd positions and multiply by 3
        sum_odd_positions = sum(digits[i] for i in range(0, 12, 2)) * 3

        # Calculate the sum of the digits in even positions
        sum_even_positions = sum(digits[i] for i in range(1, 12, 2))

        # Calculate the total sum
        total_sum = sum_odd_positions + sum_even_positions

        # Determine the check digit
        check_digit = (10 - (total_sum % 10)) % 10

        # Append the check digit to the original 12 digits to form the EAN-13 barcode
        ean13 = barcode + str(check_digit)

        return ean13