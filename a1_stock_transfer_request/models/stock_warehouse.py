from odoo import api,fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    x_is_inter_company = fields.Boolean(
        string='Is inter-company',
        default=False,
    )

    @api.depends(lambda self: (self._rec_name,) if self._rec_name else ())
    def _compute_display_name(self):
        return super(StockWarehouse, self.sudo())._compute_display_name()

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
            return super(StockWarehouse, self.sudo()).web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order, count_limit=count_limit)
