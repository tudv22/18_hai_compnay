# -*- coding: utf-8 -*-
{
    "name": "A1 Sale customization",
    'category': 'HAI Custom Module',
    'description': """
        Chức năng bán hàng và báo cáo
    """,
    'author': 'Dương Tú',
    "version": "1.0",
    'license': 'LGPL-3',
    "depends": [
        'sale_management',
        'hr',
        'a1_product',
        'a1_base',
    ],
    "data": [
        'security/ir.model.access.csv',
        'report/print_sale_order.xml',
        
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',
        'views/sale_order_reminder.xml',
        'wizard/sale_order_wizard_view.xml'
    ]
}
