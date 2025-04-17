# -*- coding: utf-8 -*-

from . import models
from . import wizard


def uninstall_hook(env):
    """ Delete domain from purchase.order action. """
    action = env['ir.actions.act_window']._for_xml_id('purchase.purchase_form_action')
    action_id = env['ir.actions.act_window'].browse(action.get('id'))
    action_id.write({'domain': "[('state', 'in', ('purchase', 'done'))]"})

    action = env['ir.actions.act_window']._for_xml_id('purchase.purchase_rfq')
    action_id = env['ir.actions.act_window'].browse(action.get('id'))
    action_id.write({'domain': "[]"})