import time
from datetime import datetime


def get_unix_timestamp_from_local_datetime(date: datetime) -> int:
    return int(time.mktime(date.timetuple()))
