# -*- coding: utf-8 -*-
{
    "name": "Product customization",
    'category': 'HAI Custom Module',
    'description': """
        custom_product
    """,
    'author': 'Dương Tú',
    "version": "1.0",
    'license': 'LGPL-3',
    "depends": [
        'account',
        'product',
    ],
    "data": [
        'security/ir.model.access.csv',
        'data/product_sequence_data.xml',
        'views/product_views.xml',
        'views/product_category_views.xml',
    ]
}
