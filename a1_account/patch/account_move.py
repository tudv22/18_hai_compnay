# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.models.account_move import AccountMove


def _compute_linked_attachment_id(self, attachment_field, binary_field):
    for move in self:
        move[attachment_field] = False
AccountMove._compute_linked_attachment_id = _compute_linked_attachment_id