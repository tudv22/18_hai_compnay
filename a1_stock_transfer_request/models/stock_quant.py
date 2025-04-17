from odoo import fields,models

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False, qty=0):
        res = super(StockQuant, self)._gather(product_id, location_id, lot_id, package_id, owner_id, strict, qty)
        accepted_name = self.env.context.get('serial_current_name', False)
        if accepted_name:
            res = res.filtered(lambda q: q.lot_id.name in accepted_name)
        return res