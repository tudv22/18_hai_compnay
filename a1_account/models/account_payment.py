from odoo import fields, models, api, _
from num2words import num2words

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def a1_print_receipt_report(self):
        self.ensure_one()
        self = self.sudo()
        url = 'report/pdf/%s/%s' % ('a1_account.action_a1_report_receipt', self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
            'res_id': self.id,
        }

    def amount_to_text(self, amount, lang='vi'):
        try:
            return num2words(amount, lang=lang).capitalize() +' VNĐ'
        except NotImplementedError:
            return _("Language not supported")