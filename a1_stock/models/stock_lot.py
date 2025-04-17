from odoo import api, fields, models
from re import findall as regex_findall, split as regex_split


class StockLot(models.Model):
    _inherit = 'stock.lot'

    def generate_lot_names_from_existed_serial(self, first_lot, count, start_from=0, serial_length=False):
        """Generate `lot_names` from a string."""
        # We look if the first lot contains at least one digit.
        caught_initial_number = regex_findall(r"\d+", first_lot)
        if not caught_initial_number:
            return self.generate_lot_names_from_existed_serial(first_lot + "0", count, start_from=start_from,
                                                               serial_length=serial_length)
        # We base the series on the last number found in the base lot.
        initial_number = caught_initial_number[-1]
        if serial_length:
            padding = serial_length
        else:
            padding = len(initial_number)
        # We split the lot name to get the prefix and suffix.
        splitted = regex_split(initial_number, first_lot)
        # initial_number could appear several times, e.g. BAV-023B-S00001
        prefix = initial_number.join(splitted[:-1])
        suffix = splitted[-1]
        initial_number = int(initial_number)
        return [{
            'lot_name': '%s%s%s' % (prefix, str(initial_number + i).zfill(padding), suffix),
        } for i in range(start_from, start_from + count)]
