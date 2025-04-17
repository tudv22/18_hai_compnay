from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date


class StockTransferRequestLine(models.Model):
    _name = 'stock.transfer.request.line'
    _description = 'Transfer Request Line'

    request_id = fields.Many2one(
        'stock.transfer.request',
        string='Stock Transfer Request',
        required=True,
        ondelete='cascade'
    )
    expected_date = fields.Datetime(
        string='Expected date',
        related='request_id.expected_date'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='request_id.company_id'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        copy=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        related='product_id.uom_id',
        string='Uom'
    )
    transfer_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        related='request_id.transfer_warehouse_id',
        string='Transfer warehouse',
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        related='transfer_warehouse_id.lot_stock_id',
    )
    dest_warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Dest warehouse',
        required=True,
    )
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Location dest',
        related = 'dest_warehouse_id.lot_stock_id',
    )
    request_qty = fields.Float(
        string="Request quantity",
        default=1,
        required=True,
        copy=False
    )
    export_qty = fields.Float(
        string="Export quantity",
        default=0,
        compute='_compute_quantity',
        store=True,
        copy=False
    )
    receive_qty = fields.Float(
        string="Receive quantity",
        default=0,
        compute='_compute_quantity',
        store=True,
        copy=False
    )
    remaining_qty = fields.Float(
        string="Quantity remaining",
        compute='compute_quantity_remaining',
        store=True,
        copy=False
    )
    stock_move_ids = fields.One2many(
        comodel_name='stock.move',
        inverse_name='x_transfer_request_line_id',
        string='Stock move',
        copy=False
    )
    quantity_in_stock = fields.Float(
        string="Quantity in stock",
        related='product_id.qty_available',
        store=True,
        copy=False
    )

    @api.onchange('product_id', 'transfer_warehouse_id')
    def _onchange_quantity_in_stock(self):
        for line in self:
            if line.product_id and line.transfer_warehouse_id:
                qty_available = line.product_id.with_context(warehouse=line.transfer_warehouse_id.id).qty_available
                line.quantity_in_stock = qty_available

    @api.onchange('product_id')
    def onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.uom_id = line.product_id.uom_id.id

    @api.depends('stock_move_ids.state', 'stock_move_ids')
    def _compute_quantity(self):
        for line in self:
            export_qty = 0
            receive_qty = 0
            for move in line.stock_move_ids:
                if move.state != 'done':
                    continue
                if move.location_dest_id.usage == 'transit':
                    export_qty += move.quantity
                else:
                    receive_qty += move.quantity
            line.export_qty = export_qty
            line.receive_qty = receive_qty

    @api.depends('request_qty', 'export_qty', 'receive_qty')
    def compute_quantity_remaining(self):
        for line in self:
            line.remaining_qty = line.request_qty - line.receive_qty

    @api.constrains('request_qty')
    def constrains_request_qty(self):
        for line in self:
            if line.request_qty <= 0:
                raise ValidationError(_("Request quantity should not be less than or equal to 0 !!"))

    def _prepare_stock_move_vals(self):
        return {
            'name': (self.product_id.display_name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date.today(),
            'date_deadline': self.expected_date,
            'location_id': False,
            'location_dest_id': False,
            'partner_id': False,
            'move_dest_ids': False,
            'state': 'draft',
            'x_transfer_request_line_id': self.id,
            'company_id': self.company_id.id,
            'price_unit': False,
            'picking_type_id': False,
            'origin': self.request_id.name,
            'warehouse_id': False,
            'product_uom_qty': self.request_qty,
            'quantity': self.request_qty,
            'product_uom': self.product_id.uom_id.id,
        }
