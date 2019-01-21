import time

from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List


def get_unix_timestamp_from_local_datetime(date: datetime) -> int:
    return int(time.mktime(date.timetuple()))


def make_delta_human_readable(start_date: datetime, end_date: datetime, absolute: bool = False) -> str:
    if start_date == end_date:
        return 'no difference' if absolute else 'now'

    dates_descending = sorted((start_date, end_date), reverse=True)
    delta = relativedelta(dates_descending[0], dates_descending[1])

    attrs = ['years', 'months', 'days', 'hours', 'minutes']
    attr_string = ', '.join('%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1]) for attr in attrs if getattr(delta, attr))

    if absolute:
        return 'by ' + attr_string

    if start_date < end_date:
        return 'in ' + attr_string

    return attr_string + ' ago'
