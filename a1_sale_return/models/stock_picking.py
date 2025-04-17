# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_return_sale_order_return_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='x_origin_picking_id',
        string="Return sales",
        copy=False
    )
    x_count_sale_order_return = fields.Integer(
        compute="_compute_count_sale_order_return",
        copy=False
    )

    @api.onchange('x_return_sale_order_return_ids')
    def _compute_count_sale_order_return(self):
        for record in self:
            record.x_count_sale_order_return = len(record.x_return_sale_order_return_ids)

    def action_view_sale_return(self):
        if self.x_return_sale_order_return_ids:
            context = {'create': True, 'delete': True, 'edit': True}
            view_id = self.env.ref('a1_sale_return.sale_order_tree_inherit_a1_sale_return').id
            view_form_id = self.env.ref('a1_sale_return.a1_sale_return_form').id
            return {
                'name': _('Sale Return'),
                'view_mode': 'list,form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': [('id', 'in', self.x_return_sale_order_return_ids.ids)],
                'context': context,
                'views': [
                    (view_id, 'list'),
                    (view_form_id, 'form')
                ]
            }