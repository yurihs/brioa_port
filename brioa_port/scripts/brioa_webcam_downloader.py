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
import threading

from docopt import docopt
from pathlib import Path

from brioa_port.webcam_downloader import WebcamDownloader
from brioa_port.exceptions import InvalidWebcamImageException


def download(downloader: WebcamDownloader) -> None:
    try:
        image_path = downloader.download_webcam_image()
        print("Downloaded " + image_path.stem)
    except InvalidWebcamImageException:
        print("Warning: invalid image. Continuing.")


def start_scheduler_thread(scheduler: schedule.Scheduler, interval: int = 1) -> threading.Event:
    """Continuously run, while executing pending jobs at each elapsed
    time interval.
    @return cease_continuous_run: threading.Event which can be set to
    cease continuous run.
    Please note that it is *intended behavior that run_continuously()
    does not run missed jobs*. For example, if you've registered a job
    that should run every minute and you set a continuous run interval
    of one hour then your job won't be run 60 times at each interval but
    only once.
    """
    cease_continuous_run = threading.Event()

    class ScheduleThread(threading.Thread):
        @classmethod
        def run(cls) -> None:
            while not cease_continuous_run.is_set():
                scheduler.run_pending()
                time.sleep(interval)

    continuous_thread = ScheduleThread()
    continuous_thread.start()
    return cease_continuous_run


def main() -> None:
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

    downloader = WebcamDownloader(
        webcam_url,
        output_dir_path
    )

    schedule.every(period).seconds.do(lambda: download(downloader))
    schedule_thread = start_scheduler_thread(schedule.default_scheduler)


if __name__ == '__main__':
    main()
