# -*- coding: utf-8 -*-
{
    "name": "A1 Stock Report Transfer",
    'category': 'HAI Custom Module',
    'description': """
        Báo cáo nhập xuất
    """,
    'author': 'Dương Tú',
    "version": "1.0",
    'license': 'LGPL-3',
    "depends": [
        'stock',
    ],
    "data": [
        'report/anna_report_template.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
}
