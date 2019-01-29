"""BRIOA Timelapse Creator.

Reads paths to the images that will make up the timelapse from the standard input.
The images should be named with the unix timestamp at the time they were taken.

Usage:
    brioa_timelapse_creator --database <database_path>  <output_path>
                            [--image-list-from-file <file_path>]
                            [--output-fps <int>]
                            [--output-resolution <name>]

Options:
    --database <database_path>  Information about the ships in port will be obtained here.
    --image-list-from-file <file_path>  Read the image list from a file instead of the standard input.
    --output-fps <int>  Framerate of the output [default: 30].
    --output-resolution <name>    Resolution of the output. The valid values are 1080p or 720p [default: 1080p].

"""

import os.path
import sys

from datetime import datetime
from docopt import docopt
from PIL import Image
from subprocess import Popen, PIPE
from pathlib import Path
from typing import List, Generator, Iterable, Tuple, Dict, cast
from tqdm import tqdm

from brioa_port.timelapse_frame_processor import TimelapseFrameProcessor
from brioa_port.util.database import create_database_engine
from brioa_port.log_keeper import LogKeeper


def start_ffmpeg_process(output_path: str, fps: int) -> Popen:
    return Popen(
        [
            'ffmpeg',
            '-loglevel', 'error',
            '-y',
            '-f', 'image2pipe',
            '-vcodec', 'ppm',
            '-framerate', str(fps),
            '-i', '-',
            '-crf', '22',
            output_path
        ],
        stdin=PIPE
    )


def process_images(
        image_paths: Iterable[str],
        frame_processor: TimelapseFrameProcessor
) -> Generator[Image.Image, None, None]:
    for image_path in tqdm(image_paths, desc='Processing the images', unit='images'):
        try:
            with Image.open(image_path) as image:
                date = datetime.fromtimestamp(int(os.path.basename(image_path)))

                frame = frame_processor.make_frame(image, date)
                if frame is None:
                    continue

                yield frame
        except OSError as e:
            print(f"Warning: ignoring image at '{image_path}'. The error was: {e}")
            continue


def make_video(frames: Iterable[Image.Image], output_path: Path, fps: int) -> None:
    ffmpeg_process = start_ffmpeg_process(str(output_path), fps)

    for frame in frames:
        frame.save(ffmpeg_process.stdin, 'PPM')

    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()


def read_lines_from_stdin() -> List[str]:
    return sys.stdin.read().splitlines()


def read_lines_from_file(path: str) -> List[str]:
    with open(path, 'rt') as f:
        lines: List[str] = f.read().splitlines()
        return lines


def main() -> None:
    args = docopt(__doc__)

    log_keeper = LogKeeper(create_database_engine(args['--database']))

    frame_processor_args = {
        '1080p': {
            'dimensions': (1920, 1080),
            'scaler': 1,
            'font_sizes': {
                'huge': 64,
                'large': 30,
                'medium': 22,
                'small': 18,
            }
        },
        '720p': {
            'dimensions': (1280, 720),
            'scaler': 0.7,
            'font_sizes': {
                'huge': 44,
                'large': 25,
                'medium': 18,
                'small': 13,
            }
        }
    }.get(args['--output-resolution'], None)
    if frame_processor_args is None:
        print("Invalid resolution.")
        return

    frame_processor = TimelapseFrameProcessor(
        log_keeper,
        dimensions=cast(Tuple[int, int], frame_processor_args['dimensions']),
        scaler_value=cast(int, frame_processor_args['scaler']),
        font_sizes=cast(Dict[str, int], frame_processor_args['font_sizes']),
    )

    if args['--image-list-from-file'] is None:
        image_paths = read_lines_from_stdin()
    else:
        image_paths = read_lines_from_file(args['--image-list-from-file'])

    frames = process_images(image_paths, frame_processor)
    make_video(frames, Path(args['<output_path>']), int(args['--output-fps']))


if __name__ == '__main__':
    main()
