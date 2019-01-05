import urllib.request
import shutil
import time
import email.utils

from datetime import datetime
from dateutil import tz
from pathlib import Path
from typing import Optional
from email.header import Header

from brioa_port.exception import InvalidWebcamImageException


class WebcamImageDownloader:

    def __init__(self, webcam_url: str, output_dir_path: Path):
        self.webcam_url = webcam_url
        self.output_dir_path = output_dir_path.absolute()

    @staticmethod
    def _download_file_from_url(url: str, output_dir: Path) -> Optional[datetime]:
        with urllib.request.urlopen(url) as response:
            last_modified_header = response.info().get('Last-Modified', None)
            if last_modified_header is None:
                return None

            if isinstance(last_modified_header, Header):
                last_modified_str = str(last_modified_header)
            else:
                last_modified_str = last_modified_header

            if last_modified_str.strip() == "":
                return None

            last_modified_date_local = email.utils.parsedate_to_datetime(last_modified_str).astimezone(tz.tzlocal())
            output_path = output_dir / str(int(time.mktime(last_modified_date_local.timetuple())))
            if output_path.exists():
                return None

            with output_path.open('wb') as out_file:
                shutil.copyfileobj(response, out_file)
        return last_modified_date_local

    def download_webcam_image(self) -> str:
        try:
            last_modified_date = self._download_file_from_url(self.webcam_url, self.output_dir_path)
            if last_modified_date is not None:
                return str(last_modified_date)
            else:
                raise InvalidWebcamImageException()
        except Exception:
            raise InvalidWebcamImageException()
