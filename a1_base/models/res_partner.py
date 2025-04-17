# -*- coding: utf-8 -*-
from Tools.scripts.dutree import store

from odoo import fields, models, _, api
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_partnership = fields.Selection(
        selection=[
            ('vendor', 'Vendor'),
            ('customer', 'Customer'),
            ('both', 'Both'),
            ('employee', 'Employee'),
        ], string='Partnership',
        default='vendor',
        tracking=True
    )
    x_identification_number = fields.Char(
        string='Identification Number',
        tracking=True,
        copy=False,
        size=12,
    )
    x_old_code = fields.Char(
        string='Old code',
        copy=False,
    )
    x_is_internal_partner = fields.Boolean(
        string='Is internal partner',
        default=False,
    )

    _sql_constraints = [
        ('unique_x_identification_number', 'unique(x_identification_number)', 'Identification number must be unique'),
        ('unique_vat', 'unique(vat)', 'VAT must be unique'),
    ]

    @api.constrains('vat')
    def _check_vat_for_partner_is_company(self):
        for record in self:
            if record.company_type == 'company':
                if not record.vat:
                    raise UserError(_("The VAT number must be between 10 and 13 characters long."))
                if not len(record.vat) in (10, 14):
                    raise UserError(_("The VAT number must be between 10 and 13 characters long."))

    def _phone_format_number(self, number, country, force_format='E164', raise_exception=False):
        return number

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self.phone

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self.mobile
