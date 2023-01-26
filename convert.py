#
# Utility functions for parsing string and converting values
#

from .msg import dbg, info, warn, err
import datetime

def today_date():
    return datetime.datetime.today()

def today_string():
    '''Get the current date with single-digit month and day and 4-digit year

    :return: string, representing the current date
    '''
    today = today_date()
    return date_string(today)

def parse_date(dateStr):
    '''Get an object representing the given date in "m/d/Y" format

    :param dateStr: string, the date in "m/d/Y" format
    :return: datetime64 object representing the date
    '''
    # Append the current year if no year is given.
    firstSlash = dateStr.find("/")
    if firstSlash > -1 and firstSlash == dateStr.rfind("/"):
        dateStr += "/" + today_date().strftime("%Y")

    if dateStr.rfind("/") == len(dateStr) - 3:
        yearComponent = "%y"
    else:
        yearComponent = "%Y"

    date = datetime.datetime.strptime(dateStr, "%%m/%%d/%s" % yearComponent)
    return date

def date_string(date):
    # Strip potential leading zeros from each component (matches sheet format)
    month = date.strftime("%m").lstrip("0")
    day = date.strftime("%d").lstrip("0")
    year = date.strftime("%Y")
    return "/".join([month, day, year])

def parse_numeric(inputStr):
    '''Get a numeric prefix, including potential fraction part, from a string

    Ignores initial whitespace. Produces a warning and returns 0 and the full
    string (minus any initial whitespace) when no numeric input was encountered.
    :param inputStr: string to parse for a numeric prefix
    :return: (float, string) parsed number and remaining string portion
    '''
    inputStr = inputStr.lstrip()
    wholeNumberText = ""
    numeratorText = ""
    denominatorText = ""
    isNumerator = False
    isDenominator = False
    remaining = ""
    for i, c in enumerate(inputStr):
        if c.isdigit() or c == ".":
            if isDenominator:
                denominatorText += c
            elif isNumerator:
                numeratorText += c
            else:
                wholeNumberText += c
        elif not isNumerator and c == " ":
            if isDenominator and len(denominatorText) > 0:
                # A space after the denominator indicates we're done
                remaining = inputStr[i+1:]
                break
            isNumerator = True
        elif c == "/":
            if numeratorText == "":
                # The parsed "whole number" was actually the numerator
                numeratorText = wholeNumberText
                wholeNumberText = "0"
            isNumerator = False
            isDenominator = True
        elif wholeNumberText:
            # Already found numeric data, so done when we encounter nonnumeric
            remaining = inputStr[i:]
            break
            
    if wholeNumberText == "":
        warn("No numeric data found: %s" % inputStr)
        return 0, remaining
    else:
        number = float(wholeNumberText)

    if numeratorText != "":
        if denominatorText == "":
            warn("Unable to parse fractional numeric data: '%s'" % inputStr)
        else:
            fractionalNumber = float(numeratorText) / float(denominatorText)
            number += fractionalNumber

    return number, remaining

def parse_nonnumeric(inputStr):
    '''Get the next nonnumeric, whitespace-delimited word from the input

    :param inputStr: string to parse for a numeric prefix
    :return: (string, string) parsed word and remaining string portion
    '''
    inputStr = inputStr.lstrip()
    text = ""
    remaining = ""
    for i, c in enumerate(inputStr):
        if c.isdigit() or c.isspace():
            remaining = inputStr[i:]
            break
        text += c
    text = text.strip().rstrip(".")
    return text, remaining

def amount_to_grams(amount, indent=""):
    '''Parse a weight amount and convert it grams

    Warns and assumes the unit is grams if not given explicitly.
    :param amount: string, the weight amount to parse
    :param indent: string of whitespace to prefix any output (warning messages)
    :return: float, the weight converted to grams
    '''
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
    
