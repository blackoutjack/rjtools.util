#
# Utility functions for parsing string and converting values
#

from .msg import dbg, info, warn, err
import numpy
import datetime

def today_date():
    today = datetime.datetime.today()
    # Strip potential leading zeros from each component (matches sheet format)
    month = today.strftime("%m").lstrip("0")
    day = today.strftime("%d").lstrip("0")
    year = today.strftime("%Y")
    return "/".join([month, day, year])

def parse_date(date_str):
    date_formatted = datetime.datetime.strptime(date_str, "%m/%d/%Y")
    return numpy.datetime64(date_formatted)

def parse_numeric(inputstr):
    inputstr = inputstr.lstrip()
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
            if is_denominator and len(denominator_text) > 0:
                # A space after the denominator indicates we're done.
                remaining = inputstr[i+1:]
                break
            is_numerator = True
        elif c == "/":
            if numerator_text == "":
                # The parsed "whole number" was actually the numerator.
                numerator_text = whole_number_text
                whole_number_text = "0"
            is_numerator = False
            is_denominator = True
        elif whole_number_text:
            # Already found numeric data, so done when we encounter nonnumeric.
            remaining = inputstr[i:]
            break
            
    dbg("WHOLE NUMBER TEXT: %r" % whole_number_text)
    dbg("NUMERATOR TEXT: %r" % numerator_text)
    dbg("DENOMINATOR TEXT: %r" % denominator_text)
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
    inputstr = inputstr.lstrip()
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

def amount_to_grams(amount, indent=""):
    text = amount
    total = 0
    if amount == "":
        warn("No amount specified", indent)
    while text != "":
        amounti, text = parse_numeric(text)
        units, text = parse_nonnumeric(text)
        if units == "":
            warn("Units not specified, assuming grams: %s" % amount, indent)
            total += amounti
        elif units == "g":
            total += amounti
        elif units == "lb" or units == "#":
            total += amounti * 453.5924
        elif units == "oz":
            total += amounti * 28.34952
        else:
            raise TypeError("Unhandled units in '%s': %s" % (amount, units))
    return total
    
