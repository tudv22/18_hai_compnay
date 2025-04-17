import inflect

class NumberToVietnamese:
    units = ["", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]
    tens = ["", "mười", "hai mươi", "ba mươi", "bốn mươi", "năm mươi", "sáu mươi", "bảy mươi", "tám mươi", "chín mươi"]
    powers = ["", "nghìn", "triệu", "tỷ"]

    def convert(self, number):
        if number == 0:
            return "không"

        parts = []
        unit_index = 0
        while number > 0:
            part = number % 1000
            if part > 0:
                parts.append(
                    self.convert_part(part) + (" " + self.powers[unit_index] if self.powers[unit_index] else ""))
            number //= 1000
            unit_index += 1

        # Reverse the parts and join them with a space
        return ' '.join(reversed(parts)).strip()

    def convert_part(self, part):
        if part == 0:
            return ""
        hundreds = part // 100
        tens_units = part % 100
        tens = tens_units // 10
        units = tens_units % 10

        result = []

        # Hundreds place
        if hundreds > 0:
            result.append(self.units[hundreds] + " trăm")

        # Tens place
        if tens > 0:
            if tens == 1 and units > 0:  # Special case for 'mười'
                result.append("mười")
            else:
                result.append(self.tens[tens])

        # Units place
        if units > 0:
            if tens > 0:  # If there are tens, we write 'lăm' for 'five'
                if units == 5:
                    result.append("lăm")
                else:
                    result.append(self.units[units])
            else:
                # Special case: 'một' for 1 and 'năm' for 5 at the unit place
                if units == 1:
                    result.append("một")
                elif units == 5:
                    result.append("năm")
                else:
                    result.append(self.units[units])

        return ' '.join(result).strip()


def amount_to_vietnamese_text(amount, currency=None):
    # Initialize the converter
    converter = NumberToVietnamese()

    # Check if the amount is negative
    if amount < 0:
        return "Số tiền âm " + converter.convert(abs(amount)) + " đồng"
    if currency and currency != 'VND':
        return converter.convert(amount) + " " + currency
    # Convert the number to text and append "đồng"
    return converter.convert(amount) + " đồng"

def convert_usd_to_text(amount):
    # Create an inflect engine
    p = inflect.engine()

    # Separate dollars and cents
    dollars = int(amount)
    cents = round((amount - dollars) * 100)

    # Convert to words
    dollars_text = p.number_to_words(dollars).capitalize()
    cents_text = p.number_to_words(cents)

    # Construct the final result
    if dollars == 0 and cents == 0:
        return "Zero dollars"
    elif dollars == 0:
        return f"{cents_text} cents"
    elif cents == 0:
        return f"{dollars_text} dollars"
    else:
        return f"{dollars_text} dollars and {cents_text} cents"
