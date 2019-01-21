import pandas as pd

from pathlib import Path

SCHEDULE_DATE_COLUMNS = ['Abertura do Gate', 'Deadline', 'ETA', 'ATA', 'ETB', 'ATB', 'ETS', 'ATS']


def parse_dates(orig_df: pd.DataFrame) -> pd.DataFrame:
    date_format = '%d/%m/%Y %H:%M:%S'

    df = orig_df.copy()

    for date_column in SCHEDULE_DATE_COLUMNS:
        df[date_column] = pd.to_datetime(df[date_column], format=date_format)

    return df


def normalize_ship_name(ship_name: str) -> str:
    if ' - ' not in ship_name:
        return ship_name
    return ship_name.split(' - ')[0]


def parse_schedule_spreadsheet(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = parse_dates(df)
    df['Navio'] = df['Navio'].apply(normalize_ship_name)
    return df
