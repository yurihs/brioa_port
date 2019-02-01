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
import logging
import sys

from docopt import docopt
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Dict, Optional

from brioa_port.util.datetime import make_delta_human_readable
from brioa_port.util.database import create_database_engine
from brioa_port.util.entry import get_ship_status, get_ship_berth_number, ShipStatus
from brioa_port.util.args import parse_period_arg
from brioa_port.schedule_parser import parse_schedule_spreadsheet
from brioa_port.log_keeper import LogKeeper


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def determine_entry_status(entry: pd.Series) -> str:
    """
    Takes the raw data from a ship entry and presents a human readable status.
    Uses the arrival, berthing, and sailing dates to determine the status of the ship.
    """
    # Use the current date to compare the with the others
    # Store it so that it's consistent over the runtime of the function
    now = datetime.now()

    status = get_ship_status(entry, now)

    berco = get_ship_berth_number(entry)
    if berco is None:
        berco_desc = 'T.B.D.'
    else:
        berco_desc = '#' + str(berco)

    if status == ShipStatus.TO_ARRIVE:
        is_prediction = entry['TA_is_predicted']
        status_desc = f'Arrives {make_delta_human_readable(now, entry["TA"])}'

    elif status == ShipStatus.ARRIVED:
        is_prediction = entry['TA_is_predicted']
        status_desc = f'Arrived, berths at {berco_desc} {make_delta_human_readable(now, entry["TB"])}'

    elif status == ShipStatus.BERTHED:
        is_prediction = entry['TB_is_predicted']
        status_desc = f'Berthed at {berco_desc}, sails {make_delta_human_readable(now, entry["TS"])}'

    elif status == ShipStatus.SAILED:
        is_prediction = entry['TS_is_predicted']
        status_desc = f'Sailed {make_delta_human_readable(now, entry["TS"])}'

    else:
        is_prediction = False
        status_desc = 'Unknown'

    if is_prediction:
        return '[PREDICTION] ' + status_desc

    return status_desc


def update_online_once(database_path: str) -> None:
    spreadsheet_url = 'http://www.portoitapoa.com.br/excel/'
    logkeeper = LogKeeper(create_database_engine(database_path))

    new_data = parse_schedule_spreadsheet(spreadsheet_url)
    date_retrieved = datetime.now()

    n_new_entries = logkeeper.write_entries(date_retrieved, new_data)

    n_new_entries_str = '1 new entry' if n_new_entries == 1 else f'{n_new_entries} new entries'
    logging.info(f'{date_retrieved.strftime("%Y-%m-%d %H:%M:%S")}: {n_new_entries_str}')


def cmd_update_online(args: Dict[str, str]) -> None:
    """
    Updates a given database by downloading the current schedule spreadsheet
    from the website.
    Will run only once, or in a loop, depending on if a period is specified.
    """
    # No period specified. Do it once.
    if args['--period'] is None:
        update_online_once(args['<database_path>'])
        return

    # Handle period option
    try:
        period = parse_period_arg(args['--period'])
    except ValueError as e:
        logger.critical("Error: %s", e)
        sys.exit(1)

    schedule.every(period).seconds.do(
        functools.partial(update_online_once, args['<database_path>'])
    )
    while True:
        schedule.run_pending()
        time.sleep(1)


def cmd_update_from_file(args: Dict[str, str]) -> None:
    """
    Updates a given database by reading from a given spreadsheet file.
    The date of retrieval for the information in the spreadsheet can be
    inferred from the filename, or specified from an option.
    """
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))

    spreadsheet_path = Path(args['<file_path>'])
    new_data = parse_schedule_spreadsheet(str(spreadsheet_path))

    # Try to parse a date from the filename
    try:
        date_from_filename: Optional[datetime] = datetime.fromtimestamp(int(spreadsheet_path.stem))
    except (ValueError, OverflowError, OSError):
        date_from_filename = None

    # Try to parse a date from the CLI option
    if args['--retrieved-at'] is not None:
        date_from_args = datetime.strptime(args['--retrieved-at'], '%Y-%m-%d %H:%M:%S')
    else:
        date_from_args = None

    # If no valid date is found, the update cannot happen
    if date_from_args is None and date_from_filename is None:
        logging.critical((
            'Unable to infer file retrieval date from filename.\n'
            'Use a Unix timestamp as the filename, or specify the --retrieved-at option.'
        ))
        sys.exit(1)

    # Give preference to the date from the CLI option, if it's set
    date_retrieved = date_from_args if date_from_args is not None else date_from_filename

    n_new_entries = logkeeper.write_entries(date_retrieved, new_data)
    logging.info('1 new entry' if n_new_entries == 1 else f'{n_new_entries} new entries')


def cmd_current(args: Dict[str, str]) -> None:
    """
    Lists the ships that are currently at the port. Includes the arrived,
    berthed, and recenly sailed ships for the current day.
    """
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))
    if not logkeeper.has_entries():
        print("No entries found.")
        return

    now = datetime.now()
    in_a_day = now + relativedelta(days=1)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    entries = logkeeper.read_ships_at_port(
        # Include ships that have arrived or will arrive in 1 day
        arrives_before=in_a_day,
        # Include ships that won't sail today, i.e. are still at the port
        sails_after=start_of_today
    )

    for index, entry in entries.iterrows():
        print(f'{entry["Navio"]} ({entry["Viagem"]}): {determine_entry_status(entry)}')


def cmd_trip(args: Dict[str, str]) -> None:
    """
    Lists all the recorded log entries for the given trip name.
    """
    logkeeper = LogKeeper(create_database_engine(args['<database_path>']))
    if not logkeeper.has_entries():
        logger.error("No entries found.")
        return

    entry = logkeeper.read_latest_entry_for_trip(args['<trip_name>'])
    if entry is None:
        logger.error("Trip not found.")
        return

    def desc_event(action: str, date_expected: pd.Timestamp, date_actual: pd.Timestamp) -> str:
        """
        Builds a message representing the relative lateness/earliness of an event
        (arrival, berthing, sailing) by comparing the expected (predicted) and
        actual occurrence dates.
        """
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

    berth = get_ship_berth_number(entry)
    berth_str = '?' if berth is None else str(berth)

    print(f'{entry["Navio"]} (owned by {entry["Armador"]}, length {entry["Comprimento(m)"]}m)')

    if not pd.isnull(entry['ATA']):
        print(desc_event('Arrived', entry['ETA'], entry['ATA']), 'at', entry['ATA'])
    else:
        print(desc_event('Arrive', entry['ETA'], entry['ATA']), 'at', entry['ETA'])

    if not pd.isnull(entry['ATB']):
        print(desc_event('Berthed', entry['ETB'], entry['ATB']), f'at {entry["ATB"]} (#{berth_str})')
    else:
        print(desc_event('Berth', entry['ETB'], entry['ATB']), f'at {entry["ETB"]} (#{berth_str})')

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
