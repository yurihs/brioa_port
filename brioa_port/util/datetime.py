import time

from datetime import datetime
from dateutil.relativedelta import relativedelta


def get_unix_timestamp_from_local_datetime(date: datetime) -> int:
    """
    Turns a datetime object into an unix epoch timestamp integer.
    """
    return int(time.mktime(date.timetuple()))


def make_delta_human_readable(start_date: datetime, end_date: datetime, absolute: bool = False) -> str:
    """
    Humanizes a timespan (difference between two datetime objects).
    Will show differences in years, month, days, hours, and minutes, as needed.
    The 'absolute' argument makes the output indifferent
    to the order of the start and end dates.

    Examples:
        2010-01-01, 2010-01-01 -> 'now'
        2010-01-01, 2010-01-01, absolute mode -> 'no difference'
        2010-01-01, 2010-01-02 -> 'in 1 day'
        2010-01-02, 2010-01-01 -> '1 day ago'
        2010-01-01, 2010-01-02, absolute mode -> 'in 1 day'
        2010-01-02, 2010-01-01, absolute mode -> 'in 1 day'
        2010-01-01 00:00:00, 2010-01-02 01:42:03 -> in 1 day, 1 hour, 42 minutes
    """
    if start_date == end_date:
        return 'no difference' if absolute else 'now'

    dates_descending = sorted((start_date, end_date), reverse=True)
    delta = relativedelta(dates_descending[0], dates_descending[1])

    attrs = ['years', 'months', 'days', 'hours', 'minutes']
    attr_string = ', '.join(
        '%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1])
        for attr in attrs if getattr(delta, attr)
    )

    if absolute:
        return 'by ' + attr_string

    if start_date < end_date:
        return 'in ' + attr_string

    return attr_string + ' ago'
