from odoo import fields, models, api, _
from odoo.exceptions import UserError
from num2words import num2words
from datetime import datetime

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def amount_to_text(self, amount, lang='vi'):
        try:
            return num2words(amount, lang=lang).capitalize()
        except NotImplementedError:
            return _("Language not supported")

    def anna_print_stock_picking(self):
        self.ensure_one()
        self = self.sudo()
        action_ingoing = 'a1_stock_report_transfer.anna_print_stock_picking_ingoing'
        action_outgoing = 'a1_stock_report_transfer.anna_print_stock_picking_outgoing'
        if self.picking_type_id.code == 'incoming':
            action = action_ingoing
        elif self.picking_type_id.code == 'outgoing':
            action = action_outgoing
        else:
            return
        url = 'report/pdf/%s/%s' % (action, self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
            'res_id': self.id,
        }