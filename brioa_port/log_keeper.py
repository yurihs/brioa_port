import pandas as pd

from datetime import datetime
from sqlalchemy.engine import Engine
from typing import Optional

from brioa_port.util.database import DATABASE_DATETIME_FORMAT
from brioa_port.schedule_parser import SCHEDULE_DATE_COLUMNS


class LogKeeper:
    LOGS_TABLE = 'logs'

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def has_entries(self) -> bool:
        return bool(self.engine.dialect.has_table(self.engine, self.LOGS_TABLE))

    def write_entries(self, date_retrieved: datetime, entries: pd.DataFrame) -> int:
        indexed_entries = entries.copy()
        indexed_entries['date_retrieved'] = date_retrieved
        indexed_entries = indexed_entries.set_index('date_retrieved')

        def is_entry_new(entry: pd.Series) -> bool:
            existing_entry = self.read_latest_entry_for_trip(entry['Viagem'])
            if existing_entry is not None:
                no_changes = entry.equals(existing_entry.drop('date_retrieved'))
                if no_changes:
                    return False
            return True

        if self.has_entries():
            new_entries = indexed_entries[indexed_entries.apply(is_entry_new, axis=1)]
        else:
            new_entries = indexed_entries

        if not new_entries.empty:
            new_entries.to_sql(self.LOGS_TABLE, con=self.engine, if_exists='append')

        return len(new_entries)

    def read_entries_for_trip(self, trip_name: str) -> Optional[pd.Series]:
        date_dict = {x: DATABASE_DATETIME_FORMAT for x in SCHEDULE_DATE_COLUMNS + ['date_retrieved']}
        df = pd.read_sql(
            f'select * from {self.LOGS_TABLE} where Viagem = ? order by date_retrieved desc',
            con=self.engine,
            params=(trip_name,),
            parse_dates=date_dict
        )
        return None if df.empty else df

    def read_latest_entry_for_trip(self, trip_name: str) -> Optional[pd.Series]:
        entries = self.read_entries_for_trip(trip_name)
        return None if entries is None else entries.iloc[0]

    def read_ships_at_port(self, arrives_before: datetime, sails_after: datetime) -> pd.DataFrame:
        date_dict = {x: DATABASE_DATETIME_FORMAT for x in ['TA', 'TB', 'TS']}

        max_arrival = arrives_before.strftime(DATABASE_DATETIME_FORMAT)
        min_sailing = sails_after.strftime(DATABASE_DATETIME_FORMAT)

        return pd.read_sql((
            "select\n"
            "   Berço, Navio, Viagem, ifnull(ETA, ATA) as TA, ifnull(ATB, ETB) as TB, ifnull(ATS, ETS) as TS,\n"
            "   ATA is NULL as TA_is_predicted, ATB is NULL as TB_is_predicted, ATS is NULL as TS_is_predicted\n"
            "from\n"
            f"   {self.LOGS_TABLE}\n"
            "where\n"
            "   TA <= datetime(?)\n"
            "   and (TS >= datetime(?) or TS = NULL)\n"
            "group by\n"
            "   Viagem\n"
            "having\n"
            "   date_retrieved = max(date_retrieved)\n"
            "order by\n"
            "   TA, TB, TS, logs.Navio, logs.Viagem"),
            con=self.engine,
            params=(max_arrival, min_sailing),
            parse_dates=date_dict
        )
