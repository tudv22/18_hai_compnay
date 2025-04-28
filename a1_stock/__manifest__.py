# -*- coding: utf-8 -*-
{
    "name": "A1 Stock",
    'category': 'HAI Custom Module',
    'description': """
        custom_stock
    """,
    'author': 'Dương Tú',
    "version": "1.0",
    'license': 'LGPL-3',
    "depends": [
        'stock',
        'queue_job'
    ],
    "data": [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/stock_reminder_views.xml',
        'views/stock_operations_menus.xml',
        'wizard/stock_picking_wizard_view.xml'
    ],
        'installable': True,
}
