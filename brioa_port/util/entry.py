import pandas as pd

from datetime import datetime
from enum import Enum
from typing import Optional


class ShipStatus(Enum):
    UNKNOWN = -1
    TO_ARRIVE = 0
    ARRIVED = 1
    BERTHED = 2
    SAILED = 3


def get_ship_status(ship_entry: pd.Series, date: datetime) -> ShipStatus:
    """
    Determines the status of a ship from the dates in it's log entry,
    and a given date to compare, e.g. 'now'.

    Args:
        ship_entry: The ship entry, with the arrival, berthing, and sailing dates.
        date: What to compare the log dates with.

    Returns:
        The ShipStatus.
    """
    yet_to_arrive = ship_entry['TA'] >= date
    yet_to_berth = ship_entry['TB'] >= date
    yet_to_sail = ship_entry['TS'] >= date
    has_sailed = ship_entry['TS'] < date

    if yet_to_arrive:
        return ShipStatus.TO_ARRIVE
    if yet_to_berth:
        return ShipStatus.ARRIVED
    if yet_to_sail:
        return ShipStatus.BERTHED
    if has_sailed:
        return ShipStatus.SAILED

    return ShipStatus.UNKNOWN


def get_ship_berth_number(ship_entry: pd.Series) -> Optional[int]:
    """
    Converts the raw ship entry info into an nice number.

    Args:
        ship_entry: The log entry with the berth info.

    Returns:
        The berth number, or None if there isn't one.
    """
    if not pd.isnull(ship_entry['Berço']):
        return int(ship_entry['Berço'])
    return None
