# -*- coding: utf-8 -*-
{
    "name": "A1 Account",
    'category': 'HAI Custom Module',
    "version": "1.0",
    'license': 'LGPL-3',
    'description': """
        custom_account
    """,
    'author': 'Dương Tú',
    "depends": [
        'a1_base',
        'account',
        'stock_landed_costs',
    ],
    "data": [
        'data/data_tax_product.xml',
        # 'report/receipt_report_templates.xml',
        # 'views/account_payment_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/account_tax_views.xml',
        'views/product_view.xml',
        'wizard/account_payment_register_views.xml',
    ]
}
