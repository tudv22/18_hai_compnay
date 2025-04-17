from odoo import api, fields, models, Command, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_exchange_rate = fields.Float(
        string="Exchange rate", 
        related='move_id.x_exchange_rate',
    )
    x_amount_tax = fields.Monetary(
        string='Amount tax',
        compute='_compute_amount_tax', store=True
    )
    x_origin_line_id = fields.Many2one(
        comodel_name='account.move.line',
        copy=False,
    )

    @api.depends('quantity', 'price_unit', 'tax_ids', 'discount')
    def _compute_amount_tax(self):
        for line in self:
            if line.tax_ids:
                price_unit = line.price_unit * (1 - line.discount / 100)
                taxes = line.tax_ids.compute_all(
                    price_unit=price_unit,
                    quantity=line.quantity,
                    currency=line.move_id.currency_id,
                    product=line.product_id,
                    partner=line.move_id.partner_id,
                )
                line.x_amount_tax = sum(t.get('amount', 0.0) for t in taxes['taxes'])
            else:
                line.x_amount_tax = 0.0

    @api.depends('currency_id', 'company_id', 'move_id.date', 'x_exchange_rate')
    def _compute_currency_rate(self):
        for line in self:
            line.currency_rate = 1 / line.x_exchange_rate if line.x_exchange_rate else 1

    def _compute_account_id(self):
        if self.env.context.get('x_skip_compute_account_id', False):
            return True
        return super(AccountMoveLine, self)._compute_account_id()