from odoo import _, api, fields, models, tools

class StockPickingWizard(models.TransientModel):
    _name = 'stock.picking.wizard'
    _description = 'Stock Move Wizard'

    product_ids = fields.Many2many('product.product', string="Select Products", required=True)

    def confirm_picking_product(self):
        active_id = self.env.context.get('active_ids', [])
        get_active_id = self.env['stock.picking'].browse(active_id)

        if get_active_id.state == 'draft':
            for wizard in self:
                for data in wizard.product_ids:
                    self.env['stock.move'].create({
                        'name': data.name,
                        'product_id': data.id,
                        'picking_id': get_active_id.id,
                        'location_id': get_active_id.location_id.id,
                        'location_dest_id': get_active_id.location_dest_id.id

                    })
        return True
