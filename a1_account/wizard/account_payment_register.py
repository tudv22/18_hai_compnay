from odoo import Command, models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    x_amount = fields.Monetary(
        string='Amount',
        compute='_compute_x_amount',
    )
    x_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    x_exchange_rate = fields.Float(
        string='Exchange Rate',
        default=1.0,
        required=True
    )

    @api.onchange('amount', 'x_exchange_rate')
    def _compute_x_amount(self):
        for record in self:
            record.x_amount = record.amount * record.x_exchange_rate

    def action_create_payments(self):
        res = super(AccountPaymentRegister,
                     self.with_context(x_exchange_rate=self.x_exchange_rate)).action_create_payments()
        for record in self:
            lines_currency= record.line_ids.mapped('currency_id')
            if len(lines_currency) > 1:
                raise UserError(_('You cannot create payments for different currencies.'))
        return res