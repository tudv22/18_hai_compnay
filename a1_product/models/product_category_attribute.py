from odoo import models, fields, api

class ProductCategoryAttribute(models.Model):
    _name = 'product.category.attribute'
    _description = 'Product Attribute Config Relation'
    _rec_name = 'product_attribute_id'

    product_category_id = fields.Many2one(
        'product.category',
        string='Product Category',
        ondelete='cascade'
    )
    product_attribute_id = fields.Many2one(
        'product.attribute',
        string='Product Attribute',
        ondelete='cascade'
    )
    sequence = fields.Integer(
        'Sequence',
    )

    _sql_constraints = [
        ('unique_category_attribute', 'unique(product_category_id, product_attribute_id)',
         'Product Category and Attribute must be unique.')
    ]