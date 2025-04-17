# -*- coding: utf-8 -*-
{
    "name": "A1 Sale Stock",
    'category': 'HAI Custom Module',
    'description': """
        Quản lý hàng bán kho
    """,
    'author': 'Dương Tú',
    "version": "1.0",
    'license': 'LGPL-3',
    "depends": [
        'sale_stock',
        'a1_sale',
        'a1_stock',
    ],
    "data": [
        'views/account_move_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
}