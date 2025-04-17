# -*- coding: utf-8 -*-
{
    'name': "A1 Stock Transfer Request",
    'summary': "Module handle stock transfer request",
    'description': """Yêu cầu điều chuyển liên kho""",
    'author': "Dương Tú",
    'category': 'HAI Custom Module',
    'version': '0.1',
    'depends': [
        'a1_stock','sale_purchase_inter_company_rules'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',

        'data/ir_sequense.xml',

        'report/anna_report_template.xml',

        'wizards/reject_stock_transfer_request_view.xml',

        'views/stock_transfer_request_views.xml',
        'views/stock_picking_views.xml',
        'views/purchase_views.xml',
        'views/stock_tranfer_request_reminder.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [],
    }
}
