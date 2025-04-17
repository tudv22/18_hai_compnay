from odoo import fields, models, api


class RejectPurchaseRequest(models.TransientModel):
    _name = "reject.stock.transfer.request"
    _description = "Reject stock transfer request"

    reject_reason = fields.Text()

    def action_stock_transfer_request(self):
        req_id = self._context.get('active_id')
        current_request = self.env['stock.transfer.request'].search([('id', '=', req_id)], limit=1)
        if current_request:
            current_request.write({
                'state': 'reject',
                'reject_reason': self.reject_reason,
            })
            return {
                'name': ('purchase.request.from'),
                'view_mode': 'form',
                'view_id': self.env.ref('purchase_request.view_purchase_request_form').id,
                'res_model': 'purchase.request',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': current_request.id,
            }

