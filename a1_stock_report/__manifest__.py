# -*- coding: utf-8 -*-
{
    'name': 'A1 Finance TT200 Report',
    'category': 'HAI Custom Module',
    'description': """
        Báo cáo nhập xuất tồn
    """,
    'author': 'Dương Tú',
    'depends': [
        'stock',
        'a1_stock',
        'product'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/in_out_stock_report.xml',
        'views/a1_stock_report_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'a1_stock_report/static/src/components/**/*',
        ],
    },
    'license': 'OEEL-1',
}
