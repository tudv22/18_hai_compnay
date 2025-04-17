# -*- coding: utf-8 -*-
from odoo import fields, models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    x_carrier_partner_id = fields.Many2one(
        related="sale_id.x_carrier_partner_id", 
        comodel_name='res.partner', string='Delivery unit')

    x_shipping_address = fields.Char(
        string="Shipping address",
        compute='_compute_x_shipping_address',
        store=True,
    )

    @api.depends('sale_id.x_shipping_address')
    def _compute_x_shipping_address(self):
        for picking in self:
            picking.x_shipping_address = picking.sale_id.x_shipping_address if picking.sale_id else ''
