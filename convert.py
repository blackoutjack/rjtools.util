# Utility functions for parsing string and converting values

import numpy
import datetime

def parse_date(date_str):
    date_formatted = datetime.datetime.strptime(date_str, "%m/%d/%Y")
    return numpy.datetime64(date_formatted)

def parse_numeric(inputstr):
    inputstr = inputstr.strip()
    whole_number_text = ""
    numerator_text = ""
    denominator_text = ""
    is_numerator = False
    is_denominator = False
    remaining = ""
    for i, c in enumerate(inputstr):
        if c.isdigit() or c == ".":
            if is_denominator:
                denominator_text += c
            elif is_numerator:
                numerator_text += c
            else:
                whole_number_text += c
        elif not is_numerator and c == " ":
            if not whole_number_text:
                is_numerator = True
        elif c == "/":
            if numerator_text == "":
                # The parsed "whole number" was actually the numerator.
                numerator_text = whole_number_text
                whole_number_text = "0"
            is_numerator = False
            is_denominator = True
        elif whole_number_text:
                # Already found numeric data, so break at this point.
                remaining = inputstr[i:]
                break
            
    if whole_number_text == "":
        warn("No numeric data found: %s" % inputstr)
        return 0, remaining
    else:
        number = float(whole_number_text)

    if numerator_text != "":
        if denominator_text == "":
            warn("Unable to parse fractional numeric data: '%s'" % inputstr)
        else:
            fractional_number = float(numerator_text) / float(denominator_text)
            number += fractional_number

    return number, remaining

# Return the next "word" and the remaining string
def parse_nonnumeric(inputstr):
    inputstr = inputstr.strip()
    text = ""
    remaining = ""
    saw_space = False
    for i, c in enumerate(inputstr):
        if c.isdigit() or c == " ":
            remaining = inputstr[i:]
            break
        text += c
    text = text.strip().rstrip(".")
    return text, remaining

def amount_to_grams(amount):
    text = amount
    total = 0
    while text != "":
        amounti, text = parse_numeric(text)
        units, text = parse_nonnumeric(text)
        if units == "g":
            total += amounti
        elif units == "lb" or units == "#":
            total += amounti * 453.5924
        elif units == "oz":
            total += amounti * 28.34952
        else:
            raise TypeError("Unhandled units in '%s': %s" % (amount, units))
    return total
    
