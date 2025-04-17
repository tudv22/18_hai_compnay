# -*- coding: utf-8 -*-
{
    'name': "A1 Purchase Return",
    'summary': "A1 Purchase Return",
    'description': """
        Chức năng trả hàng đã mua và báo cáo
    """,
    'author': "Dương Tú",
    'category': 'HAI Custom Module',
    'version': '1.0',
    'depends': [
        'stock_accountant',
        'a1_stock_return_picking',
        'a1_purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',

        'report/print_purchase_return.xml',

        'views/purchase_return_views.xml',
        'views/purchase_views.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_views.xml',

        'wizard/stock_picking_views.xml',
        'wizard/purchase_return_wizard_views.xml',
        'wizard/purchase_bill_return_wizard_views.xml',
    ],
    'license': 'LGPL-3',
    'uninstall_hook': 'uninstall_hook',
    'installable': True,
}
