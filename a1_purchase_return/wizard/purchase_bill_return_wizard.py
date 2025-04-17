from odoo import fields, models, api, _
from odoo.exceptions import UserError


class PurchaseBillReturnWizard(models.TransientModel):
    _name = 'purchase.bill.return.wizard'
    _description = 'Purchase Bill Return Wizard'

    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Bill',
    )
    purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        string='Purchase Orders',
        required=True
    )
    return_line_ids = fields.One2many(
        comodel_name='purchase.return.line.wizard',
        inverse_name='wizard_bill_id',
        string='Lines'
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        compute='_compute_company_id',
    )
    selected_all = fields.Boolean(string='Selected all')
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string='Return Location',
    )
    picking_type_id = fields.Many2one(
        comodel_name='stock.picking.type',
        string='Picking type'
    )
    origin_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Picking',
    )

    @api.onchange('selected_all')
    def _onchange_selected_all(self):
        self.return_line_ids.write({'is_selected': self.selected_all})

    @api.onchange('location_id')
    def _onchange_location_id(self):
        if self.location_id:
            picking_type_id = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id', '=', self.location_id.warehouse_id.id)
            ], limit=1)
            self.picking_type_id = picking_type_id

    @api.onchange('purchase_ids')
    def _onchange_purchase_ids(self):
        self.ensure_one()
        if self.purchase_ids:
            self.return_line_ids = [(5, 0, 0)]
            for purchase in self.purchase_ids:
                for line in purchase.order_line:
                    self.return_line_ids |= self.return_line_ids.new({
                        'product_id': line.product_id.id,
                        'uom_id': line.product_uom.id,
                        'received_qty': line.qty_received,
                        'returned_qty': line.x_returned_qty,
                        'remaining_qty': line.qty_received - line.x_returned_qty,
                        'return_qty': 0,
                        'purchase_line_id': line.id,
                    })

    @api.depends('purchase_ids')
    def _compute_company_id(self):
        for record in self:
            if record.purchase_ids:
                record.company_id = record.purchase_ids[0].company_id
            else:
                record.company_id = False

    def button_create_return(self):
        self.ensure_one()
        return_line_ids = self.return_line_ids.filtered('is_selected')
        if not return_line_ids:
            raise UserError(_("Please select at least one line to return."))

        list_line_vals = {}
        for return_line_id in return_line_ids:
            if return_line_id.return_qty > 0:
                purchase = return_line_id.purchase_line_id.order_id
                if purchase not in list_line_vals:
                    list_line_vals[purchase] = []
                list_line_vals[purchase].append((0, 0, self._prepare_purchase_line_default_values(return_line_id)))
        if not list_line_vals:
            raise UserError(_("Please enter quantity to return."))
        list_purchases = []
        for purchase, line_vals in list_line_vals.items():
            if not line_vals:
                continue
            purchase_vals = self._prepare_purchase_default_values(purchase, line_vals)
            list_purchases.append(self.env['purchase.order'].create(purchase_vals))

        ctx = dict(self.env.context)
        return {
            'name': _('Returned Purchases'),
            'view_mode': 'form,list',
            'res_model': 'purchase.order',
            'domain': [('id', 'in', [p.id for p in list_purchases])],
            'type': 'ir.actions.act_window',
            'context': ctx,
            'views': [(self.env.ref('a1_purchase_return.purchase_order_tree_inherit_a1_purchase_return').id, "list"),
                      (self.env.ref('a1_purchase_return.a1_purchase_order_return_form').id, "form")
                      ],
        }

    def _prepare_purchase_default_values(self, purchase, line_vals):
        return {
            'x_type': 'return',
            'x_origin_purchase_id': purchase.id,
            'partner_id': purchase.partner_id.id,
            'currency_id': purchase.currency_id.id,
            'x_exchange_rate': purchase.x_exchange_rate,
            'x_origin_picking_id': self.origin_picking_id.id,
            'order_line': line_vals,
            'picking_type_id': self.picking_type_id.return_picking_type_id.id if self.picking_type_id else purchase.picking_type_id.return_picking_type_id.id,
            'state': 'draft',
        }

    def _prepare_purchase_line_default_values(self, return_line):
        vals = {
            'product_id': return_line.product_id.id,
            'name': return_line.product_id.name,
            'product_uom': return_line.uom_id.id,
            'product_qty': return_line.return_qty,
            'price_unit': return_line.purchase_line_id.price_unit,
            'x_origin_purchase_line_id': return_line.purchase_line_id.id,
            'taxes_id': [(6, 0, return_line.purchase_line_id.taxes_id.ids)],
            'discount': return_line.purchase_line_id.discount,
        }
        return vals