from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
from .convert_amount_in_words import amount_to_vietnamese_text

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_type = fields.Selection([
        ('sale', 'Sale'),
    ], default='sale', string='Type'
    )
    x_exchange_rate = fields.Float(
        string='Exchange Rate',
        default=1.0,
        required=True,
    )
    x_company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Company currency',
        related='company_id.currency_id',
    )
    carrier_tracking_ref = fields.Char(
        string='Tracking Reference',
        copy=False
    )
    x_is_cod = fields.Boolean(
        string="COD?",
        default=False
    )
    x_source_details = fields.Char(
        string="Source details",
        help="The Information field used to display more details about the order source."
             " Ex: Fanpage A, Tiktok 1,...",
        copy=False
    )
    x_source_activity = fields.Char(
        string="Source activity",
        help="The Information field used to display the activity of the order source."
             " Ex: Livestream, Story,...",
        copy=False
    )
    x_mobile = fields.Char(
        string="Mobile",
        related='partner_id.phone',
        store=True
    )
    x_carrier_partner_id = fields.Many2one(
        'res.partner',
        'Delivery unit',
        ondelete='set null'
    )
    x_company_name = fields.Char(
        string="Company name",
        readonly=True,
        compute='_onchange_partner_id_info',
    )
    x_tax_code = fields.Char(
        string="Tax code"
    )
    x_invoice_address = fields.Char(
        string="Invoice address"
    )
    x_shipping_address = fields.Char(
        string="Shipping address"
    )
    x_is_variation_grid_entry = fields.Boolean(
        string="Is Variation Grid Entry ?",
        default=False,
        compute="_compute_is_variation_grid_entry",
        compute_sudo=True,
    )
    x_department_id = fields.Many2one(
        comodel_name='hr.department',
        string="Department",
        copy=False,
    )
    x_adjust_invoice_ids = fields.One2many(
        'account.move',
        'x_adjust_sale_order_id',
        string='Invoices',
    )
    x_payment_status = fields.Selection(
        selection=[
            ('unpaid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('full', 'Fully Paid'),
        ],
        string='Payment Status',
        compute='_compute_x_payment_status',
        store=True
    )
    @api.depends('order_line.invoice_lines', 'x_adjust_invoice_ids')
    def _get_invoiced(self):
        res = super(SaleOrder, self)._get_invoiced()
        for order in self:
            if order.x_adjust_invoice_ids:
                all_invoices = order.invoice_ids | order.x_adjust_invoice_ids
                order.invoice_ids = all_invoices
                order.invoice_count = len(all_invoices)
        return res

    @api.depends('currency_id', 'date_order', 'company_id', 'x_exchange_rate')
    def _compute_currency_rate(self):
        for order in self:
            if order.x_exchange_rate:
                order.currency_rate = 1 / order.x_exchange_rate
            else:
                order.currency_rate = 1

    @api.depends('order_line.product_uom_qty', 'invoice_ids.invoice_line_ids.quantity',
                 'invoice_ids.invoice_line_ids.sale_line_ids', 'invoice_ids.state')
    def _compute_x_payment_status(self):
        for order in self:
            full = True
            partial = False
            has_invoice = False
            if not order.invoice_ids:
                order.x_payment_status = 'unpaid'
                continue
            for sale_line in order.order_line:
                order_qty = sale_line.product_uom_qty
                invoice_lines = self.env['account.move.line'].search([
                    ('sale_line_ids', 'in', sale_line.ids),
                    ('move_id', 'in', order.invoice_ids.ids),
                    ('move_id.state', '=', 'posted')  # Chỉ tính hóa đơn đã xác nhận
                ])
                invoiced_qty = sum(invoice_lines.mapped('quantity'))
                if invoiced_qty > 0:
                    has_invoice = True
                if invoiced_qty == order_qty:
                    continue
                elif invoiced_qty > 0:
                    partial = True
                    full = False
                else:
                    full = False

            if full:
                order.x_payment_status = 'full'
            elif partial or has_invoice:
                order.x_payment_status = 'partial'
            else:
                order.x_payment_status = 'unpaid'

    def action_confirm_so(self):
        if any(order.state not in ('draft', 'sent') for order in self):
            raise UserError(_("Only draft orders can be marked as created directly."))
        self.action_confirm()

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent') and self.user_id.email_formatted:
            kwargs["email_from"] = self.user_id.email_formatted
        return super().message_post(**kwargs)

    def get_partner_address(self, partner_id):
        address = []
        if not partner_id:
            return False
        if partner_id.street:
            address.append(partner_id.street)
        if partner_id.street2:
            address.append(partner_id.street2)
        if partner_id.city:
            address.append(partner_id.city)
        if partner_id._get_country_name():
            address.append(partner_id._get_country_name())

        return ", ".join(address)

    @api.onchange('partner_id')
    def _onchange_partner_id_info(self):
        for record in self:
            if not record.partner_id:
                record.x_company_name = False
                record.x_tax_code = False
                continue
            record.x_company_name = record.partner_id.name if record.partner_id.is_company else record.partner_id.parent_id.name
            record.x_tax_code = record.partner_id.vat
            if record.partner_id.user_id:
                record.x_department_id = record.partner_id.user_id.department_id.id
            else:
                record.x_department_id = record.user_id.department_id

    @api.onchange('partner_shipping_id', 'partner_id')
    def _onchange_partner_shipping_address_id(self):
        for record in self:
            if not record.partner_shipping_id:
                record.x_shipping_address = False
                continue
            record.x_shipping_address = record.get_partner_address(record.partner_shipping_id)

    @api.onchange('partner_invoice_id')
    def _onchange_partner_invoice_address_id(self):
        for record in self:
            record.x_invoice_address = record.get_partner_address(record.partner_invoice_id)

    @api.depends('partner_id')
    def _compute_partner_id_info(self):
        for order in self:
            if not order.partner_id:
                continue
            if not order.x_company_name:
                order.x_company_name = order.partner_id.name if order.partner_id.is_company else order.partner_id.company_id.name
            if not order.x_tax_code:
                order.x_tax_code = order.partner_id.vat

    @api.depends('partner_shipping_id', 'partner_id')
    def _compute_partner_shipping_address_id(self):
        for order in self:
            if not order.partner_shipping_id:
                order.x_shipping_address = False
                continue
            if not order.x_shipping_address:
                order.x_shipping_address = self.get_partner_address(order.partner_shipping_id)

    @api.depends('partner_invoice_id')
    def _compute_partner_invoice_address_id(self):
        for order in self:
            if not order.partner_invoice_id:
                continue
            if not order.x_invoice_address:
                order.x_invoice_address = self.get_partner_address(order.partner_invoice_id)

    def _prepare_invoice(self):
        res = super(SaleOrder, self)._prepare_invoice()
        if not self.x_is_cod:
            res.update({
                'partner_id': self.partner_id.id,
            })
        else:
            res.update({
                'partner_id': self.x_carrier_partner_id.id,
            })
        return res

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Sale Order'),
            'template': '/a1_sale/static/src/xlsx/Template_SO.xlsx'
        }]

    def _compute_is_variation_grid_entry(self):
        res_config_settings = self.env['res.config.settings'].sudo().search([],limit = 1, order = 'id desc')
        for rec in self:
            if res_config_settings.module_sale_product_matrix:
                rec.x_is_variation_grid_entry = True
            else:
                rec.x_is_variation_grid_entry = False

    @api.model
    def default_get(self, fields_list):
        res = super(SaleOrder, self).default_get(fields_list)
        res_config_settings = self.env['res.config.settings'].sudo().search([],limit = 1, order = 'id desc')
        if res_config_settings.module_sale_product_matrix:
            res['x_is_variation_grid_entry'] = True
        else:
            res['x_is_variation_grid_entry'] = False
        return res

    def _check_amount_is_positive(self):
        for wizard in self:
            if wizard.advance_payment_method == 'percentage' and wizard.amount <= 0.00:
                raise UserError(_('The value of the down payment amount must be positive.'))
            elif wizard.advance_payment_method == 'fixed' and wizard.fixed_amount <= 0.00:
                raise UserError(_('The value of the down payment amount must be positive.'))

    def action_btn_create_invoices(self):
        invoicing_wizard = self.env['sale.advance.payment.inv'].create({
            'sale_order_ids': [(6, 0, self.ids)],
            'advance_payment_method': 'delivered',
        })
        invoices = invoicing_wizard._create_invoices(invoicing_wizard.sale_order_ids)
        return invoicing_wizard.sale_order_ids.action_view_invoice(invoices=invoices)

    @api.model
    def action_create_invoices(self):
        invoicing_wizard = self.env['sale.advance.payment.inv'].create({
            'sale_order_ids': [(6, 0, self.ids)],
            'advance_payment_method': 'delivered',
        })
        invoices = invoicing_wizard._create_invoices(invoicing_wizard.sale_order_ids)
        return invoicing_wizard.sale_order_ids.action_view_invoice(invoices=invoices)

    def action_preview_print_so(self):
        action = 'a1_sale.action_print_sale_order'
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

