"""BRIOA Webcam Downloader

Periodically downloads images from the Port of Itapoa webcam to a
specified output directory. The filenames are the UNIX timestamp
representing the time that the photo was taken.

The output directory will be created if it doesn't exist.

Usage:
    brioa_webcam_downloader.py <output_dir> [--period <seconds>] [--verbose | --quiet]

Options:
    -v, --verbose   Show more information messages
    --period <seconds>   How often to download an image [default: 20].

"""

import schedule
import time
import os
import errno
import sys
import logging

from docopt import docopt
from pathlib import Path

from brioa_port.webcam_downloader import download_webcam_image
from brioa_port.exceptions import InvalidWebcamImageException
from brioa_port.util.args import parse_period_arg


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def safe_download(webcam_url: str, output_dir: Path) -> None:
    """
    Task for the scheduler. Downloads an image and ignores exceptions.
    """
    try:
        image_path = download_webcam_image(webcam_url, output_dir)
        logger.info("Downloaded " + image_path.stem)
    except InvalidWebcamImageException:
        logger.warning("Got invalid image. Continuing.")


def main() -> None:
    arguments = docopt(__doc__)

    webcam_url = 'http://www.portoitapoa.com.br/images/camera/camera.jpeg'
    output_dir_path = Path(arguments['<output_dir>'])

    # Handle logging options
    if arguments['--verbose']:
        logger.setLevel(logging.DEBUG)
    if arguments['--quiet']:
        logging.disable(logging.CRITICAL)

    # Handle period option
    try:
        period = parse_period_arg(arguments['--period'])
    except ValueError as e:
        logger.critical("Error: %s", e)
        sys.exit(1)

    # Handle output dir argument, creates it if necessary
    try:
        os.makedirs(output_dir_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            logger.critical("Error: Unable to create output directory.")
            sys.exit(1)

    # Download in a loop!
    schedule.every(period).seconds.do(lambda: safe_download(webcam_url, output_dir_path))
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
