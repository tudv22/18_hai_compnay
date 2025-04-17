from odoo import _, api, fields, models
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_currency_rate = fields.Float(
        string='Currency Rate',
        compute='_compute_invoice_currency_rate', store=True, precompute=True,
        copy=False,
        digits=0,
        help="Currency rate from company currency to document currency.",
    )

    def _get_violated_lock_dates(self, invoice_date, has_tax):
        if not self.company_id:
            self._compute_company_id()
        return super()._get_violated_lock_dates(invoice_date, has_tax)

    @api.depends('currency_id', 'company_currency_id', 'company_id', 'invoice_date')
    def _compute_invoice_currency_rate(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                if move.currency_id:
                    move.invoice_currency_rate = self.env['res.currency']._get_conversion_rate(
                        from_currency=move.company_currency_id,
                        to_currency=move.currency_id,
                        company=move.company_id,
                        date=move.invoice_date or fields.Date.context_today(move),
                    )
                else:
                    move.invoice_currency_rate = 1

    @api.model
    def default_get(self, vals):
        res = super(AccountMove, self).default_get(vals)
        res['invoice_date'] = fields.Date.context_today(self)
        return res

    def _get_default_x_exchange_rate(self):
        for r in self:
            if r.currency_id == r.company_currency_id:
                return 1.0
            else:
                return r.x_exchange_rate

    x_exchange_rate = fields.Float(
        string="Exchange rate",
        copy=False,
        default=1.0
    )
    x_invoice_id = fields.Many2one(
        'account.move',
        string='Original Invoice',
        help="Reference to the original invoice.",
        readonly=True,
    )
    x_amount_tax_total = fields.Monetary(
        string='Tax total',
        compute='_compute_amount_tax_total', store=True, readonly=True,
    )
    x_tax_payment_substitute_ids = fields.One2many(
        'account.move',
        'x_tax_payment_substitute_id',
        string='Tax Payment Substitute',
        copy=False,
    )
    x_tax_payment_substitute_id = fields.Many2one(
        'account.move',
        string='Tax Payment Substitute',
        copy=False,
    )

    @api.onchange('currency_id')
    def _update_x_exchange_rate(self):
        for record in self:
            record.x_exchange_rate = record._get_default_x_exchange_rate()

    @api.depends('line_ids.x_amount_tax')
    def _compute_amount_tax_total(self):
        for move in self:
            move.x_amount_tax_total = sum(move.line_ids.mapped('x_amount_tax'))

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        # self._compute_sale_order_id()
        return res

    def action_register_payment(self):
        res = super(AccountMove, self).action_register_payment()
        res['context'].update({
            'default_x_exchange_rate': self[0].x_exchange_rate,
        })
        return res

    @api.depends('move_type')
    def _compute_invoice_default_sale_person(self):
        res = super(AccountMove, self)._compute_invoice_default_sale_person()
        for record in self:
            if not record.invoice_user_id:
                record.invoice_user_id = self.env.user.id
        return res

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft)
        tax_product_id = self.env.ref('a1_account.product_tax_payment_substitute_tax', raise_if_not_found=True)
        vals_list = []

        for record in self:
            if record.move_type == 'in_invoice':
                tax_payment_substitute = record.line_ids.filtered(lambda x: x.tax_line_id.amount < 0)
                if not tax_payment_substitute:
                    continue
                if not tax_product_id.property_account_expense_id or not tax_product_id.x_property_tax_payment_substitute_account_id:
                    raise UserError(_('Please set accounts for Tax Payment Substitute product.'))
                list_by_partner = self._get_list_by_partner(tax_payment_substitute)
                for partner_id, lines in list_by_partner.items():
                    move_vals = record.prepare_tax_payment_substitute_move(partner_id=partner_id, lines=lines, tax_product_id=tax_product_id)
                    vals_list.append(move_vals)

        if vals_list:
            self.env['account.move'].with_context(x_skip_compute_account_id=True).create(vals_list)
        return res

    def prepare_tax_payment_substitute_move(self, partner_id, lines, tax_product_id):
        self.ensure_one()
        move_line_vals = self.prepare_tax_payment_substitute_move_lines(lines, tax_product_id)
        vals = {
            'partner_id': partner_id.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'invoice_date': self.date,
            'x_tax_payment_substitute_id': self.id,
            'date': self.date,
            'ref': self.name,
            'line_ids': move_line_vals,
            'move_type': 'in_invoice',
            'x_exchange_rate': self.x_exchange_rate,
        }
        return vals

    def prepare_tax_payment_substitute_move_lines(self, lines, tax_product_id):
        self.ensure_one()
        vals = []
        for line in lines:
            debit_val = {
                'sequence': 99991,
                'name': tax_product_id.name,
                'product_id': tax_product_id.id,
                'tax_ids': False,
                'account_id': tax_product_id.property_account_expense_id.id,
                'debit': line.credit,
                'credit': 0,
                'price_unit': line.credit,
            }
            vals.append((0, 0, debit_val))
        credit_move_line_vals = self.prepare_credit_tax_payment_substitute_move_lines(lines, tax_product_id)
        vals.append((0, 0, credit_move_line_vals))
        return vals

    def prepare_credit_tax_payment_substitute_move_lines(self, lines, tax_product_id):
        self.ensure_one()
        total_credit = sum([line.credit for line in lines])
        credit_val = {
            'sequence': 99991,
            'name': tax_product_id.name,
            'product_id': tax_product_id.id,
            'debit': 0,
            'credit': total_credit,
            'tax_ids': False,
            'account_id': tax_product_id.x_property_tax_payment_substitute_account_id.id,
        }
        return credit_val

    def action_view_tax_payment_substitute_invoice(self):
        """This function returns an action that display tax payment substitute of
        given vendor invoice. When only one found, show the tax payment substitute
        immediately.
        """
        invoices = self.x_tax_payment_substitute_ids
        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        # choose the view_mode accordingly
        if len(invoices) > 1:
            result['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            res = self.env.ref('account.view_move_form', False)
            form_view = [(res and res.id or False, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(state, view) for state, view in result['views'] if view != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = invoices.id
        else:
            result = {'type': 'ir.actions.act_window_close'}

        return result

    def button_draft(self):
        res = super(AccountMove, self).button_draft()
        for record in self:
            for move in record.x_tax_payment_substitute_ids:
                if move.state in ('posted', 'cancel'):
                    move.button_draft()
            record.x_tax_payment_substitute_ids.unlink()
        return res

    def _get_list_by_partner(self, tax_payment_substitute):
        list_by_partner = {}
        err = []
        for line in tax_payment_substitute:
            partner_id = line.tax_line_id.x_tax_authority_id
            if not partner_id:
                err.append(line.tax_line_id.name)
            else:
                list_by_partner.setdefault(partner_id, []).append(line)
        if err:
            raise UserError(_('Please set Tax Authority for the following taxes: %s') % ', '.join(err))
        return list_by_partner