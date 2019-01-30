from datetime import datetime

from brioa_port.util.datetime import make_delta_human_readable


def test_positive_timespan() -> None:
    start_date = datetime(2010, 1, 1, 0, 0, 0)
    end_date = datetime(2010, 2, 11, 0, 0, 0)
    assert make_delta_human_readable(start_date, end_date) == 'in 1 month, 10 days'
    assert make_delta_human_readable(start_date, end_date, absolute=True) == 'by 1 month, 10 days'


def test_negative_timespan() -> None:
    start_date = datetime(2010, 2, 11, 0, 0, 0)
    end_date = datetime(2010, 1, 1, 0, 0, 0)
    assert make_delta_human_readable(start_date, end_date) == '1 month, 10 days ago'
    assert make_delta_human_readable(start_date, end_date, absolute=True) == 'by 1 month, 10 days'


def test_zero_timespan() -> None:
    start_date = datetime(2010, 1, 1, 0, 0, 0)
    end_date = start_date
    assert make_delta_human_readable(start_date, end_date) == 'now'
    assert make_delta_human_readable(start_date, end_date, absolute=True) == 'no difference'
