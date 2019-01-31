#!/usr/bin/env python3
"""BRIOA Schedule Downloader

Usage:
    brioa_programacao.py update online <database_path> [--period <seconds>]
    brioa_programacao.py update from_file <file_path> <database_path> [--retrieved-at <date_retrieved>]
    brioa_programacao.py current <database_path>
    brioa_programacao.py trip <trip_name> <database_path>

Options:
    --period <seconds>  To constantly update the database, set the update frequency with this option.
    --retrieved-at <date_retrieved> The date/time that the information in the file is from.
                                    ISO 8601 Format: 2000-01-01 00:00:00
                                    By default, it's taken from the filename (unix timestamp, local time).

"""

import functools
import time
import pandas as pd
import schedule

from docopt import docopt
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, Optional

from brioa_port.util.datetime import make_delta_human_readable
from brioa_port.util.database import create_database_engine
from brioa_port.schedule_parser import parse_schedule_spreadsheet
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


def update_once(database_path: str) -> None:
    spreadsheet_url = 'http://www.portoitapoa.com.br/excel/'
    logkeeper = LogKeeper(create_database_engine(database_path))

    new_data = parse_schedule_spreadsheet(spreadsheet_url)
    date_retrieved = datetime.now()

    n_new_entries = logkeeper.write_entries(date_retrieved, new_data)
    print(date_retrieved.strftime('%Y-%m-%d %H:%M:%S'), end=': ')
    print(n_new_entries, 'new entry.' if n_new_entries == 1 else 'new entries.')


def cmd_update_online(args: Dict[str, str]) -> None:
    if args['--period'] is None:
        update_once(args['<database_path>'])
        return

    period_str = args['--period']
    try:
        period = int(period_str)
    except ValueError:
        print("Error: Invalid period.")
        return

    if period < 0:
        print("Error: Invalid period.")
        return

    schedule.every(period).seconds.do(functools.partial(update_once, args['<database_path>']))
    while True:
        schedule.run_pending()
        time.sleep(1)


def cmd_update_from_file(args: Dict[str, str]) -> None:
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))

    spreadsheet_path = Path(args['<file_path>'])

    new_data = parse_schedule_spreadsheet(str(spreadsheet_path))

    try:
        date_from_filename: Optional[datetime] = datetime.fromtimestamp(int(spreadsheet_path.stem))
    except (ValueError, OverflowError, OSError):
        date_from_filename = None

    if args['--retrieved-at'] is not None:
        date_from_args = datetime.strptime(args['--retrieved-at'], '%Y-%m-%d %H:%M:%S')
    else:
        date_from_args = None

    if date_from_args is None and date_from_filename is None:
        print((
            'Unable to infer file retrieval date from filename.\n'
            'Use a Unix timestamp as the filename, or specify the --retrieved-at option.'
        ))
        return

    date_retrieved = date_from_args if date_from_args is not None else date_from_filename

    n_new_entries = logkeeper.write_entries(date_retrieved, new_data)
    print(n_new_entries, 'new entry.' if n_new_entries == 1 else 'new entries.')


def cmd_current(args: Dict[str, str]) -> None:
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


def cmd_trip(args: Dict[str, str]) -> None:
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))
    if not logkeeper.has_entries():
        print("No entries found.")
        return

    entry = logkeeper.read_latest_entry_for_trip(args['<trip_name>'])
    if entry is None:
        print("Trip not found.")
        return

    def desc_event(action: str, date_expected: pd.Timestamp, date_actual: pd.Timestamp) -> str:
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

    if args['update'] and args['online']:
        cmd_update_online(args)
    if args['update'] and args['from_file']:
        cmd_update_from_file(args)
    elif args['current']:
        cmd_current(args)
    elif args['trip']:
        cmd_trip(args)


if __name__ == '__main__':
    main()
