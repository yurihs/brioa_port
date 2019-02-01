import pytest

from brioa_port.util.args import parse_period_arg


def test_valid_period() -> None:
    assert parse_period_arg('1') == 1


def test_negative_period() -> None:
    with pytest.raises(ValueError):
        assert parse_period_arg('-1')


def test_non_numeric_period() -> None:
    with pytest.raises(ValueError):
        assert parse_period_arg('1e5')
