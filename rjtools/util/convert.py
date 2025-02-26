"""
Utility functions for converting values to and from strings
"""

import datetime
import html
import math

from .msg import warn


def date_string(date):
    """
    Convert the given date or datetime into an ISO string representing the date

    :param date: datetime.date|datetime.datetime, date object to convert
    :raises TypeError: when the date is not a datetime/date object or None
    :return: ISO string representing the date, or None if given None
    :rtype: str|None
    """
    if date is None: return None

    if not isinstance(date, (datetime.date, datetime.datetime)):
        msg = "Non-date value to provided: {date}"
        raise TypeError(msg)

    return "%s-%s-%s" % (
        date.strftime("%Y"),
        date.strftime("%m"),
        date.strftime("%d"))


def date_user_string(date):
    """
    Convert the given date or datetime into a American date string

    :param date: datetime.date|datetime.datetime, date object to convert
    :raises TypeError: when the date is not a datetime/date object or None
    :return: ISO string representing the date, or None if given None
    :rtype: str|None
    """
    if date is None: return None

    if not isinstance(date, (datetime.date, datetime.datetime)):
        msg = "Non-date value to provided: {date}"
        raise TypeError(msg)

    # Strip potential leading zeros from each component (matches sheet format)
    month = date.strftime("%m").lstrip("0")
    day = date.strftime("%d").lstrip("0")
    year = date.strftime("%Y")
    return "/".join([month, day, year])


def timestamp_string(timestamp):
    """
    Get the current time in ISO format

    :param timestamp: datetime.datetime, the timestamp to convert
    :raises TypeError: when the date is not a datetime object or None
    :return: the timestamp in ISO format
    :rtype: str
    """
    if timestamp is None: return None

    if not isinstance(timestamp, datetime.datetime):
        msg = "Non-timestamp value to provided: {timestamp}"
        raise TypeError(msg)

    return "%s-%s-%s %s:%s:%s" % (
        timestamp.strftime("%Y"),
        timestamp.strftime("%m"),
        timestamp.strftime("%d"),
        timestamp.strftime("%H"),
        timestamp.strftime("%M"),
        timestamp.strftime("%S"),
    )


def now_time():
    """
    Get the current time

    :return: the current time
    :rtype: datetime.datetime
    """
    return datetime.datetime.now()


def today_date():
    """
    Get the current date

    :return: datetime object representing the current date
    :rtype: datetime.datetime
    """
    return datetime.date.today()


def now_string():
    """
    Get the current time in ISO format

    :return: the current time
    :rtype: string
    """
    now = now_time()
    return timestamp_string(now)


def today_string():
    """
    Get the current date in ISO format

    :return: the current date in ISO format
    :rtype: string
    """
    today = today_date()
    return date_string(today)


def today_user_string():
    """
    Get the current date with 1-or-2-digit month and day and 4-digit year

    :return: string, representing the current date
    """
    today = today_date()
    return date_user_string(today)


def _date_from_datetime(dateTime):
    dateStrISO = date_string(dateTime)
    return datetime.date.fromisoformat(dateStrISO)


def _date_from_string(dateStr, form):
    dateTime = datetime.datetime.strptime(dateStr, form)
    return _date_from_datetime(dateTime)


def parse_date(dateStr, form="%Y-%m-%d"):
    """
    Get an object representing the given date

    :param dateStr: string, the date in format specified by ``form``, defaults
        to ``"YYYY-mm-dd"``
    :param form: string, format to use for parsing ``dateStr``

    :raises ValueError: when an unparsable date or invalid format are given
    :return: datetime object representing the date
    :rtype: datetime.date
    """
    if dateStr is None:
        msg = "Empty date value"
        raise ValueError(msg)

    if not isinstance(dateStr, str):
        msg = f"Unable to parse non-string date value: {dateStr}"
        raise ValueError(msg)

    if dateStr == "":
        msg = "Empty date value"
        raise ValueError(msg)

    # Can also raise ValueError
    return _date_from_string(dateStr, form)


def parse_iso_date(dateISO):
    """
    Get an object representing the date given in "YYYY-mm-dd" format

    :param dateISO: string, the date in ISO format

    :raises ValueError: when an unparsable date or invalid format are given
    :return: datetime object representing the date
    :rtype: datetime.date
    """
    return parse_date(dateISO, "%Y-%m-%d")


def parse_user_date(dateStr):
    """
    Get an object representing the possibly empty date given in American format

    :param dateStr: string|None, the date as "m/d/Y", "m/d/y", "m/d" or empty
    :raises ValueError: when an unparsable date is given
    :raises TypeError: when the given date is not a string or None
    :return: object representing the date
    :rtype: datetime.date
    """
    if dateStr is None: return None

    if not isinstance(dateStr, str):
        msg = f"Unable to parse non-string date value: {dateStr}"
        raise TypeError(msg)

    if dateStr == "": return ""

    # Append the current year if no year is given.
    firstSlash = dateStr.find("/")
    if firstSlash > -1 and firstSlash == dateStr.rfind("/"):
        dateStr += "/" + today_date().strftime("%Y")

    if dateStr.rfind("/") == len(dateStr) - 3:
        yearComponent = "%y"
    else:
        yearComponent = "%Y"

    # Can raise ValueError
    return _date_from_string(dateStr, f"%m/%d/{yearComponent}")


