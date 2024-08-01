from fractions import Fraction
import itertools
import mimetypes
import os
from natsort import os_sorted

import re
from typing import Optional, List, Tuple

from PIL import Image, ImageTk

from inbac.model import Model
from inbac.view import View

DEFAULT_GAP_SIZE: int = 100
IMAGE_FILE_EXTENSIONS = ('.jpg', '.jpeg', '.png')
# Regular expression to match the filename structure of cropped images
CROPPED_IMAGE_PATTERN = re.compile(r"(.*_crop)(\d+)(.*)(.jpg|.jpeg|.png)", re.IGNORECASE)

class Controller():
    def __init__(self, model: Model):
        self.model: Model = model
        self.view = None

    def run(self):
        self.select_images_folder()
        self.load_images()

    def select_images_folder(self):
        input_dir = self.view.ask_directory()
        if input_dir:
            self.model.args.input_dir = input_dir
            self.model.args.output_dir = os.path.join(
                self.model.args.input_dir, "crops")

    def create_output_directory(self):
        try:
            os.makedirs(self.model.args.output_dir)
        except OSError:
            self.view.show_error(
                "Error",
                "Output directory cannot be created, please select output directory location")
            self.model.args.output_dir = self.view.ask_directory()

    def load_image(self, image_name: str):
        if self.model.current_image is not None:
            self.model.current_image.close()
            self.model.current_image = None
        image = Image.open(os.path.join(self.model.args.input_dir, image_name))
        image_dimensions: Tuple[int, int] = self.display_image_on_canvas(image)
        image_width: int = image_dimensions[0]
        image_height: int = image_dimensions[1]

        # TODO: Add mapping from float to aspect ratio with tolerances -> introduce tolerant function for proper mapping!
        aspect_ratio: Fraction = Fraction(round(image_width / image_height, 3)).limit_denominator()
        aspect_ratio_string: str = str(aspect_ratio).replace('/', ':')
        image_name_with_counter = f'({self.model.current_file + 1}/{len(self.model.images)}): {image_name}'
        full_image_title = f'{image_name_with_counter} - Dimensions: {image_width}x{image_height} - Aspect Ratio: {aspect_ratio_string}'
        self.view.set_title(full_image_title)

    # TODO: Add option to control it via args from CLI + checkbox on UI
    def draw_initial_selection_box(self):
        image_dimensions: Tuple[int, int] = self.model.canvas_image_dimensions
        # We don't have image dimensions, but they're required
        if image_dimensions is None:
            return

        # If we don't have custom, user-specified aspect ratio don't draw initial box
        if self.model.args.aspect_ratio is None:
            return

        image_width: int = image_dimensions[0]
        image_height: int = image_dimensions[1]

        # By default start with selection box covering biggest part of image possible
        self.start_selection((0, 0))
        self.program_move_selection((image_width, image_height))

        # Get current coordinates of the selection box
        left_x, top_y, right_x, bottom_y = self.view.get_canvas_object_coords(self.model.selection_box)
        self.update_overlays(left_x, top_y, right_x, bottom_y)
        self.update_golden_ratio_lines(left_x, top_y, right_x, bottom_y)
        self.view.tag_raise(self.model.selection_box)

    def load_images(self):
        if self.model.args.input_dir:
            try:
                self.model.images = self.load_image_list(
                    self.model.args.input_dir)
            except OSError:
                self.view.show_error(
                    "Error", "Input directory cannot be opened")

        if self.model.images:
            try:
                self.model.current_file = 0
                self.load_image(self.model.images[self.model.current_file])
            except IOError:
                self.next_image()

    def display_image_on_canvas(self, image: Image) -> Tuple[int, int]:
        """
        Called when the main window is resized, a new image is being loaded or the image is rotated.
        Displays the requested image on the canvas
        """
        self.clear_canvas()
        self.model.current_image = image
        self.model.canvas_image_dimensions = self.calculate_canvas_image_dimensions(
            self.model.current_image.size[0],
            self.model.current_image.size[1],
            self.view.image_canvas.winfo_width(),
            self.view.image_canvas.winfo_height())
        displayed_image: Image = self.model.current_image.copy()
        displayed_image.thumbnail(
            self.model.canvas_image_dimensions, Image.LANCZOS)
        self.model.displayed_image = ImageTk.PhotoImage(displayed_image)
        self.model.canvas_image = self.view.display_image(
            self.model.displayed_image)

        self.draw_initial_selection_box()

        return self.model.canvas_image_dimensions

    def clear_canvas(self):
        self.clear_selection_box()
        if self.model.canvas_image is not None:
            self.view.remove_from_canvas(self.model.canvas_image)
            self.model.canvas_image = None

    def clear_selection_box(self):
        if self.model.selection_box is not None:
            self.view.remove_from_canvas(self.model.selection_box)
            self.model.selection_box = None
        
        # Also clear golden ratio lines, which can be considered being part of the selection box itself (-> created and deleted together)
        for line in self.model.golden_ratio_lines:
            self.view.remove_from_canvas(line)
        self.model.golden_ratio_lines.clear()

        # Also clear overlays, which can be considered being part of the selection box itself (-> created and deleted together)
        if self.model.overlay_top is not None:
            self.view.remove_from_canvas(self.model.overlay_top)
            self.model.overlay_top = None

        if self.model.overlay_bottom is not None:
            self.view.remove_from_canvas(self.model.overlay_bottom)
            self.model.overlay_bottom = None
        
        if self.model.overlay_left is not None:
            self.view.remove_from_canvas(self.model.overlay_left)
            self.model.overlay_left = None
        
        if self.model.overlay_right is not None:
            self.view.remove_from_canvas(self.model.overlay_right)
            self.model.overlay_right = None

    def update_selection_box(self):
        selected_box: Tuple[int, int, int, int] = self.get_selected_box(
            self.model.canvas_image_dimensions, self.model.press_coord, self.model.move_coord, self.model.args.aspect_ratio)

        if self.model.selection_box is None:
            self.model.selection_box = self.view.create_rectangle(
                                            selected_box, self.model.args.selection_box_color)
            
            # Create overlays
            self.create_overlays()
        else:
            self.view.change_canvas_object_coords(
                     self.model.selection_box, selected_box)
            # Update the overlay rectangles
            self.update_overlays(selected_box[0], selected_box[1], selected_box[2], selected_box[3])
            # Draw the golden ratio lines
            self.update_golden_ratio_lines(selected_box[0], selected_box[1], selected_box[2], selected_box[3])
            self.view.tag_raise(self.model.selection_box)

    def stop_selection(self):
        self.model.box_selected = False

    def on_mouse_wheel_zoom(self, delta: int):
        if not self.model.selection_box:
            return

        # Get current coordinates of the selection box
        left_x, top_y, right_x, bottom_y = self.view.get_canvas_object_coords(self.model.selection_box)

        # Calculate the current width and height of selection box
        width: int = right_x - left_x
        height: int = bottom_y - top_y

        # Calculate the change in size
        direction: int = 1 if delta > 0 else -1
        delta: int = self.model.effective_scrolling_speed_in_px * direction

        # Maintain user defined aspect ratio and if not present the current selection box'
        aspect_ratio: Tuple[int, int] = self.model.args.aspect_ratio if self.model.args.aspect_ratio is not None else (width, height)

        # Update width and height based on the aspect ratio
        new_width = width + delta
        new_height = (new_width / aspect_ratio[0]) * aspect_ratio[1]

        # Image width
        image_width: int = self.model.canvas_image_dimensions[0]
        image_height: int = self.model.canvas_image_dimensions[1]

        # Ensure the new size fits within the image boundaries
        if left_x + new_width > image_width:
            new_width = image_width - left_x
            new_height = (new_width / aspect_ratio[0]) * aspect_ratio[1]
        if top_y + new_height > image_height:
            new_height = image_height - top_y
            new_width = (new_height / aspect_ratio[1]) * aspect_ratio[0]

        # Restrict resizing only when going too small
        if delta < 0 and (new_width < 10 or new_height < 10):
            return

        # Update the selection box coordinates
        self.view.change_canvas_overlay_coords(self.model.selection_box, (left_x, top_y, left_x + new_width, top_y + new_height))

        # Update the overlay rectangles
        self.update_overlays(left_x, top_y, left_x + new_width, top_y + new_height)
        # Draw the golden ratio lines
        self.update_golden_ratio_lines(left_x, top_y, left_x + new_width, top_y + new_height)
        self.view.tag_raise(self.model.selection_box)

    def start_selection(self, press_coord: Tuple[int, int]):
        self.model.press_coord = press_coord
        self.model.move_coord = press_coord
        if self.is_outside_image_dimensions(press_coord):
            return
        if self.model.enabled_selection_mode:
            self.clear_selection_box()
        elif self.model.selection_box is not None:
            selected_box: Tuple[int, int, int, int] = self.view.get_canvas_object_coords(
                self.model.selection_box)
            self.model.box_selected = self.coordinates_in_selection_box(
                self.model.press_coord, selected_box)
            

    def program_move_selection(self, move_coord: Tuple[int, int]):
        """
        Utility to programatically move/ create the selection box on the canvas. This is like the user would do -> by reusing all existing functions, with minimal
        additional (technical) boilerplate code.
        To be able to programatically move/ create the selection box, "enabled_selection_mode" must be artificially activated
        """
        previous_state = self.model.enabled_selection_mode
        self.model.enabled_selection_mode = True
        self.move_selection(move_coord)
        self.model.enabled_selection_mode = previous_state


    def move_selection(self, move_coord: Tuple[int, int]):
        """
        Called whenever the selection box should be initially created on canvas or must be moved.
        When canvas doesn't exist yet on screen will be created, otherwise moved.
        """
        if not self.model.enabled_selection_mode and not self.model.box_selected:
            # We are not in "selection mode" (-> existing selection box shall be moved), but we don't have a box (it must exist though)
            # => exit
            # In "selection mode" it doesn't matter whether there is an existing selection box or not, it will be replaced anyway
            return
        if self.is_outside_image_dimensions(move_coord):
            # In any case the desired coordinates (regardless if from user or program) must be within image range to perform useful actions. If not in image range:
            # => exit
            return
        prev_move_coord: Tuple[int, int] = self.model.move_coord
        self.model.move_coord = move_coord
        if self.model.box_selected:
            x_delta: int = self.model.move_coord[0] - prev_move_coord[0]
            y_delta: int = self.model.move_coord[1] - prev_move_coord[1]

            selected_box: Tuple[int, int, int, int] = self.view.get_canvas_object_coords(
                self.model.selection_box)

            # The image bounds
            min_x = 0
            max_x = self.model.canvas_image_dimensions[0]
            min_y = 0
            max_y = self.model.canvas_image_dimensions[1]

            # Calculate proposed new coordinates
            new_x0 = selected_box[0] + x_delta
            new_y0 = selected_box[1] + y_delta
            new_x1 = selected_box[2] + x_delta
            new_y1 = selected_box[3] + y_delta

            # Check if new coordinates are within bounds
            if (min_x <= new_x0 <= max_x and min_x <= new_x1 <= max_x and
                min_y <= new_y0 <= max_y and min_y <= new_y1 <= max_y):

                self.view.move_canvas_object_by_offset(
                        self.model.selection_box, x_delta, y_delta)
            
                # Update the overlay rectangles
                self.update_overlays(new_x0, new_y0, new_x1, new_y1)
                # Draw the golden ratio lines
                self.update_golden_ratio_lines(new_x0, new_y0, new_x1, new_y1)
                self.view.tag_raise(self.model.selection_box)
        else:
            self.update_selection_box()

    def is_outside_image_dimensions(self, move_coord: Tuple[int, int]) -> bool:
        image_dimensions: Tuple[int, int] = self.model.canvas_image_dimensions
        image_box: Tuple[int, int, int, int] = (0, 0, image_dimensions[0], image_dimensions[1])
        return not self.coordinates_in_selection_box(move_coord, image_box)

    def next_image(self):
        if self.model.current_file + 1 >= len(self.model.images):
            return
        self.model.current_file += 1
        try:
            self.load_image(self.model.images[self.model.current_file])
        except IOError:
            self.next_image()

    def previous_image(self):
        if self.model.current_file - 1 < 0:
            return
        self.model.current_file -= 1
        try:
            self.load_image(self.model.images[self.model.current_file])
        except IOError:
            self.previous_image()

    def save_next(self):
        if self.save():
            self.next_image()

    def save(self) -> bool:
        if self.model.selection_box is None:
            return False
        selected_box: Tuple[int, int, int, int] = self.view.get_canvas_object_coords(
            self.model.selection_box)
        box: Tuple[int, int, int, int] = self.get_real_box(
            selected_box, self.model.current_image.size, self.model.canvas_image_dimensions)
        new_filename: str = self.find_available_name(
            self.model.args.output_dir, self.model.images[self.model.current_file])
        saved_image: Image = self.model.current_image.copy().crop(box)
        if self.model.args.resize:
            saved_image = saved_image.resize(
                (self.model.args.resize[0], self.model.args.resize[1]), Image.LANCZOS)
        if self.model.args.image_format:
            new_filename, _ = os.path.splitext(new_filename)
        if not os.path.exists(self.model.args.output_dir):
            self.create_output_directory()
        saved_image.save(
            os.path.join(
                self.model.args.output_dir,
                new_filename),
            self.model.args.image_format,
            quality=self.model.args.image_quality)
        return True

    def rotate_image(self):
        if self.model.current_image is not None:
            rotated_image = self.model.current_image.transpose(Image.ROTATE_90)
            self.model.current_image.close()
            self.model.current_image = None
            self.display_image_on_canvas(rotated_image)
    
    def rotate_aspect_ratio(self):
        if self.model.args.aspect_ratio is not None:
            self.model.args.aspect_ratio = (
                int(self.model.args.aspect_ratio[1]), int(self.model.args.aspect_ratio[0]))

    
    def create_overlays(self):
        if self.model.overlay_top:
            self.view.remove_from_canvas(self.model.overlay_top)
        if self.model.overlay_bottom:
            self.view.remove_from_canvas(self.model.overlay_bottom)
        if self.model.overlay_left:
            self.view.remove_from_canvas(self.model.overlay_left)
        if self.model.overlay_right:
            self.view.remove_from_canvas(self.model.overlay_right)

        image_dimensions = self.model.canvas_image_dimensions
        self.model.overlay_top = self.view.create_overlay((0, 0, image_dimensions[0], 0))
        self.model.overlay_bottom = self.view.create_overlay((0, image_dimensions[1], image_dimensions[0], image_dimensions[1]))
        self.model.overlay_left = self.view.create_overlay((0, 0, 0, image_dimensions[1]))
        self.model.overlay_right = self.view.create_overlay((image_dimensions[0], 0, image_dimensions[0], image_dimensions[1]))

    def update_overlays(self, left_x, top_y, right_x, bottom_y):
        image_dimensions = self.model.canvas_image_dimensions
        self.view.change_canvas_overlay_coords(self.model.overlay_top, (0, 0, image_dimensions[0], top_y))
        self.view.change_canvas_overlay_coords(self.model.overlay_bottom, (0, bottom_y, image_dimensions[0], image_dimensions[1]))
        self.view.change_canvas_overlay_coords(self.model.overlay_left, (0, top_y, left_x, bottom_y))
        self.view.change_canvas_overlay_coords(self.model.overlay_right, (right_x, top_y, image_dimensions[0], bottom_y))
    
    # TODO: Add option to control display of golden ratio lines via args from CLI + checkbox on UI
    def update_golden_ratio_lines(self, left_x, top_y, right_x, bottom_y):
        for line in self.model.golden_ratio_lines:
            self.view.remove_from_canvas(line)
        self.model.golden_ratio_lines.clear()

        width = right_x - left_x
        height = bottom_y - top_y

        phi = (1 + 5 ** 0.5) / 2  # Golden ratio

        # Vertical lines
        vertical_line_1_x = left_x + width / phi
        vertical_line_2_x = right_x - width / phi
        self.model.golden_ratio_lines.append(
            self.view.create_line((vertical_line_1_x, top_y, vertical_line_1_x, bottom_y), fill=self.model.args.selection_box_color))
        self.model.golden_ratio_lines.append(
            self.view.create_line((vertical_line_2_x, top_y, vertical_line_2_x, bottom_y), fill=self.model.args.selection_box_color))

        # Horizontal lines
        horizontal_line_1_y = top_y + height / phi
        horizontal_line_2_y = bottom_y - height / phi
        self.model.golden_ratio_lines.append(
            self.view.create_line((left_x, horizontal_line_1_y, right_x, horizontal_line_1_y), fill=self.model.args.selection_box_color))
        self.model.golden_ratio_lines.append(
            self.view.create_line((left_x, horizontal_line_2_y, right_x, horizontal_line_2_y), fill=self.model.args.selection_box_color))


    @staticmethod
    def calculate_canvas_image_dimensions(image_width: int,
                                          image_height: int,
                                          canvas_width: int,
                                          canvas_height: int) -> Tuple[int, int]:
        if image_width > canvas_width or image_height > canvas_height:
            width_ratio: float = canvas_width / image_width
            height_ratio: float = canvas_height / image_height
            ratio: float = min(width_ratio, height_ratio)
            new_image_width: int = int(image_width * ratio)
            new_image_height: int = int(image_height * ratio)
            return (new_image_width, new_image_height)
        return (image_width, image_height)

    @staticmethod
    def load_image_list(directory: str) -> List[str]:
        images: List[str] = []

        for filename in sorted(os.listdir(directory)):
            filetype, _ = mimetypes.guess_type(filename)
            if filetype is None or filetype.split("/")[0] != "image":
                continue
            images.append(filename)

        return images

    @staticmethod
    def coordinates_in_selection_box(
            coordinates: Tuple[int, int], selection_box: Tuple[int, int, int, int]) -> bool:
        return (coordinates[0] >= selection_box[0] and coordinates[0] <= selection_box[2]
                and coordinates[1] >= selection_box[1] and coordinates[1] <= selection_box[3])

    @staticmethod
    def find_available_name(directory: str, filename: str) -> str:
        crop_suffix: str = '_crop'
        name, extension = os.path.splitext(filename)
        for num in itertools.count(1):
            if not os.path.isfile(
                os.path.join(
                    directory,
                    name +
                    crop_suffix +
                    str(num) +
                    extension)):
                return name + crop_suffix + str(num) + extension

    @staticmethod
    def get_selected_box(image_dimensions: Tuple[int, int],
                         mouse_press_coord: Tuple[int,
                                                  int],
                         mouse_move_coord: Tuple[int,
                                                 int],
                         aspect_ratio: Optional[Tuple[int,
                                                      int]]) -> Tuple[int,
                                                                      int,
                                                                      int,
                                                                      int]:
        
        current_x: int = mouse_move_coord[0]
        current_y: int = mouse_move_coord[1]

        start_x: int = mouse_press_coord[0]
        start_y: int = mouse_press_coord[1]

        # Calculate the width and height
        width: int = abs(current_x - start_x)
        height: int = abs(current_y - start_y)

        if aspect_ratio is not None:
            # Calculate the height maintaining the aspect ratio
            height: int = (width / aspect_ratio[0]) * aspect_ratio[1]


        # Ensure the box fits within the image boundaries
        if start_x < current_x:  # Right direction
            if start_x + width > image_dimensions[0]:
                width = image_dimensions[0] - start_x
                if aspect_ratio is not None:
                    height = (width / aspect_ratio[0]) * aspect_ratio[1]
        else:  # Left direction
            if start_x - width < 0:
                width = start_x
                if aspect_ratio is not None:
                    height = (width / aspect_ratio[0]) * aspect_ratio[1]

        if start_y < current_y:  # Down direction
            if start_y + height > image_dimensions[1]:
                height = image_dimensions[1] - start_y
                if aspect_ratio is not None:
                    width = (height / aspect_ratio[1]) * aspect_ratio[0]
        else:  # Up direction
            if start_y - height < 0:
                height = start_y
                if aspect_ratio is not None:
                    width = (height / aspect_ratio[1]) * aspect_ratio[0]

        # Calculate the top-left and bottom-right coordinates
        if current_x < start_x:
            left_x: int = start_x - width
            right_x: int = start_x
        else:
            left_x: int = start_x
            right_x: int = start_x + width

        if current_y < start_y:
            top_y: int = start_y - height
            bottom_y: int = start_y
        else:
            top_y: int = start_y
            bottom_y: int = start_y + height
        

        selection_box: Tuple[int,
                             int,
                             int,
                             int] = (left_x,
                                     top_y,
                                     right_x,
                                     bottom_y)

        return selection_box

    @staticmethod
    def get_real_box(selected_box: Tuple[int,
                                         int,
                                         int,
                                         int],
                     original_image_size: Tuple[int,
                                                int],
                     displayed_image_size: Tuple[int,
                                                 int]) -> Tuple[int,
                                                                int,
                                                                int,
                                                                int]:
        return (int(selected_box[0] *
                    original_image_size[0] /
                    displayed_image_size[0]), int(selected_box[1] *
                                                  original_image_size[1] /
                                                  displayed_image_size[1]), int(selected_box[2] *
                                                                                original_image_size[0] /
                                                                                displayed_image_size[0]), int(selected_box[3] *
                                                                                                              original_image_size[1] /
                                                                                                              displayed_image_size[1]))

    @staticmethod
    def remove_filename_gaps(directory, process_all=True):
        """
        Removes the sequence number gaps in filenames of image files containing the "_crop" identifier. Can be performed for all files
        of the current directory or only the newest one
        """

        files_dict = Controller.collect_cropped_files(directory, process_all=process_all)

        # Process each group of files
        failed_renamings = {}
        for base_name, files in files_dict.items():

            # Rename files forward to remove gaps (forward direction to avoid possible conflicts!)
            for new_index, (_, suffix, extension, old_filename) in enumerate(files, start=1):
                try:
                    Controller.rename_file(directory, old_filename, base_name, new_index, extension)
                except FileExistsError:
                    # File exists -> collision:
                    #  => Collect planned renaming and perform later, once blocking file is renamed as well
                    new_base_name = f"tmp_{base_name}"
                    new_filename = Controller.rename_file(directory, old_filename, new_base_name, new_index, extension)
                    failed_renamings[new_filename] = f"{base_name}{new_index}{extension}"


        # Finally rename files to real filename which failed earlier due to temporary filename collisions
        #  -> now all files should be renamed so that collisions won't occur anymore!
        for tmp_filename, real_filename in failed_renamings.items():
            old_filepath = os.path.join(directory, tmp_filename)
            new_filepath = os.path.join(directory, real_filename)
            if old_filename != new_filename:
                os.rename(old_filepath, new_filepath)


    @staticmethod
    # FIXME: Analyze: When "insert gaps += 1" is apllied twice it only takes effect once => why?!
    def insert_filename_gaps(directory, gap_after, gap_size=DEFAULT_GAP_SIZE):
        """
        Introduces gaps of the specified gap_size (default=100) to the filenames after the specified index. Can only be performed for latest file
        """

        # Validate arguments
        if gap_after is None or gap_after < 1:
            raise Exception("gap_after argument is required!")

        if gap_size is None or gap_size < 1:
            gap_size = DEFAULT_GAP_SIZE


        # Start processing
        files_dict = Controller.collect_cropped_files(directory, process_all=False)

        if len(files_dict) > 1:
            raise Exception("Invalid amount of files -> Only in latest file gaps can be introduced!")

        # Process each group of files
        for base_name, files in files_dict.items():

            # Rename files to close the gaps or introduce the new gaps (backward to avoid conflicts)
            for i in range(len(files)-1, -1, -1):
                crop_number, suffix, extension, old_filename = files[i]
                if gap_after is not None and crop_number > gap_after:
                    new_index = i + 1 + gap_size
                else:
                    new_index = i + 1
                Controller.rename_file(directory, old_filename, base_name, new_index, extension)


    @staticmethod
    def collect_cropped_files(directory:str, process_all: bool=True, extensions: list[str]=IMAGE_FILE_EXTENSIONS) -> dict[str, list[(int, str, str, str)]]:
        
        # Dictionary to hold filenames by their base name
        files_dict = {}
        
        # List all image files in the directory *as per operating system order* => very important for keeping correct order of files and not mixing!!
        files = [
            filename
            for filename in os_sorted(os.listdir(directory))    # sorting according to the operating system!
            if filename.lower().endswith(extensions) and CROPPED_IMAGE_PATTERN.match(filename)
        ]
        
        # If not processing all, select only the last file based on modification time
        latest_file_base_name=None
        if not process_all and files:
            newest_file = files[-1]
            match = CROPPED_IMAGE_PATTERN.match(newest_file)
            if match:
                latest_file_base_name = match.group(1)
        
        # Extract and categorize files based on the regular expression (-> create files_dict)
        for filename in files:
            match = CROPPED_IMAGE_PATTERN.match(filename)
            if match:
                base_name = match.group(1)
                crop_number = int(match.group(2))
                suffix = match.group(3)
                extension = match.group(4)
                # Only continue processing/ collecting files, when they match the latest file's base name (in case process_all=False provided)
                if latest_file_base_name is None or base_name == latest_file_base_name:
                    if base_name not in files_dict:
                        # Only add key once to dict
                        files_dict[base_name] = []
                    files_dict[base_name].append((crop_number, suffix, extension, filename))
        
        return files_dict


    @staticmethod
    def rename_file(directory: str, old_filename: str, base_name: str, new_index: int, extension: str) -> str:
        new_filename = f"{base_name}{new_index}{extension}"
        old_filepath = os.path.join(directory, old_filename)
        new_filepath = os.path.join(directory, new_filename)
        if old_filename != new_filename:
            os.rename(old_filepath, new_filepath)
            return new_filename
        return None
