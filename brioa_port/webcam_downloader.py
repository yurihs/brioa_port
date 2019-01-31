from pathlib import Path
from urllib.error import URLError, HTTPError, ContentTooShortError

from brioa_port.exceptions import InvalidWebcamImageException, FileHasInvalidLastModifiedDateException
from brioa_port.util.request import save_latest_file_from_url


def download_webcam_image(webcam_url: str, output_dir_path: Path) -> Path:
    """
    Downloads an image from the given URL to the given directory,
    with the filename representing the  'last modified date' that
    the server responds with.

    Args:
        webcam_url: Where to download from
        output_dir_path: Where to download to

    Returns:
        The path to the saved file.
    """
    try:
        return save_latest_file_from_url(webcam_url, output_dir_path)
    except (URLError, HTTPError, ContentTooShortError, FileHasInvalidLastModifiedDateException, FileExistsError):
        raise InvalidWebcamImageException()