def iso_to_user_date(dateISO, doWarn=True):
    """
    Convert ISO date string into American date ("m/d/Y" format)

    :param dateISO: string, date in ISO format
    :param doWarn: bool, emit warning if the date format is not as expected
    :return: date represented in American format
    :rtype: str
    """
    try:
        return date_user_string(parse_iso_date(dateISO))
    except ValueError as ex:
        if doWarn:
            warn(f"Error while parsing ISO date to display date: {str(ex)}")
        return None


def parse_timestamp(timestamp, form="%Y-%m-%d %H:%M:%S"):
    """
    Create a datetime object representing the timestamp string

    :param timestamp: string, the timestamp in the given format
    :param form: string, format to expect when parsing, defaults to
        ``"%Y-%m-%d %H:%M:%S"``
    :raises ValueError: when an unparsable date or invalid format are given
    :raises TypeError: when the timestamp is not a string or None
    :return: datetime.datetime object representing the date
    :rtype: datetime.datetime
    """
    if timestamp is None:
        msg = "Empty timestamp value"
        raise TypeError(msg)

    if not isinstance(timestamp, str):
        msg = f"Unable to parse non-string timestamp value: {timestamp}"
        raise TypeError(msg)

    if timestamp == "":
        msg = "Empty timestamp value"
        raise ValueError(msg)

    # Can raise ValueError
    return datetime.datetime.strptime(timestamp, form)


def parse_date_idem(dateRepr):
    """
    Get a datetime object representing the date given in various formats

    :param dateRepr: str|datetime.date(time)|None, date in various formats
    :return: datetime.datetime object representing the date, or None if unable
        to parse the date
    :rtype: datetime.datetime|None
    """
    # Float may occur with errors, where the value becomes NaN
    if dateRepr is None or isinstance(dateRepr, float):
        return None

    if isinstance(dateRepr, datetime.datetime):
        return _date_from_datetime(dateRepr)

    if isinstance(dateRepr, datetime.date):
        return dateRepr

    if not isinstance(dateRepr, str):
        msg = f"Unable to parse non-string date value: {dateRepr}"
        raise ValueError(msg)

    try:
        return parse_iso_date(dateRepr)
    except ValueError:
        pass  # Try next format

    try:
        return parse_user_date(dateRepr)
    except ValueError:
        return None  # Give up


def parse_digits(inputStr):
    """
    Get any leading digits from the input string

    :param inputStr: string to parse for leading digits
    :raises TypeError: when the input is not a string
    :return: (string, string) parsed digits and remaining string portion
    """
    if not isinstance(inputStr, str):
        msg = f"Unable to parse digits from non-string: {inputStr}"
        raise TypeError(msg)

    wholeNumberText = ""
    remaining = ""
    for i, c in enumerate(inputStr):
        if c.isdigit():
            wholeNumberText += c
        else:
            remaining = inputStr[i:]
            break
    return wholeNumberText, remaining


def parse_numeric(inputStr):
    """
    Get a numeric prefix, including potential fraction part, from a string

    Ignores initial whitespace.

    :param inputStr: string to parse for a numeric prefix
    :raises ValueError: when no numeric data is found or fractional data
        cannot be parsed
    :return: (float, string), parsed number and remaining string portion
    """
    inputStr = inputStr.lstrip()
    wholeNumberText = ""
    numeratorText = ""
    denominatorText = ""
    inNumerator = False
    inDenominator = False
    remaining = ""
    for i, c in enumerate(inputStr):
        if c.isdigit() or c == ".":
            if inDenominator:
                denominatorText += c
            elif inNumerator:
                numeratorText += c
            else:
                wholeNumberText += c
        elif not inNumerator and c == " ":
            if inDenominator and len(denominatorText) > 0:
                # A space after the denominator indicates we're done
                remaining = inputStr[i+1:]
                break
            inNumerator = True
        elif c == "/":
            if numeratorText == "":
                # The parsed "whole number" was actually the numerator
                numeratorText = wholeNumberText
                wholeNumberText = "0"
            inNumerator = False
            inDenominator = True
        elif wholeNumberText:
            # Already found numeric data, so done when we encounter nonnumeric
            remaining = inputStr[i:]
            break

    if wholeNumberText == "":
        raise ValueError(f"No numeric data found: {inputStr}")

    number = float(wholeNumberText)

    if numeratorText != "":
        if denominatorText == "":
            raise ValueError(
                f"Unable to parse fractional numeric data: '{inputStr}'")

        fractionalNumber = float(numeratorText) / float(denominatorText)
        number += fractionalNumber

    return number, remaining


