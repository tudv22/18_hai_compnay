# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'


    x_return_purchase_order_return_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='x_origin_picking_id',
        string="Return Purchases",
        copy=False
    )
    x_count_purchase_order_return = fields.Integer(
        compute="_compute_x_count_purchase_order_return",
        copy=False
    )

    @api.onchange('x_return_purchase_order_return_ids')
    def _compute_x_count_purchase_order_return(self):
        for record in self:
            record.x_count_purchase_order_return = len(record.x_return_purchase_order_return_ids)

    def action_view_purchase_return(self):
        if self.x_return_purchase_order_return_ids:
            context = {'create': True, 'delete': True, 'edit': True}
            view_id = self.env.ref('a1_purchase_return.purchase_order_tree_inherit_a1_purchase_return').id
            view_form_id = self.env.ref('a1_purchase_return.a1_purchase_order_return_form').id
            return {
                'name': _('Purchase Return'),
                'view_mode': 'list,form',
                'res_model': 'purchase.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', '=', self.x_return_purchase_order_return_ids.ids)],
                'context': context,
                'views': [
                    (view_id, 'list'),
                    (view_form_id, 'form')
                ]
            }
