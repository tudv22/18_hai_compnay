# -*- coding: utf-8 -*-
from odoo import fields, models, api


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _compute_partner_is_internal_partner(self):
        companies = self.env['res.company'].sudo().search([])
        for company in companies:
            company.partner_id.x_is_internal_partner = True
        return True

    x_company_type = fields.Selection(
        selection=[
            ('distribution_company', 'Distribution company'),
            ('retail_company', 'Retail company'),
            ('household_company', 'Household company'),
            ('examination_company', 'Examination company'),
            ('other', 'Other'),
        ],
        string='Company type',
    )

    @api.model
    def _apply_ir_rules(self, query, mode='read'):
        # Pass rule multi-company
        is_inter_company = self.env.context.get('inter-company', False)
        is_inter_company_request = self.env.context.get('default_transfer_request_type', False) == 'inter'
        if is_inter_company or is_inter_company_request:
            return True
        return super()._apply_ir_rules(query, mode)

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        is_inter_company = self.env.context.get('inter-company', False)
        is_inter_company_request = self.env.context.get('default_transfer_request_type', False) == 'inter'
        if is_inter_company or is_inter_company_request:
            return super(ResCompany, self.sudo()).web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super(ResCompany, self).create(vals_list)
        companies._compute_partner_is_internal_partner()
        return companies