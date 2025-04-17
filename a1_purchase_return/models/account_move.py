# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    x_origin_cog_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Origin COG move'
    )

    def button_cancel(self):
        res = super().button_cancel()
        if not self.env.context.get('back_cog_move_cancel', False):
            self._action_back_cog_move_cancel()
        return res

    def button_draft(self):
        res = super().button_draft()
        if not self.env.context.get('back_cog_move_draft', False):
            self._action_back_cog_move_draft()
        return res

    def _action_back_cog_move_draft(self):
        cog_move_ids = self.search([('x_origin_cog_move_id', 'in', self.ids)])
        if cog_move_ids:
            cog_move_ids.filtered(lambda x: x.state == 'posted').with_context(back_cog_move_draft=True).button_draft()
            cog_move_ids.with_context(dynamic_unlink=True).unlink()

    def _action_back_cog_move_cancel(self):
        cog_move_ids = self.search([('x_origin_cog_move_id', 'in', self.ids)])
        if cog_move_ids:
            cog_move_ids.filtered(lambda x: x.state != 'cancel').with_context(back_cog_move_cancel=True).button_cancel()
            cog_move_ids.with_context(dynamic_unlink=True).unlink()

    def _post(self, soft=True):
        posted = super()._post(soft)
        self._create_diff_cog_return_invoice()
        return posted

    def _create_diff_cog_return_invoice(self):
        for invoice in self:
            if invoice.move_type != 'in_refund':
                continue
            valued_lines = self.env['account.move.line'].sudo()
            if invoice.invoice_line_ids.purchase_line_id.order_id and invoice.invoice_line_ids.purchase_line_id.order_id[0].x_type == 'return':
                valued_lines |= invoice.invoice_line_ids.filtered(lambda l: l.product_id and l.product_id.cost_method != 'standard')

            if valued_lines:
                aml_vals = valued_lines._prepare_cog_return_move_line()
                if aml_vals:
                    move_vals = invoice._prepare_move_cog_return_vals()
                    move_vals.update({
                        'line_ids': aml_vals
                    })
                    move_id = self.env['account.move'].sudo().create(move_vals)
                    move_id.action_post()

    def _prepare_move_cog_return_vals(self):
        journal_id = self.env['account.journal'].search([
            ('code', '=', 'MISC'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        return {
            'move_type': 'entry',
            'partner_id': self.partner_id.id,
            'ref': (self.invoice_origin if self.invoice_origin else '') + _(' Differences when returns of NCC goods'),
            'date': self.date,
            'journal_id': journal_id.id,
            'x_origin_cog_move_id': self.id,
        }

    def action_wizard_purchase_order_bill_return(self):
        source_orders = self.line_ids.purchase_line_id.order_id
        view_id = self.env.ref('a1_purchase_return.purchase_bill_return_wizard_form_view').id
        ctx = self.env.context
        default_location_id = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
        ctx = {**ctx, 'default_purchase_ids': source_orders.ids, 'default_location_id': default_location_id.id}
        ctx.pop('default_move_type', None)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Bill Return Wizard'),
            'res_model': 'purchase.bill.return.wizard',
            'target': 'new',
            'view_mode': 'form',
            'context': ctx,
            'views': [[view_id, 'form']]
        }
