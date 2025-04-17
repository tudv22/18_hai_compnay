from odoo import fields, models, api


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company=None, date=None):
        if self.env.context.get('x_exchange_rate', 0):
            return self.env.context.get('x_exchange_rate', 0)
        return super(ResCurrency, self)._get_conversion_rate(from_currency, to_currency, company=company, date=date)

