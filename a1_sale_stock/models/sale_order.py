from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_scheduled_date = fields.Datetime(
        string='Picking Scheduled Time',
        compute='_compute_scheduled_date',
    )

    def _prepare_invoice(self):
        values = super(SaleOrder, self)._prepare_invoice()
        values["x_invoice_address"] = self.x_invoice_address
        return values

    @api.depends('picking_ids.scheduled_date')
    def _compute_scheduled_date(self):
        for order in self:
            for picking in order.picking_ids:
                if picking.state not in ('done', 'cancel'):
                    order.x_scheduled_date = picking.scheduled_date