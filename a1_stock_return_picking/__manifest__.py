# -*- coding: utf-8 -*-
{
    'name': "A1 stock return picking",
    'summary': "A1 stock return picking",
    'description': """
        Giao diện trả hàng tại kho
    """,
    'author': 'Dương Tú',
    'category': 'HAI Custom Module',
    'version': '1.0',
    'depends': [
        'purchase_stock',
        'stock',
        'sale_stock',
    ],
    'data': [
        'wizard/stock_return_picking_views.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
}
