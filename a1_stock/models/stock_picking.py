from odoo import fields, models, api, _
from odoo.exceptions import UserError
from num2words import num2words
from datetime import datetime


class StockPicking(models.Model):
    _inherit = "stock.picking"

    x_total_quantity = fields.Integer(
        string='Total Quantity',
        compute='_compute_total_quantity',
    )
    x_warehouse_internal_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        related='picking_type_id.warehouse_id',
    )

    @api.onchange('x_warehouse_internal_id')
    def _internal_set_picking_type_id(self):
        for record in self:
            if record.picking_type_code == 'internal':
                record.picking_type_id = record.x_warehouse_internal_id.int_type_id

    def _compute_total_quantity(self):
        for rec in self:
            rec.x_total_quantity = sum(rec.move_ids.mapped('product_uom_qty'))

    def validate_redundant_export_import(self):
        for rec in self:
            err = ""
            for line in rec.move_ids:
                if line.quantity > line.product_uom_qty:
                    if err == "":
                        err += _('Quantity must be less than or equal to the demand of the product.\n')
                    err += _(
                        '\n---\n'
                        'Product: %s\n'
                        'Demand: %s\n'
                        'Quantity: %s'
                    ) % (line.product_id.name, line.product_uom_qty, line.quantity)
            if err != "":
                raise UserError(err)
        return True

    def button_validate(self):
        self.validate_redundant_export_import()
        res = super(StockPicking, self.with_context(x_skip_write_date_done=True)).button_validate()
        return res

    def open_popup_print_stock_picking(self):
        action = self.env["ir.actions.actions"]._for_xml_id("a1_stock.popup_print_stock_picking_action")
        action['res_id'] = self.id
        action['context'] = self._context
        action['context'] = self._context
        return action

    def write(self, vals):
        if (
                'date_done' in vals
            and vals.get('date_done', False)
            and self.env.context.get('x_skip_write_date_done', False)
        ):
            for record in self:
                cp_vals = vals.copy()
                if record.date_done:
                    cp_vals.pop('date_done')
                super(StockPicking, record).write(cp_vals)
            return True
        else:
            return super(StockPicking, self).write(vals)