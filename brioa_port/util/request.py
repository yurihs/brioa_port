import email.utils
import shutil
import urllib.request

from datetime import datetime
from email.header import Header
from http.client import HTTPResponse
from pathlib import Path
from typing import Optional, Union, NamedTuple, cast
from dateutil import tz

from brioa_port.exceptions import FileHasInvalidLastModifiedDateException
from brioa_port.util.datetime import get_unix_timestamp_from_local_datetime


def save_latest_file_from_url(url: str, output_dir: Path) -> Path:
    """
    Downloads a file and names it according to the reported last modified date.
    Throws an error if no date is returned by the server.

    Args:
        url: Where to download from.
        output_dir: Where to download to.

    Returns:
        Where the file was saved (including the filename with the date).
    """
    response = open_latest_file_from_url(url)

    output_path = output_dir / str(get_unix_timestamp_from_local_datetime(response.last_modified_date))
    if output_path.exists():
        raise FileExistsError()

    with output_path.open('wb') as out_file:
        shutil.copyfileobj(response.file, out_file)

    response.file.close()

    return output_path


class ResponseWithLastModifiedDate(NamedTuple):
    file: HTTPResponse
    last_modified_date: datetime


def open_latest_file_from_url(url: str) -> ResponseWithLastModifiedDate:
    """
    Opens a connection to a remote file and checks the last modified date that
    the server returns.
    Throws an error if no date is returned by the server, or if it's invalid.
    """
    response = cast(HTTPResponse, urllib.request.urlopen(url))
    last_modified_header = response.info().get('Last-Modified', None)
    if last_modified_header is None:
        raise FileHasInvalidLastModifiedDateException()

    last_modified_date = parse_last_modified_date(last_modified_header)
    if last_modified_date is None:
        raise FileHasInvalidLastModifiedDateException()

    return ResponseWithLastModifiedDate(
        response,
        last_modified_date
    )


def parse_last_modified_date(last_modified_header: Union[Header, str]) -> Optional[datetime]:
    """
    Parses an HTTP Last-Modified-Date header (RFC 7231).

    Args:
        last_modified_header: Accepts the date string, or a Header object.

    Returns:
        The parsed datetime object, or None, if no date could be parsed.
    """
    if isinstance(last_modified_header, Header):
        last_modified_str = str(last_modified_header)
    else:
        last_modified_str = last_modified_header

    if last_modified_str.strip() == "":
        return None

    try:
        return email.utils.parsedate_to_datetime(last_modified_str).astimezone(tz.tzlocal())
    except (TypeError, ValueError, IndexError):
        return None
