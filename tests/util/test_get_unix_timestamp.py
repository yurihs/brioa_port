from datetime import datetime

from dateutil import tz

from brioa_port.util.datetime import get_unix_timestamp_from_local_datetime


def test_timezone_aware_date():
    bttf = datetime(2015, 10, 21, 23, 29, 0, tzinfo=tz.UTC).astimezone(tz.tzlocal())
    assert get_unix_timestamp_from_local_datetime(bttf) == 1445470140


def test_native_date():
    bttf = datetime(2015, 10, 21, 23, 29, 0, tzinfo=tz.UTC).astimezone(tz.tzlocal()).replace(tzinfo=None)
    assert get_unix_timestamp_from_local_datetime(bttf) == 1445470140
