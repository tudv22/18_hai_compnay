from odoo import api, models, fields


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    base = fields.Selection(
        selection_add=[
            ('warehouse_cost', 'Warehouse Cost')
        ],
            ondelete={'warehouse_cost': 'set default'},
    )

    def _compute_base_price(self, product, quantity, uom, date, currency):
        for item in self:
            if not item.base == 'warehouse_cost':
                return super(PricelistItem, item)._compute_base_price(product, quantity, uom, date, currency)
            else:
                warehouse = self.env.context.get('x_warehouse_for_sh_cost')
                warehouse_cost = product.get_warehouse_wise_cost(warehouse)
                return warehouse_cost[0].cost if warehouse_cost else 1.0