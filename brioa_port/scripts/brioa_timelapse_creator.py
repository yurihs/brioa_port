"""BRIOA Timelapse Creator.

Reads paths to the images that will make up the timelapse from the standard input.
The images should be named with the unix timestamp at the time they were taken.

Usage:
    brioa_timelapse_creator --database <database_path>  <output_path>
                            [--image-list-from-file <file_path>]
                            [--output-fps <int>]
                            [--output-resolution <name>]
                            [--no-progress]

Options:
    --database <database_path>  Information about the ships in port will be obtained here.
    --image-list-from-file <file_path>  Read the image list from a file instead of the standard input.
    --output-fps <int>  Framerate of the output [default: 30].
    --output-resolution <name>    Resolution of the output. The valid values are 1080p or 720p [default: 1080p].
    --no-progress   Don't show a progress bar.

"""

import os.path
import sys
import logging

from datetime import datetime
from docopt import docopt
from PIL import Image
from subprocess import Popen, PIPE
from pathlib import Path
from typing import List, Generator, Iterable, Tuple, Dict, NamedTuple
from tqdm import tqdm

from brioa_port.timelapse_frame_processor import TimelapseFrameProcessor
from brioa_port.util.database import create_database_engine
from brioa_port.log_keeper import LogKeeper


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def start_ffmpeg_process(output_path: str, image_format: str, fps: int) -> Popen:
    """
    Start and FFmpeg process that reads images from stdin in the given format
    and joins them into a video at the given output path.
    """
    return Popen(
        [
            'ffmpeg',
            # Overwrite without confirmation
            '-y',
            # Don't output warnings and other information
            '-loglevel', 'error',
            # Take images from a pipe (duh)
            '-f', 'image2pipe',
            # The images will be in this format
            '-vcodec', image_format,
            '-framerate', str(fps),
            # Read from STDIN
            '-i', '-',
            # Output quality (h264 codec)
            '-crf', '22',
            output_path
        ],
        stdin=PIPE
    )


def make_frames_into_video(frames: Iterable[Image.Image], output_path: Path, fps: int) -> None:
    """
    Takes some images and joins them into a video file using FFmpeg.

    Args:
        frames: The images to join.
        output_path: Where to put the video.
        fps: The framerate of the video.
    """
    # Use PPM to pass the images to FFmpeg.
    # It's faster than, say, JPEG because it has no compression.
    image_format = 'ppm'

    ffmpeg_process = start_ffmpeg_process(str(output_path), image_format, fps)

    for frame in frames:
        frame.save(ffmpeg_process.stdin, image_format)

    ffmpeg_process.stdin.close()
    ffmpeg_process.wait()


def process_images(
        image_paths: Iterable[str],
        frame_processor: TimelapseFrameProcessor,
        show_progress: bool
) -> Generator[Image.Image, None, None]:
    """
    Takes some image paths and runs them through a frame processor,
    returns the results as each frame is completed.
    The date that is required by the processor is taken from each image's filename.
    Frames that fail to complete are ignored.
    """
    for image_path in tqdm(image_paths, desc='Processing the images', unit='images', disable=not show_progress):
        try:
            with Image.open(image_path) as image:
                date = datetime.fromtimestamp(int(os.path.basename(image_path)))
                frame = frame_processor.make_frame(image, date)
        except OSError as e:
            logger.warning(f"Ignoring image at '{image_path}'. The error was: {e}")

        if frame is not None:
            yield frame


def read_lines_from_stdin() -> List[str]:
    """
    Reads from standard input and returns each line,
    with no EOL characters.
    """
    return sys.stdin.read().splitlines()


def read_lines_from_file(path: str) -> List[str]:
    """
    Reads from a given path and returns each line,
    with no EOL characters.
    """
    with open(path, 'rt') as f:
        lines: List[str] = f.read().splitlines()
        return lines


class FrameProcessorArgs(NamedTuple):
    dimensions: Tuple[int, int]
    scaler: float
    font_sizes: Dict[str, int]


def main() -> None:
    args = docopt(__doc__)

    log_keeper = LogKeeper(create_database_engine(args['--database']))

    frame_processor_args = {
        '1080p': FrameProcessorArgs(
            dimensions=(1920, 1080),
            scaler=1,
            font_sizes={
                'huge': 64,
                'large': 30,
                'medium': 22,
                'small': 18,
            }
        ),
        '720p': FrameProcessorArgs(
            dimensions=(1280, 720),
            scaler=0.7,
            font_sizes={
                'huge': 44,
                'large': 25,
                'medium': 18,
                'small': 13,
            }
        )
    }.get(args['--output-resolution'], None)

    if frame_processor_args is None:
        logging.critical('Invalid resolution.')
        sys.exit(1)

    frame_processor = TimelapseFrameProcessor(
        log_keeper,
        dimensions=frame_processor_args.dimensions,
        scaler_value=frame_processor_args.scaler,
        font_sizes=frame_processor_args.font_sizes
    )

    if args['--image-list-from-file'] is None:
        image_paths = read_lines_from_stdin()
    else:
        image_paths = read_lines_from_file(args['--image-list-from-file'])

    frames = process_images(image_paths, frame_processor, show_progress=not args['--no-progress'])
    make_frames_into_video(frames, Path(args['<output_path>']), int(args['--output-fps']))


if __name__ == '__main__':
    main()