def parse_nonnumeric(inputStr):
    """Get the next nonnumeric, whitespace-delimited word from the input

    :param inputStr: string to parse for a numeric prefix
    :return: (string, string), parsed word and remaining string portion
    """
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


def amount_to_grams(amount, nonFatalErrors:list|None=None):
    """
    Parse a weight amount and convert it grams

    Provides a non-fatal error and assumes the unit is grams if unit is not
        given explicitly in `amount`.
    :param amount: string, the weight amount to parse
    :param nonFatalErrors: list, a list to collect non-fatal errors
    :raises ValueError, when unrecognized units are provided
    :return: float, the weight converted to grams
    """

    if nonFatalErrors is None: nonFatalErrors = []

    amount = amount.strip()
    text = amount
    total = 0
    if text == "":
        nonFatalErrors.append("No amount specified, assuming zero")
        return 0
    while text != "":
        amounti, text = parse_numeric(text)
        units, text = parse_nonnumeric(text)
        if units == "":
            # "0" can be interpreted as 0 grams without warning
            if amount != "0":
                nonFatalErrors.append(
                    "Units not specified in '{amount}', assuming grams")
                total += amounti
        elif units == "g":
            total += amounti
        elif units in ["lb", "#"]:
            total += amounti * 453.5924
        elif units == "oz":
            total += amounti * 28.34952
        else:
            raise ValueError("Unhandled units in '{amount}': '{units}'")
    return math.floor(total)


def alpha(number, lower=False):
    """
    Convert a number to an spreadsheet column letter

    :param num: int, the number 1-26 to convert to letter
    :raises TypeError: when ``num`` is not an integer
    :raises ValueError: when ``num`` is not in the range 1-26
    :param lower: bool, whether to produce lowercase letter, defaults to False
    :return: the letter corresponding to the number
    :rtype: str
    """
    if not isinstance(number, int):
        msg = f"Unable to convert non-integer to letter: {number}"
        raise TypeError(msg)

    # %%% Could handle cases where num > 26 as "AA", "AB" and so forth
    if number not in range(1, 27):
        msg = f"Number out of range for conversion to letter: {number}"
        raise ValueError(msg)

    shift = 96 if lower else 64
    return chr(number + shift)


def num(letter):
    """
    Convert a spreadsheet column letter to a 1-indexed number

    :param letter: string, the letter to convert to a number
    :raises TypeError: when ``letter`` is not a string
    :raises ValueError: when ``letter`` is not a single character
    :return: the number corresponding to the letter
    :rtype: int
    """
    if not isinstance(letter, str):
        msg = f"Unable to convert non-string to number: {letter}"
        raise TypeError(msg)

    # %%% Handle double/triple/etc letters ("AA"=27, "AB"=28 and so forth)
    if len(letter) != 1:
        msg = f"Unable to convert multi-character string to number: {letter}"
        raise ValueError(msg)

    lower = letter.lower() == letter
    shift = 96 if lower else 64
    return ord(letter) - shift


def parse_range(sheetRange):
    """
    Parse a spreadsheet range string into its components: sheet name, start
        cell and optional end cell

    :param sheetRange: string, the range to parse
    :return: (string, (int, int|None), (int, int|None)), the sheet name, start
        cell and end cell coordinates (with columns represented as numbers, not
        letters)
    """
    if not isinstance(sheetRange, str):
        msg = f"Unable to parse non-string range: {sheetRange}"
        raise TypeError(msg)

    rangeParts = sheetRange.split('!')
    if len(rangeParts) < 2:
        sheetName = ""
        cellRange = rangeParts[0]
    else:
        sheetName = rangeParts[0]
        cellRange = rangeParts[1]

    cellRangeParts = cellRange.split(":")
    if len(cellRangeParts) < 2:
        rangeStart = cellRangeParts[0]
        rangeEnd = None
    else:
        rangeStart = cellRangeParts[0]
        rangeEnd = cellRangeParts[1]

    startColumn, startRow = parse_nonnumeric(rangeStart)

    if rangeEnd is None:
        endColumn = None
        endRow = None
    else:
        endColumn, endRow = parse_nonnumeric(rangeEnd)

    try:
        startRow = int(startRow)
    except (TypeError, ValueError) as ex:
        msg = f"Unable to parse start row from '{startRow}': {str(ex)}"
        raise ValueError(msg)

    if endRow in [None, ""]:
        endRow = None
    else:
        try:
            endRow = int(endRow)
        except (TypeError, ValueError) as ex:
            msg = f"Unable to parse end row from '{endRow}': {str(ex)}"
            warn(msg)
            endRow = None

    # Convert column letters to numbers
    startColumn = num(startColumn)
    endColumn = num(endColumn)

    return sheetName, (startColumn, startRow), (endColumn, endRow)


def html_escape(val):
    """
    Escape the given value for HTML display

    :param val: string|None, the value to escape
    :return: string, the escaped value
    """
    if val is None:
        return ""
    return html.escape(val)
