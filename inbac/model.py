from typing import Optional, List, Tuple, Any
from argparse import Namespace
from PIL import Image
from PIL.ImageTk import PhotoImage


class Model():
    def __init__(self, args):
        self.args: Namespace = args
        self.images: List[str] = []
        self.selection_box: Optional[Any] = None
        self.golden_ratio_lines = []
        self.press_coord: Tuple[int, int] = (0, 0)
        self.move_coord: Tuple[int, int] = (0, 0)
        self.displayed_image: Optional[PhotoImage] = None
        self.canvas_image: Optional[Any] = None
        self.canvas_image_dimensions: Tuple[int, int] = (0, 0)
        self.current_image: Optional[Image] = None
        self.overlay_top: Optional[Any] = None
        self.overlay_bottom: Optional[Any] = None
        self.overlay_left: Optional[Any] = None
        self.overlay_right: Optional[Any] = None
        self.enabled_selection_mode: bool = False
        self.default_scrolling_speed_in_px: int = 8
        self.smooth_scrolling_speed_in_px: int = 1
        self.effective_scrolling_speed_in_px: int = self.default_scrolling_speed_in_px
        self.box_selected: bool = False
        self.current_file: int = 0
