# -*- coding: utf-8 -*-

from odoo import models, _, fields, api
from odoo.exceptions import UserError


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    x_has_purchase_order = fields.Boolean(
        string='Has PO',
        compute='_compute_x_has_purchase_order',
    )

    @api.depends('picking_id.purchase_id')
    def _compute_x_has_purchase_order(self):
        for record in self:
            if record.picking_id.purchase_id or record.picking_id.move_ids.move_orig_ids.purchase_line_id:
                record.x_has_purchase_order = True
            else:
                record.x_has_purchase_order = False

    def action_wizard_purchase_stock_picking_return(self):
        self.ensure_one()
        # Kiểm tra điều kiện cho từng dòng product_return_moves (lines)
        for return_line in self.product_return_moves:
            if return_line.quantity > return_line.move_id.quantity:
                raise UserError(
                    f"Số lượng trả hàng cho sản phẩm {return_line.product_id.name} không thể lớn hơn số lượng đã nhận. "
                    f"Vui lòng kiểm tra lại.")

        prepare_purchase_order = self._prepare_purchase_order_wizard()
        new_purchase_order = self.env['purchase.order'].create(prepare_purchase_order)
        self.picking_id.write({
            'x_return_purchase_order_return_ids': (0, 0, new_purchase_order.id)
        })
        result = {
            'type': 'ir.actions.act_window',
            "name": _('Returned Purchase'),
            'res_model': 'purchase.order',
            'view_mode': 'list, form',
            'res_id': new_purchase_order.id,
            'views': [(self.env.ref('a1_purchase_return.a1_purchase_order_return_form').id, "form")],
        }
        return result

    def _prepare_purchase_order_wizard(self):
        vals = []
        for line in self.product_return_moves:
            if line.x_is_selected:
                vals.append((0, 0, line._prepare_purchase_stock_return_picking_line()))
        if vals == []:
            raise UserError(_("Please select at least one line to return."))

        location_id = self.picking_id.location_dest_id

        res = self.env['purchase.return.wizard'].create(
            [
                {
                    "purchase_id": self.picking_id.purchase_id.id or self.picking_id.move_ids.move_orig_ids.purchase_line_id.order_id.id,
                    "location_id": location_id.id,
                    "return_line_ids": vals,
                    "origin_picking_id": self.picking_id.id,
                }
            ]
        )

        lines = []
        for line in res.return_line_ids:
            val = res._prepare_purchase_line_default_values(line)
            lines.append((0, 0, val))
        prepare_purchase_order = res._prepare_purchase_default_values(lines)

        return prepare_purchase_order


class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    def _prepare_purchase_stock_return_picking_line(self):
        self.ensure_one()
        res = {
            'product_id': self.product_id.id,
            'uom_id': self.product_id.uom_po_id.id,
            'received_qty': self.uom_id._compute_quantity(qty=self.move_id.product_uom_qty,
                                                          to_unit=self.product_id.uom_po_id),
            'return_qty': self.uom_id._compute_quantity(qty=self.quantity, to_unit=self.product_id.uom_po_id),
            'purchase_line_id': self.move_id.purchase_line_id.id or self.move_id.move_orig_ids.purchase_line_id.id,
        }
        return res
