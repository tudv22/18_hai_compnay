from odoo import _, api, fields, models

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_adjust_sale_order_id = fields.Many2one(
        'sale.order',
        string='Original SO',
        help="Reference to the original SO.",
        readonly=True,
    )

    @api.depends('line_ids.sale_line_ids')
    def _compute_origin_so_count(self):
        res = super(AccountMove, self)._compute_origin_so_count()
        for move in self:
            if move.x_adjust_sale_order_id:
                move.sale_order_count = len(move.x_adjust_sale_order_id)
        return res

    def action_adjust_increase(self):
        self.ensure_one()
        # Duplicate the record
        duplicate = self.copy({
            'x_invoice_id': self.id,
            'invoice_user_id': self.invoice_user_id.id,
        })
        # Update sale order links on the duplicated invoice lines
        for original_line, new_line in zip(self.invoice_line_ids, duplicate.invoice_line_ids):
            if original_line.sale_line_ids:
                new_line.sale_line_ids = [(6, 0, original_line.sale_line_ids.ids)]
        if self.x_adjust_sale_order_id:
            duplicate.x_adjust_sale_order_id = self.x_adjust_sale_order_id
        else:
            duplicate.x_adjust_sale_order_id = self.line_ids.sale_line_ids.order_id[0] if self.line_ids.sale_line_ids.order_id else False

        # Redirect to the duplicated record
        return {
            'name': 'Draft',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': duplicate.id,
            'target': 'current',
        }

    def action_view_source_sale_orders(self):
        res = super(AccountMove, self).action_view_source_sale_orders()
        if self.x_adjust_sale_order_id:
            result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
            result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
            result['res_id'] = self.x_adjust_sale_order_id.id
            return result
        return res