# -*- coding: utf-8 -*-
{
    'name': "A1 sale return",
    'summary': "A1 sale return",
    'description': """
        Chức năng trả hàng đã bán và báo cáo
    """,
    'author': "Dương Tú",
    'category': 'HAI Custom Module',
    'version': '1.0',
    'depends': [
        'a1_sale_stock',
        'a1_sale',
        'sh_warehouse_avg_costing',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'report/print_sale_order_return.xml',
        'views/sale_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_return_views.xml',
        'wizard/stock_picking_return_views.xml',
        'wizard/sale_return_wizard_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
}
