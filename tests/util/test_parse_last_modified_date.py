from email.header import Header

from dateutil import tz

from brioa_port.util.request import parse_last_modified_date


def test_header_object():
    header = Header('Mon, 21 Oct 2015 23:29:00 GMT')
    parsed = parse_last_modified_date(header).astimezone(tz.UTC)
    assert parsed.year == 2015
    assert parsed.month == 10
    assert parsed.day == 21
    assert parsed.hour == 23
    assert parsed.minute == 29
    assert parsed.second == 0


def test_string():
    parsed = parse_last_modified_date('Mon, 21 Oct 2015 23:29:00 GMT').astimezone(tz.UTC)
    assert parsed.year == 2015
    assert parsed.month == 10
    assert parsed.day == 21
    assert parsed.hour == 23
    assert parsed.minute == 29
    assert parsed.second == 0


def test_empty():
    assert parse_last_modified_date('  ') is None
