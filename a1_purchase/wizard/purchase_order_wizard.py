from odoo import _, api, fields, models, tools


class PurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'
    _description = 'Purcahse Order Wizard'

    product_ids = fields.Many2many('product.product', string="Select Products", required=True)

    def confirm_purchase_product(self):
        active_id = self.env.context.get('active_ids', [])
        get_active_id = self.env['purchase.order'].browse(active_id)

        if get_active_id.state == 'draft':
            for wizard in self:
                for data in wizard.product_ids:
                    self.env['purchase.order.line'].create({
                        'product_id': data.id,
                        'order_id': get_active_id.id,

                    })
        return True