from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = "stock.move"


    name = fields.Char(
        'Description',
        required=False
    )
    x_origin = fields.Char(
        string='PO Origin',
        related='picking_id.origin',
    )
    x_scheduled_date = fields.Datetime(
        string='Scheduled Date',
        related='picking_id.scheduled_date',
    )
    x_default_code = fields.Char(
        string='Product Default Code',
        related='product_id.default_code',
    )
    free_qty_today = fields.Float(
        string="Available quantity",
        help='The information field used to enter the available inventory quantity of the selected product is displayed directly on the order.',
        copy=False
    )
    x_free_qty = fields.Float(
        string="Free quantity",
        compute='_compute_qty_free',
        copy=False
    )

    @api.depends('product_id', 'warehouse_id')
    def _compute_qty_free(self):
        for move in self:
            if move.location_id.usage == 'internal':
                move.x_free_qty = move.product_id.with_context(warehouse=move.location_id.warehouse_id.id).free_qty
            else:
                move.x_free_qty = 0

    def _generate_serial_numbers_from_existed_serial(self, next_serial, next_serial_count=False, location_id=False,
                                                     start_from=0, serial_length=False):
        """ This method will generate `lot_name` from a string (field
        `next_serial`) and create a move line for each generated `lot_name`.
        """
        self.ensure_one()
        if not location_id:
            location_id = self.location_dest_id
        lot_names = self.env['stock.lot'].generate_lot_names_from_existed_serial(next_serial,
                                                                                 next_serial_count or self.next_serial_count,
                                                                                 start_from=start_from,
                                                                                 serial_length=serial_length)
        existed_move_line_ids = self.env['stock.move.line'].sudo().search(
            [('product_id', '=', self.product_id.id), ('lot_name', 'like', f'{next_serial}%')]).mapped('lot_name')
        duplicate_lot_name = [lot_name['lot_name'] for lot_name in lot_names if
                              lot_name['lot_name'] in existed_move_line_ids]

        if duplicate_lot_name:
            raise UserError(f"Serial {', '.join(duplicate_lot_name)}" + _(" already exists."))

        field_data = [{'lot_name': lot_name['lot_name'], 'quantity': 1} for lot_name in lot_names]
        if self.picking_type_id.use_existing_lots:
            self._create_lot_ids_from_move_line_vals(field_data, self.product_id.id, self.company_id.id)
        move_lines_commands = self._generate_serial_move_line_commands(field_data)
        self.move_line_ids = move_lines_commands
        return True

    def _compute_product_available_qty(self):
        for line in self:
            free_qty_today = 0
            domain = [
                ('product_id', 'in', line.product_id.ids),
                ('on_hand', '=', True)
            ]
            product_stock = self.env['stock.quant'].search(domain).filtered(lambda r: r.location_id.usage == 'internal')
            if len(product_stock):
                for r in product_stock:
                    free_qty_today += r.available_quantity
            line.free_qty_today = free_qty_today

    @api.onchange('product_id')
    def _onchange_product_id_free_qty_today(self):
        if not self.product_id:
            return
        self._compute_product_available_qty()
