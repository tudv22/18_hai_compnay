from odoo import api, fields, models
from datetime import date, datetime, timedelta

class StockMove(models.Model):
    _inherit = "stock.move"


    def _get_price_unit(self):
        self = self.with_context(x_exchange_rate=self.picking_id.x_exchange_rate)
        return super(StockMove, self)._get_price_unit()

    def _account_entry_move(self, qty, description, svl_id, cost):
        am_vals = super()._account_entry_move(qty, description, svl_id, cost)
        for am_val in am_vals:
            am_val.update({
                'x_exchange_rate': self.picking_id.x_exchange_rate
            })
        return am_vals

    def _get_accounting_data_for_valuation(self):
        """
            Nếu là picking trả lại hàng bán thì sẽ update tài khoản trung gian (15x, 3319, ...) bằng 632
        """
        self.ensure_one()
        journal_id, acc_src, acc_dest, acc_valuation = super()._get_accounting_data_for_valuation()
        if self._is_in() and not self._is_returned(valued_type='in') and self.picking_id.sale_id and self.picking_id.sale_id.x_type == 'return':
            acc_src = acc_dest

        """
            Nếu là picking trả lại hàng mua thì sẽ update tài khoản trung gian 1561 thành Có, 151 thành Nợ
        """
        if self._is_out() and self._is_returned(valued_type='out') and self.picking_id.purchase_id and self.picking_id.purchase_id.x_type == 'return':
            temp = acc_valuation
            acc_valuation = acc_src
            acc_src = temp
        return journal_id, acc_src, acc_dest, acc_valuation

    def get_department_id(self):
        # Nếu phiếu kho được tạo từ POS order
        pos_oder = self.picking_id.pos_order_id
        if pos_oder:
            return pos_oder.x_store_id.department_id.id

        # Nếu phiếu kho được tạo từ PO
        purchase_order = self.picking_id.purchase_id
        if purchase_order:
            return purchase_order.x_department_id.id

        # Nếu phiếu kho được tạo từ SO
        sale_order = self.picking_id.sale_id
        if sale_order:
            return sale_order.x_department_id.id

        # Nếu phiếu kho được tạo từ YC nhập/xuất khác
        stock_other_request = self.picking_id.x_stock_other_request_id
        if stock_other_request:
            return stock_other_request.department_id.id

    def _generate_valuation_lines_data(self, partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description):
        if not self.env.context.get('x_department_id'):
            x_department_id = self.get_department_id()
            self = self.with_context(x_department_id=x_department_id)
        results = super()._generate_valuation_lines_data(partner_id, qty, debit_value, credit_value, debit_account_id, credit_account_id, svl_id, description)
        x_department_id = self.env.context.get('x_department_id')
        for key, line in results.items():
            line['x_profit_cost_center_id'] = x_department_id
        return results

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        # if self._is_out() and not self.env.context.get('is_returned') and self.sale_line_id:
        #     temp_account_id = credit_account_id
        #     credit_account_id = debit_account_id
        #     debit_account_id = temp_account_id
        if not self.env.context.get('x_department_id'):
            x_department_id = self.get_department_id()
            self = self.with_context(x_department_id=x_department_id)
        result = super()._prepare_account_move_vals(credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost)
        result['x_department_id'] = self.env.context.get('x_department_id')
        svl = self.env['stock.valuation.layer'].browse(svl_id)
        if not self.env.context.get('force_period_date') and not svl.account_move_line_id:
            date_done = self.picking_id.date_done if self.picking_id.date_done else datetime.now()
            date = (date_done + timedelta(hours=7)).date()
            result.update({
                'date': date
            })
        return result