import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from dateutil import tz

from brioa_port.util import request
from brioa_port.util.datetime import get_unix_timestamp_from_local_datetime


def test_save_new_file(mocker):
    mocker.patch('brioa_port.util.request.open_latest_file_from_url')
    file = MagicMock()
    last_modified_date = datetime(2015, 10, 21, 23, 59, 0, tzinfo=tz.UTC).astimezone(tz.tzlocal())
    last_modified_date_unix = str(get_unix_timestamp_from_local_datetime(last_modified_date))
    request.open_latest_file_from_url.return_value = request.ResponseWithLastModifiedDate(
        file,
        last_modified_date
    )

    out_dir = Path('/tmp/out')
    expected_out_file = MagicMock()

    mocker.patch('pathlib.PurePath.__truediv__', wraps=out_dir.__truediv__)
    mocker.patch('pathlib.Path.open')
    out_dir_open_context = MagicMock()
    out_dir_open_context.__enter__.return_value = expected_out_file
    out_dir.open.return_value = out_dir_open_context

    mocker.patch('shutil.copyfileobj')

    request.save_latest_file_from_url('http://example.com', out_dir)
    out_dir.__truediv__.assert_called_once_with(last_modified_date_unix)
    shutil.copyfileobj.assert_called_once_with(file, expected_out_file)
