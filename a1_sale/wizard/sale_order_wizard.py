from odoo import _, api, fields, models, tools


class SelectProductWizard(models.TransientModel):
    _name = 'sale.order.wizard'
    _description = 'Sale Order Wizard'

    product_ids = fields.Many2many('product.product', string="Select Products", required=True)

    def confirm_sale_product(self):
        active_id = self.env.context.get('active_ids', [])
        get_active_id = self.env['sale.order'].browse(active_id)

        if get_active_id.state == 'draft':
            for wizard in self:
                for data in wizard.product_ids:
                    self.env['sale.order.line'].create({
                        'product_id': data.id,
                        'order_id': get_active_id.id,
                        'state': 'draft',

                    })
        return True