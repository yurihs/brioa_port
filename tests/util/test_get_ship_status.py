import pytest
import pandas as pd

from datetime import datetime

from brioa_port.util.entry import ShipStatus, get_ship_status


@pytest.fixture
def ship_entry() -> pd.Series:
    return pd.Series({
        'TA': datetime(2010, 1, 1, 10, 0, 0),
        'TB': datetime(2010, 1, 1, 12, 0, 0),
        'TS': datetime(2010, 1, 2, 0, 0, 0),
    })


def test_yet_to_arrive_ship(ship_entry: pd.Series) -> None:
    assert get_ship_status(
        ship_entry,
        datetime(2010, 1, 1, 0, 0, 0)
    ) == ShipStatus.TO_ARRIVE


def test_arrived_ship(ship_entry: pd.Series) -> None:
    assert get_ship_status(
        ship_entry,
        datetime(2010, 1, 1, 11, 0, 0)
    ) == ShipStatus.ARRIVED


def test_berthed_ship(ship_entry: pd.Series) -> None:
    assert get_ship_status(
        ship_entry,
        datetime(2010, 1, 1, 13, 0, 0)
    ) == ShipStatus.BERTHED


def test_sailed_ship(ship_entry: pd.Series) -> None:
    assert get_ship_status(
        ship_entry,
        datetime(2010, 1, 2, 12, 0, 0)
    ) == ShipStatus.SAILED
