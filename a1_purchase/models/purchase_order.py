# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from .convert_amount_in_words import amount_to_vietnamese_text

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_mobile = fields.Char(
        string="Mobile",
        related='partner_id.phone',
        store=True
    )
    x_company_name = fields.Char(
        string="Company name",
        readonly=True,
        compute='_onchange_partner_id_info',
    )
    x_tax_code = fields.Char(
        string="Tax code"
    )
    x_exchange_rate = fields.Float(
        string='Exchange Rate',
        default=1.0,
        required=True
    )
    x_department_id = fields.Many2one(
        comodel_name='hr.department',
        string="Department",
        copy=False,
    )
    x_company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Company currency',
        related='company_id.currency_id',
    )
    x_type = fields.Selection([
        ('purchase', 'Purchase')
    ], default='purchase', string='Type')

    def action_clear_tax_lines(self):
        for line in self.order_line:
            line.taxes_id = False
        return True

    @api.depends('date_order', 'currency_id', 'company_id', 'company_id.currency_id', 'x_exchange_rate')
    def _compute_currency_rate(self):
        for order in self:
            if order.x_exchange_rate:
                order.currency_rate = 1 / order.x_exchange_rate
            else:
                order.currency_rate = 1

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for PO'),
            'template': '/a1_purchase/static/src/xlsx/template_import_po.xlsx'
        }]

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_rfq_as_sent') and self.user_id.email_formatted:
            kwargs['email_from'] = self.user_id.email_formatted
        return super().message_post(**kwargs)

    @api.depends('order_line.move_ids.picking_id')
    def _a1_compute_picking_ids(self):
        res = super(PurchaseOrder, self)._compute_picking_ids()
        for record in self:
            record.picking_ids |= self.env['stock.picking'].search([('origin', '=', record.name)])
        return res

    def _create_picking(self):
        res = super(PurchaseOrder, self)._create_picking()
        for order in self:
            if order.picking_type_id.warehouse_id.reception_steps == 'one_step':
                continue
            order._a1_compute_picking_ids()
        return res

    def _prepare_picking(self):
        res = super(PurchaseOrder, self)._prepare_picking()
        res.update({
            'x_currency_id': self.currency_id.id,
            'x_exchange_rate': self.x_exchange_rate,
        })
        return res

    @api.onchange('currency_id')
    def _onchange_currency_for_exchange_rate(self):
        for record in self:
            if record.currency_id and record.currency_id == record.company_id.currency_id:
                record.x_exchange_rate = 1.0

    @api.onchange('partner_id')
    def _onchange_partner_id_info(self):
        for record in self:
            record.x_company_name = record.partner_id.name if record.partner_id.is_company else record.partner_id.parent_id.name
            record.x_tax_code = record.partner_id.vat
            record.x_department_id = record.user_id.department_id
            if record.partner_id.x_identification_number:
                record.partner_ref = record.partner_id.x_identification_number
            else:
                record.partner_ref = record.partner_id.parent_id.x_identification_number

            if record.partner_id.property_supplier_payment_term_id:
                record.payment_term_id = record.partner_id.property_supplier_payment_term_id
            else:
                record.payment_term_id = record.partner_id.parent_id.property_supplier_payment_term_id

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        res.update({
            'x_exchange_rate': self.x_exchange_rate,
        })
        return res

    def action_preview_print(self):
        action = 'a1_purchase.action_print_purchase_order'
        url = 'report/pdf/%s/%s' % (action, self.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
            'res_id': self.id,
        }

    def amount_total_in_words(self, number, currency):
        number = int(number)
        amount_in_words = amount_to_vietnamese_text(number, currency)
        return amount_in_words


