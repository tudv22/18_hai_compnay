from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def create(self, vals):
        move = super(StockMove, self).create(vals)
        if move.sale_line_id:  # Nếu có liên kết với đơn bán hàng
            move.price_unit = move.sale_line_id.price_unit
        return move

    def _get_dest_account(self, accounts_data):
        res = super(StockMove, self)._get_dest_account(accounts_data)
        if self.product_id.x_is_voucher:
            picking_type_code = self.picking_id.picking_type_code
            partner_id = self.picking_id.partner_id
            if picking_type_code == 'outgoing' and partner_id.x_is_internal_partner:
                internal_outgoing_account_id = self.product_id.with_company(self.company_id).categ_id.x_internal_voucher_outgoing_warehouse_cost_id
                if not internal_outgoing_account_id:
                    raise UserError(_("Please set Internal Voucher Outgoing Account for product category %s") % self.product_id.categ_id.name)
                return internal_outgoing_account_id.id
        return res