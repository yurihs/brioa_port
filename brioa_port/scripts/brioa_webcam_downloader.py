"""BRIOA Webcam Downloader

Periodically downloads images from the Port of Itapoa webcam to a
specified output directory. The filenames are the UNIX timestamp
representing the time that the photo was taken.

Usage:
    brioa_webcam_downloader.py <output_dir> [--period <seconds>]

Options:
    --period <seconds>   How often to download an image [default: 20].

"""

import schedule
import time
import os
import errno

from docopt import docopt
from pathlib import Path

from brioa_port.webcam_image_downloader import WebcamImageDownloader
from brioa_port.exception import InvalidWebcamImageException

def download(downloader):
    try:
        image_date = downloader.download_webcam_image()
        print(image_date)
    except InvalidWebcamImageException:
        print("Got an invalid image. Continuing.")

def main():
    arguments = docopt(__doc__)

    webcam_url = 'http://www.portoitapoa.com.br/images/camera/camera.jpeg'
    output_dir_path = Path(arguments['<output_dir>'])

    period_str = arguments['--period']
    try:
        period = int(period_str)
    except ValueError:
        print("Error: Invalid period.")
        return

    if period < 0:
        print("Error: Invalid period.")
        return

    try:
        os.makedirs(output_dir_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            print("Error: Unable to create output directory.")
            return

    downloader = WebcamImageDownloader(
        webcam_url,
        output_dir_path
    )
    schedule.every(period).seconds.do(lambda: download(downloader))

    while 1:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()
