import urllib.request
from unittest.mock import MagicMock

import pytest
from dateutil import tz

from brioa_port.exceptions import FileHasInvalidLastModifiedDateException
from brioa_port.util.request import open_latest_file_from_url


def test_valid_last_modified_date(mocker):
    mocker.patch('urllib.request.urlopen')
    urlopen_return_mock = MagicMock()
    urlopen_return_mock.info.return_value = {
        'Last-Modified': 'Mon, 21 Oct 2015 23:29:00 GMT'
    }
    urllib.request.urlopen.return_value = urlopen_return_mock

    response = open_latest_file_from_url('http://example.com')
    response_date = response.last_modified_date.astimezone(tz.UTC)
    assert response_date.year == 2015
    assert response_date.month == 10
    assert response_date.day == 21
    assert response_date.hour == 23
    assert response_date.minute == 29
    assert response_date.second == 0


def test_invalid_last_modified_date(mocker):
    mocker.patch('urllib.request.urlopen')
    urlopen_return_mock = MagicMock()
    urlopen_return_mock.info.return_value = {
        'Last-Modified': "I'm not a valid date"
    }
    urllib.request.urlopen.return_value = urlopen_return_mock

    with pytest.raises(FileHasInvalidLastModifiedDateException):
        open_latest_file_from_url('http://example.com')


def test_no_last_modified_date(mocker):
    mocker.patch('urllib.request.urlopen')
    urlopen_return_mock = MagicMock()
    urlopen_return_mock.info.return_value = {
        'Last-Modified': None
    }
    urllib.request.urlopen.return_value = urlopen_return_mock

    with pytest.raises(FileHasInvalidLastModifiedDateException):
        open_latest_file_from_url('http://example.com')
