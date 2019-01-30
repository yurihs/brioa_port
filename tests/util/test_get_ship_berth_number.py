import numpy as np
import pandas as pd

from brioa_port.util.entry import get_ship_berth_number


def test_valid_berth_number() -> None:
    assert get_ship_berth_number(pd.Series({
        'Berço': 1.0
    })) == 1


def test_invalid_berth_number() -> None:
    assert get_ship_berth_number(pd.Series({
        'Berço': np.nan
    })) is None
