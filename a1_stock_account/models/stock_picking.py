# -*- coding: utf-8 -*-
from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_account_move_count = fields.Integer(
        "Account move count",
        compute='_compute_picking_account_move_count'
    )
    x_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    x_exchange_rate = fields.Float(
        string='Exchange Rate',
        default=1.0,
    )

    @api.depends('move_ids.account_move_ids')
    def _compute_picking_account_move_count(self):
        for picking in self:
            picking.x_account_move_count = len(picking.move_ids.account_move_ids)

    def action_view_account_moves(self):
        self.ensure_one()
        action = self.env.ref('account.action_move_journal_line').read()[0]
        account_move_ids = self.move_ids.account_move_ids
        if len(account_move_ids) > 1:
            action['domain'] = [('id', 'in', account_move_ids.ids)]
            action['views'] = [
                (self.env.ref('account.view_move_tree').id, 'tree'),
                (self.env.ref('account.view_move_form').id, 'form')
            ]
        elif account_move_ids:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = account_move_ids.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
