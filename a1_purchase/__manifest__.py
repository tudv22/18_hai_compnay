# -*- coding: utf-8 -*-
{
    "name": "A1 Purchase",
    'category': 'HAI Custom Module',
    "version": "1.0",
    'license': 'LGPL-3',
    'description': """
        Chức năng mua hàng và báo cáo
    """,
    'author': 'Dương Tú',
    "depends": [
        'purchase',
        'purchase_stock',
        'a1_base',
        'a1_stock',
    ],
    "data": [
        'security/ir.model.access.csv',

        'report/print_purchase_order.xml',
        'views/purchase_views.xml',
        'views/purchase_reminder_views.xml',
        'wizard/purchase_order_wizard_view.xml'
    ]
}
