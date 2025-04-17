# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    x_stock_transfer_request_id = fields.Many2one(
        'stock.transfer.request',
        string='Stock Transfer Request',
        ondelete='cascade',
        copy=False
    )

    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        res = super()._prepare_sale_order_line_data(line, company)
        tax_source_company = line.product_id.with_company(company).taxes_id._filter_taxes_by_company(company)
        current_company_is_household_company = self.company_id.x_company_type == 'household_company'
        if not current_company_is_household_company:
            price_unit = line.price_unit * (1 + sum(tax_source_company.mapped('amount')) / 100)
        else:
            price_unit = line.price_unit
        res.update({
            'purchase_line_ids': [(6, 0, line.ids)],
            'tax_id': [(6, 0, tax_source_company.ids)],
            'price_unit': price_unit,
        })
        return res

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        res = super()._prepare_sale_order_data(name, partner, company, direct_delivery_address)
        warehouse_id = self.env.context.get('sale_warehouse_id', False)
        if self.env.context.get('context_partner_for_household_company', False):
            res.update({
                'partner_id': self.env.context.get('context_partner_for_household_company').id
            })
        if warehouse_id:
            res.update({
                'warehouse_id': warehouse_id
            })
        return res
