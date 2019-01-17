from datetime import datetime
from pathlib import Path
from urllib.error import URLError, HTTPError, ContentTooShortError

from brioa_port.exceptions import InvalidWebcamImageException, FileHasInvalidLastModifiedDateException
from brioa_port.util.request import save_latest_file_from_url


class WebcamDownloader:

    def __init__(self, webcam_url: str, output_dir_path: Path):
        self.webcam_url = webcam_url
        self.output_dir_path = output_dir_path.absolute()

    def download_webcam_image(self) -> Path:
        try:
            return save_latest_file_from_url(self.webcam_url, self.output_dir_path)
        except (URLError, HTTPError, ContentTooShortError, FileHasInvalidLastModifiedDateException, FileExistsError):
            raise InvalidWebcamImageException()
