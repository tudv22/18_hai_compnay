# -*- coding: utf-8 -*-

from odoo import models, _, fields, api
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    x_has_sale_order = fields.Boolean(
        string='Has SO',
        compute='_compute_x_has_sale_order',
    )
    x_partner_id = fields.Many2one(
        comodel_name='res.partner',
        related='picking_id.partner_id',
        string='Customer'
    )

    @api.depends('picking_id.sale_id')
    def _compute_x_has_sale_order(self):
        for record in self:
            if record.picking_id.sale_id:
                record.x_has_sale_order = True
            else:
                record.x_has_sale_order = False

    def action_wizard_sale_stock_picking_return(self):
        self.ensure_one()
        new_sale_order_return = self.env['sale.order'].create(self._prepare_sale_order_return_wizard())
        self.picking_id.write({
            'x_return_sale_order_return_ids': (0, 0, new_sale_order_return.id)
        })
        result = {
            'type': 'ir.actions.act_window',
            "name": _('Returned sale'),
            'res_model': 'sale.order',
            'view_mode': 'list, form',
            'res_id': new_sale_order_return.id,
            'views': [(self.env.ref('a1_sale_return.a1_sale_return_form').id, "form")],
        }
        return result

    def _prepare_sale_order_return_wizard(self):
        vals = []
        for line in self.product_return_moves:
            if line.x_is_selected:
                vals.append((0, 0, line._prepare_sale_stock_return_picking_line()))
        if vals == []:
            raise UserError(_("Please select at least one line to return."))
        res = self.env['sale.return.wizard'].create({
            "sale_id": self.picking_id.sale_id.id,
            "return_line_ids": vals,
            "location_id": self.location_id.id,
            "origin_picking_id": self.picking_id.id,
        })
        lines = []
        for line in res.return_line_ids:
            val = res._prepare_sale_line_default_values(line)
            lines.append((0, 0, val))
        prepare_sale_order = res._prepare_sale_default_values(lines)

        return prepare_sale_order


class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    def _prepare_sale_stock_return_picking_line(self):
        self.ensure_one()
        res = {
            'product_id': self.product_id.id,
            'uom_id': self.product_id.uom_po_id.id,
            'delivered_qty': self.uom_id._compute_quantity(qty=self.move_id.product_uom_qty,
                                                           to_unit=self.product_id.uom_po_id),
            'return_qty': self.uom_id._compute_quantity(qty=self.quantity, to_unit=self.product_id.uom_po_id),
            'sale_line_id': self.move_id.sale_line_id.id,
        }
        return res
