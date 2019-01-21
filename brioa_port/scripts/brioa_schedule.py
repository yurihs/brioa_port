#!/usr/bin/env python3
"""BRIOA Schedule Downloader

Usage:
    brioa_programacao.py update <database_path>
    brioa_programacao.py current <database_path>
    brioa_programacao.py trip <trip_name> <database_path>

"""

import sys
import pandas as pd
import numpy as np

from docopt import docopt
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta

from brioa_port.util.datetime import make_delta_human_readable
from brioa_port.util.database import create_database_engine, DATABASE_DATETIME_FORMAT
from brioa_port.schedule_parser import parse_schedule_spreadsheet, SCHEDULE_DATE_COLUMNS
from brioa_port.log_keeper import LogKeeper


def determine_entry_status(entry: pd.Series) -> str:
    now = datetime.now()

    if not pd.isnull(entry['Berço']):
        berco_desc = '#' + str(int(entry['Berço']))
    else:
        berco_desc = 'T.B.D.'

    yet_to_arrive = entry['TA'] >= now
    yet_to_berth = entry['TB'] >= now
    yet_to_sail = entry['TS'] >= now
    has_sailed = entry['TS'] < now

    human_delta = make_delta_human_readable

    prefix = ''
    unverified_prefix = '[UNVERIFIED] '

    if yet_to_arrive:
        if entry['TA_is_predicted']:
            prefix = unverified_prefix
        return prefix + f'Arrives {human_delta(now, entry["TA"])}'

    if yet_to_berth:
        if entry['TA_is_predicted']:
            prefix = unverified_prefix
        return prefix + f'Arrived, berths at {berco_desc} {human_delta(now, entry["TB"])}'

    if yet_to_sail:
        if entry['TB_is_predicted']:
            prefix = unverified_prefix
        return prefix + f'Berthed at {berco_desc}, sails {human_delta(now, entry["TS"])}'

    if has_sailed:
        if entry['TS_is_predicted']:
            prefix = unverified_prefix
        return prefix + f'Sailed {human_delta(now, entry["TS"])}'

    return 'Unknown'


def cmd_update(args):
    spreadsheet_url = 'http://www.portoitapoa.com.br/excel/'
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))

    new_data = parse_schedule_spreadsheet(spreadsheet_url)
    date_retrieved = datetime.now()

    n_new_entries = logkeeper.write_entries(date_retrieved, new_data)
    print(n_new_entries, 'new entry.' if n_new_entries == 1 else 'new entries.')


def cmd_current(args):
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))

    if not logkeeper.has_entries():
        print("No entries found.")
        return

    now = datetime.now()
    in_a_day = now + relativedelta(days=1)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    entries = logkeeper.read_ships_at_port(
        in_a_day,
        start_of_today
    )

    for index, entry in entries.iterrows():
        print(f'{entry["Navio"]} ({entry["Viagem"]}): {determine_entry_status(entry)}')


def cmd_trip(args):
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))
    if not logkeeper.has_entries():
        print("No entries found.")
        return

    entry = logkeeper.read_latest_entry_for_trip(args['<trip_name>'])
    if entry is None:
        print("Trip not found.")
        return


    def desc_event(action, date_expected, date_actual):
        date_expected = date_expected.to_pydatetime()
        date_actual = date_actual.to_pydatetime()

        if pd.isnull(date_actual):
            return 'Yet to ' + action.lower()

        delta = make_delta_human_readable(date_actual, date_expected, absolute=True)

        if date_actual > date_expected:
            return action + ' late ' + delta
        if date_actual < date_expected:
            return action + ' early ' + delta
        return action + ' on time'

    berth = '?' if pd.isnull(entry['Berço']) else str(int(entry['Berço']))

    print(f'{entry["Navio"]} (owned by {entry["Armador"]}, length {entry["Comprimento(m)"]}m)')
    if not pd.isnull(entry['ATA']):
        print(desc_event('Arrived', entry['ETA'], entry['ATA']), 'at', entry['ATA'])
    else:
        print(desc_event('Arrive', entry['ETA'], entry['ATA']), 'at', entry['ETA'])

    if not pd.isnull(entry['ATB']):
        print(desc_event('Berthed', entry['ETB'], entry['ATB']), f'at {entry["ATB"]} (#{berth})')
    else:
        print(desc_event('Berth', entry['ETB'], entry['ATB']), f'at {entry["ETB"]} (#{berth})')

    if not pd.isnull(entry['ATS']):
        print(desc_event('Sailed', entry['ETS'], entry['ATS']), 'at', entry['ATS'])
    else:
        print(desc_event('Sail', entry['ETS'], entry['ATS']), 'at', entry['ETS'])

def main() -> None:
    args = docopt(__doc__)

    if args['update']:
        cmd_update(args)
    elif args['current']:
        cmd_current(args)
    elif args['trip']:
        cmd_trip(args)

if __name__ == '__main__':
    main()
