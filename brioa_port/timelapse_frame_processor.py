import pandas as pd

from dateutil.relativedelta import relativedelta
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from babel.dates import format_date, format_time
from typing import Tuple, Dict, Optional

from brioa_port.log_keeper import LogKeeper
from brioa_port.util.entry import get_ship_status, get_ship_berth_number, \
                                  ShipStatus

BoxTuple = Tuple[int, int, int, int]


class TimelapseFrameProcessor:
    """
    Turns raw webcam images into timelapse frames, with overlayed information.

    Attributes:
        log_keeper: Source for the ship schedule information.
        dimensions: Output frame resolution. Preferably with a 16:9 aspect ratio.
        scaler_value: Adjust this to change the spaces between elements, at different resolutions.
        font_sizes: Specify the font sizes that work best for the resolution.
                    The following keys are required: 'huge', 'large', 'medium', and 'small'.
        font_path_or_name: From where to load the font. Will search system directories.

    """

    def __init__(
        self,
        log_keeper: LogKeeper,
        dimensions: Tuple[int, int] = (1920, 1080),
        scaler_value: float = 1,
        font_sizes: Optional[Dict[str, int]] = None,
        font_path_or_name: str = 'DejaVuSans'
    ) -> None:
        self.log_keeper = log_keeper
        self.dimensions = dimensions
        self.scaler_value = scaler_value

        default_font_sizes = {
            'huge':   64,
            'large':  30,
            'medium': 22,
            'small':  18,
        }
        if font_sizes is None:
            font_sizes = default_font_sizes
        elif len(set(font_sizes.keys()).difference(default_font_sizes.keys())) != 0:
            raise ValueError('All font sizes must be specified.')

        self.fonts = {
            'huge':   self._load_font(font_path_or_name, font_sizes['huge']),
            'large':  self._load_font(font_path_or_name, font_sizes['large']),
            'medium': self._load_font(font_path_or_name, font_sizes['medium']),
            'small':  self._load_font(font_path_or_name, font_sizes['small'])
        }
        self.font_path = self.fonts['medium'].path

        self.colors = {
            'background': '#05021a',
            'date_box_background': '#cc2f26',
            'date_box_text': 'white',
            'berthed_ship_box_background_even': '#00a32e',
            'berthed_ship_box_background_odd': '#00d63d',
            'berthed_ship_box_text': 'white',
        }

    def _load_font(self, font_path_or_name: str, size: int) -> ImageFont.FreeTypeFont:
        """
        Loads a font file from the system.
        """
        try:
            return ImageFont.truetype(font_path_or_name, size)
        except IOError:
            raise ValueError(f"Could not load font at '{self.font_path}'")

    def _make_canvas(self) -> Image.Image:
        """
        Makes a blank image to draw the frame onto.
        """
        return Image.new('RGB', self.dimensions, self.colors['background'])

    def _get_berthed_ships(self, date: datetime) -> pd.DataFrame:
        """
        Queries the LogKeeper instance to obtain a list of the ships berthed
        to the port at the given date.
        """
        start_of_today = date.replace(hour=0, minute=0, second=0, microsecond=0)
        ships_at_port = self.log_keeper.read_ships_at_port(
            start_of_today + relativedelta(days=1),
            start_of_today
        )

        return ships_at_port[
            ships_at_port.apply(
                lambda ship: get_ship_status(ship, date) == ShipStatus.BERTHED,
                axis=1
            )
        ].reset_index(drop=True)

    def _draw_date_box(self, draw: ImageDraw.Draw, top_left_corner: Tuple[int, int], width: int, date: datetime) -> int:
        """
        Draws a date/time clock onto the canvas at the given position.

        Args:
            draw: The ImageDraw instance to draw on the desired canvas.
            top_left_corner: Where to start the box.
            width: The fixed horizontal dimension of the box.
            date: The date/time to display on the clock.

        Returns:
            The bottom y coordinate of the box, so that further elements may be drawn after it
        """
        time_str = format_time(date, 'HH:mm', locale='pt_BR')
        time_font = self.fonts['huge']
        time_font_height = time_font.getsize('X')[1]

        date_str = format_date(date, "EEEE\ndd 'de' MMM 'de' yyyy", locale='pt_BR').capitalize()
        date_font = self.fonts['large']
        date_font_height = date_font.getsize('X')[1]

        margin = 20 * self.scaler_value

        bottom_y = int(top_left_corner[1] + time_font_height + date_font_height * 2 + margin * 4)
        draw.rectangle(
            (
                top_left_corner[0],
                top_left_corner[1],
                top_left_corner[0] + width,
                bottom_y
            ),
            fill=self.colors['date_box_background']
        )

        time_y = top_left_corner[1] + margin
        draw.text(
            (top_left_corner[0] + margin, time_y),
            time_str,
            fill=self.colors['date_box_text'],
            font=time_font,
        )

        draw.multiline_text(
            (top_left_corner[0] + margin, time_y + time_font_height + margin),
            date_str,
            fill=self.colors['date_box_text'],
            font=date_font
        )

        return bottom_y

    def _draw_berthed_ship_box(
        self,
        draw: ImageDraw.Draw,
        top_left_corner: Tuple[int, int],
        width: int,
        ship: pd.Series
    ) -> int:
        """
        Draws a berthed ship's information on a box.

        Args:
            draw: The ImageDraw instance to draw on the desired canvas.
            top_left_corner: Where to start the box.
            width: The fixed horizontal dimension of the box.
            ship: Source of the information for the ship, obtained from the LogKeeper.

        Returns:
            The bottom y coordinate of the box, so that further elements may be drawn after it
        """
        berco = get_ship_berth_number(ship)
        # Alternate colors for different designated berthing numbers.
        if berco is None or berco % 2 == 0:
            background_color = self.colors['berthed_ship_box_background_even']
        else:
            background_color = self.colors['berthed_ship_box_background_odd']

        name_str = ship['Navio']
        name_font = self.fonts['large']
        # Resize the font until the name fits within the specified width.
        while (name_font.size > 12) and (name_font.getsize(name_str)[0] > (width - 30)):
            name_font = self._load_font(self.font_path, max(1, name_font.size - 1))
        name_font_height = name_font.getsize('X')[1]

        berco_str = 'Berço ' + str(berco)
        berco_font = self.fonts['medium']
        berco_font_height = berco_font.getsize('X')[1]

        margin = (20 * self.scaler_value)

        bottom_y = int(top_left_corner[1] + name_font_height + berco_font_height + margin * 3)

        draw.rectangle(
            (
                top_left_corner[0],
                top_left_corner[1],
                top_left_corner[0] + width,
                bottom_y
            ),
            fill=background_color
        )

        draw.multiline_text(
            (top_left_corner[0] + margin, top_left_corner[1] + margin),
            name_str,
            fill=self.colors['berthed_ship_box_text'],
            font=name_font
        )

        if berco is not None:
            draw.multiline_text(
                (top_left_corner[0] + margin, top_left_corner[1] + name_font_height + margin * 2),
                berco_str,
                fill=self.colors['berthed_ship_box_text'],
                font=berco_font
            )

        return bottom_y

    def make_frame(self, image: Image.Image, date: datetime) -> Image.Image:
        """
        Processes a webcam image into a timelapse frame.

        Args:
            image: The raw image. Will be resized and pasted onto the final frame.
            date: The time that the image was taken. Used to correlating other information.

        Returns:
            The processed frame, in the form of a new image.
        """
        canvas = self._make_canvas()

        try:
            # Correct for SDTV 480i pixel aspect ratio
            # https://en.wikipedia.org/wiki/Standard-definition_television#Pixel_aspect_ratio
            if image.width == 704 and image.height == 480:
                image_aspect_ratio = 640 / 480
            else:
                image_aspect_ratio = image.width / image.height

            # Try to fit the image to a fraction of the canvas width
            # (to leave some space for the sidebar)
            new_image_width = int(canvas.width * 0.83)
            new_image_height = int(new_image_width / image_aspect_ratio)

            # If that would make the image go off canvas vertically,
            # fit it to the canvas height instead
            if new_image_height > canvas.height:
                new_image_height = canvas.height
                new_image_width = int(new_image_height * image_aspect_ratio)

            image = image.resize(
                (new_image_width, new_image_height),
                Image.BICUBIC
            )
            image_x = canvas.width - image.width
            canvas.paste(image, (image_x, 0))
            draw = ImageDraw.Draw(canvas)
        except OSError:
            return None

        date_bottom_y = self._draw_date_box(draw, (0, 0), image_x, date)

        ships_berthed = self._get_berthed_ships(date)

        ship_box_height = 0
        for index, ship in ships_berthed.iterrows():
            ship_box_top_y = date_bottom_y + (index * ship_box_height)
            ship_box_bottom_y = self._draw_berthed_ship_box(draw, (0, ship_box_top_y), image_x, ship)
            ship_box_height = ship_box_bottom_y - ship_box_top_y

        return canvas
