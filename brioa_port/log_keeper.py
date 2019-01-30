import pandas as pd

from datetime import datetime
from sqlalchemy.engine import Engine
from typing import Optional

from brioa_port.util.database import DATABASE_DATETIME_FORMAT
from brioa_port.schedule_parser import SCHEDULE_DATE_COLUMNS


class LogKeeper:
    """
    Interacts with a database of schedule logs,
    writing and reading to pandas dataframes originating from the ScheduleParser.

    Attributes:
        engine: The database engine that pandas will connect to.
    """
    LOGS_TABLE = 'logs'

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def has_entries(self) -> bool:
        """
        Checks if the database has been initialized.
        """
        return bool(self.engine.dialect.has_table(self.engine, self.LOGS_TABLE))

    def write_entries(self, date_retrieved: datetime, entries: pd.DataFrame) -> int:
        """
        Inserts new log entries into the database.

        Args:
            date_retrieved: Will be checked against existing entries, as to
                            not overwrite the logs with older information.
            entries: The new entries.

        Returns:
            The number of new entries which were inserted.
        """

        # Add the date_retrieved timestamp to the entries as an index,
        # so it can be differentiated from earlier entries in the database.
        indexed_entries = entries.copy()
        indexed_entries['date_retrieved'] = date_retrieved
        indexed_entries = indexed_entries.set_index('date_retrieved')

        def is_entry_new(entry: pd.Series) -> bool:
            """
            Determines if an entry has new information. For that, it must either:
                a. Be a new trip (trip name not in the database).
                b. Have at least one different value from the latest entry for that trip,
                   and Have a more recent date_retrieved than the existing one.

            Args:
                entry: The log entry to be compared.

            Returns:
                Whether it's new or not.
            """
            existing_entry = self.read_latest_entry_for_trip(entry['Viagem'])
            if existing_entry is not None:
                no_changes = entry.equals(existing_entry.drop('date_retrieved'))
                if no_changes:
                    return False
                existing_date_retrieved = existing_entry['date_retrieved'].to_pydatetime()
                if existing_date_retrieved >= date_retrieved:
                    return False
            return True

        if self.has_entries():
            # Database has existing entries.
            # Insert only new entries, aka the ones with new information.
            new_entries = indexed_entries[indexed_entries.apply(is_entry_new, axis=1)]
        else:
            # Database is empty. Insert everything.
            new_entries = indexed_entries

        if not new_entries.empty:
            new_entries.to_sql(self.LOGS_TABLE, con=self.engine, if_exists='append')

        return len(new_entries)

    def read_entries_for_trip(self, trip_name: str) -> Optional[pd.DataFrame]:
        """
        Queries the log entries for the given trip name, ordered from most to least recent.

        Args:
            trip_name: e.g. 'MCBF124'

        Returns:
            A dataframe with the log entries, or None if the trip is not found.
        """
        date_dict = {x: DATABASE_DATETIME_FORMAT for x in SCHEDULE_DATE_COLUMNS + ['date_retrieved']}
        df = pd.read_sql(
            f'select * from {self.LOGS_TABLE} where Viagem = ? order by date_retrieved desc',
            con=self.engine,
            params=(trip_name,),
            parse_dates=date_dict
        )
        return None if df.empty else df

    def read_latest_entry_for_trip(self, trip_name: str) -> Optional[pd.Series]:
        """
        Queries the latest log entry for the given trip name.

        Args:
            trip_name: e.g. 'MCBF124'

        Returns:
            The entry, or None if the trip is not found.
        """
        entries = self.read_entries_for_trip(trip_name)
        return None if entries is None else entries.iloc[0]

    def read_ships_at_port(self, arrives_before: datetime, sails_after: datetime) -> pd.DataFrame:
        """
        Queries the ships present at the port in a given date/time range.
        Includes, ships that have arrived, berthed, or recently sailed (left).

        Args:
            arrives_before: Maximum threshold for the arrival date/time.
                            e.g. include ships that arrived since X.
            sails_after: Minimum threshold for the sailing date/time.
                         e.g. include ships that will be in the port until X.

        Returns:
            A dataframe contaiing the latest log entries for the relevant ships.
            Columns:
                Berço: berth number (may often be NaN, i.e. not determined)
                Navio: ship name
                Viagem: trip name
                TA: time of arrival
                TB: time of berthing
                TS: time of sailing
                TA_is_predicted: indicates if TA is actual (confirmed time), or an estimation.
                TB_is_predicted: indicates if TB is actual (confirmed time), or an estimation.
                TS_is_predicted: indicates if TS is actual (confirmed time), or an estimation.
        """
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
