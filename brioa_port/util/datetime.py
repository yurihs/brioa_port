import time
from datetime import datetime


def get_unix_timestamp(date: datetime) -> int:
    return int(time.mktime(date.timetuple()))
