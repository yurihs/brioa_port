import pandas as pd

SCHEDULE_DATE_COLUMNS = ['Abertura do Gate', 'Deadline', 'ETA', 'ATA', 'ETB', 'ATB', 'ETS', 'ATS']


def parse_dates(orig_df: pd.DataFrame) -> pd.DataFrame:
    """
    Parses the date format that the schedule spreadsheet uses
    into proper datetime objects.

    Returns:
        A new data frame with the parsed dates.
    """
    df = orig_df.copy()

    date_format = '%d/%m/%Y %H:%M:%S'
    for date_column in SCHEDULE_DATE_COLUMNS:
        df[date_column] = pd.to_datetime(df[date_column], format=date_format)

    return df


def normalize_ship_name(ship_name: str) -> str:
    """
    Removes the redundant "trip name" after the ship name.

    Args:
        ship_name: The raw string, e.g. 'BOATY MCBOATFACE - MCBF1234'
    Returns:
        The normalized name, e.g. 'BOATY MCBOATFACE'
    """
    if ' - ' not in ship_name:
        return ship_name
    return ship_name.split(' - ')[0]


def parse_schedule_spreadsheet(path: str) -> pd.DataFrame:
    """
    Applies all the parsing and normalization steps to the raw
    schedule spreadsheet.

    Args:
        path: Where to read the spreadsheet from
    Returns:
        A dataframe with the parsed data.
    """
    df = pd.read_excel(path)
    df = parse_dates(df)
    df['Navio'] = df['Navio'].apply(normalize_ship_name)
    return df
