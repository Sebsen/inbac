import tkinter as tk
import types
from tkinter import Tk, Frame, Canvas, Event, Menu, messagebox, filedialog, Toplevel
from typing import Tuple, Any
from PIL.ImageTk import PhotoImage
import inbac


class View():
    def __init__(self, master: Tk, controller, initial_window_size: Tuple[int, int], no_fullscreen: bool):
        self.controller = controller
        self.master: Tk = master
        self.frame: Frame = tk.Frame(self.master, relief=tk.FLAT)
        self.frame.pack(fill=tk.BOTH, expand=tk.YES)
        self.image_canvas: Canvas = Canvas(self.frame, highlightthickness=0)
        self.image_canvas.pack(fill=tk.BOTH, expand=tk.YES)
        self.master.geometry(
            str(initial_window_size[0]) + "x" + str(initial_window_size[1]))
        # Maximize window to achieve full screen (-> default behaviour unless -nfs is provided in command line arguments)
        if not no_fullscreen:
            self.master.state('zoomed') 
        self.master.update()

        self.bind_events()
        self.create_menu()

    def bind_events(self):
        self.master.bind('z', self.save_next)
        self.master.bind('<space>', self.save)
        self.master.bind('x', self.save_next)
        self.master.bind('y', self.save)
        self.master.bind('c', self.rotate_image)
        self.master.bind('r', self.rotate_aspect_ratio)
        self.master.bind('<Left>', self.previous_image)
        self.master.bind('<Right>', self.next_image)
        self.master.bind('<ButtonPress-3>', self.next_image)
        self.master.bind('<ButtonPress-2>', self.previous_image)
        self.image_canvas.bind('<ButtonPress-1>', self.on_mouse_down)
        self.image_canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.image_canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.image_canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        # Get the selection box cleared from canvas when pressing escape
        self.master.bind('<Escape>', self.on_escape)

        self.master.bind('<KeyPress-Shift_L>', self.enable_selection_mode)
        self.master.bind('<KeyPress-Control_L>', self.enable_selection_mode)
        self.master.bind('<KeyRelease-Shift_L>', self.disable_selection_mode)
        self.master.bind('<KeyRelease-Control_L>', self.disable_selection_mode)

        self.image_canvas.bind('<Configure>', self.on_resize)

    def create_menu(self):
        self.menu: Menu = Menu(self.master, relief=tk.FLAT)
        filename_gaps_menu = Menu(self.master, relief=tk.FLAT)

        self.menu.add_command(label="Open", command=self.open_dialog)
        self.menu.add_command(
            label="Settings", command=self.create_settings_window)
        self.menu.add_command(label="About", command=self.show_about_dialog)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self.master.quit)
        self.menu.add_command(label="\u22EE", activebackground=self.menu.cget("background"))
        self.menu.add_separator()
        self.menu.add_cascade(label="Filename Gaps", menu=filename_gaps_menu)

        filename_gaps_menu.add_command(label="Remove Gaps (latest file)", command=self.remove_gaps_latest)
        filename_gaps_menu.add_command(label="Remove Gaps (all files)", command=self.remove_gaps_all)
        filename_gaps_menu.add_command(label="Insert Gaps", command=self.show_insert_gaps)
        self.master.config(menu=self.menu)

    def ask_directory(self) -> str:
        return filedialog.askdirectory(parent=self.master)

    def open_dialog(self):
        self.controller.select_images_folder()
        self.controller.load_images()

    def create_settings_window(self):
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.geometry("{}x{}".format(400, 400))
        settings = types.SimpleNamespace()

        settings.aspect_ratio_checked = tk.IntVar()
        settings.aspect_ratio_checked.set(
            self.controller.model.args.aspect_ratio is not None)
        aspect_ratio_checkbox = tk.Checkbutton(
            settings_window,
            variable=settings.aspect_ratio_checked,
            onvalue=1,
            offvalue=0,
            text="Aspect Ratio")
        aspect_ratio_checkbox.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky=tk.W,
            padx=5,
            pady=5)

        settings.aspect_ratio_x = tk.StringVar()
        if self.controller.model.args.aspect_ratio is not None:
            settings.aspect_ratio_x.set(
                str(self.controller.model.args.aspect_ratio[0]))
        aspect_ratio_x_entry = tk.Entry(
            settings_window,
            width=5,
            textvariable=settings.aspect_ratio_x,
            bg="white")
        aspect_ratio_x_entry.grid(row=1, column=0, padx=5, pady=5)

        settings.aspect_ratio_y = tk.StringVar()
        if self.controller.model.args.aspect_ratio is not None:
            settings.aspect_ratio_y.set(
                str(self.controller.model.args.aspect_ratio[1]))
        aspect_ratio_y_entry = tk.Entry(
            settings_window,
            width=5,
            textvariable=settings.aspect_ratio_y,
            bg="white")
        aspect_ratio_y_entry.grid(row=1, column=1, padx=5, pady=5)

        settings.resize_checked = tk.IntVar()
        settings.resize_checked.set(
            self.controller.model.args.resize is not None)
        resize_checkbox = tk.Checkbutton(
            settings_window,
            variable=settings.resize_checked,
            onvalue=1,
            offvalue=0,
            text="Resize")
        resize_checkbox.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky=tk.W,
            padx=5,
            pady=5)

        settings.resize_x = tk.StringVar()
        if self.controller.model.args.resize is not None:
            settings.resize_x.set(str(self.controller.model.args.resize[0]))
        resize_x_entry = tk.Entry(
            settings_window,
            width=5,
            textvariable=settings.resize_x,
            bg="white")
        resize_x_entry.grid(row=3, column=0, padx=5, pady=5)

        settings.resize_y = tk.StringVar()
        if self.controller.model.args.resize is not None:
            settings.resize_y.set(str(self.controller.model.args.resize[1]))
        resize_y_entry = tk.Entry(
            settings_window,
            width=5,
            textvariable=settings.resize_y,
            bg="white")
        resize_y_entry.grid(row=3, column=1, padx=5, pady=5)

        selection_box_color_label = tk.Label(
            settings_window, text='Selection box color')
        selection_box_color_label.grid(
            row=4, column=0, columnspan=2, padx=5, pady=5)

        settings.selection_box_color_choices = [
            "black", "white", "red", "green", "blue", "cyan", "yellow", "magenta"]
        settings.selection_box_color_listbox = tk.Listbox(
            settings_window, listvariable=tk.StringVar(
                value=settings.selection_box_color_choices))
        if self.controller.model.args.selection_box_color in settings.selection_box_color_choices:
            selection_box_color_index = settings.selection_box_color_choices.index(
                self.controller.model.args.selection_box_color)
            settings.selection_box_color_listbox.selection_set(
                selection_box_color_index)
            settings.selection_box_color_listbox.see(selection_box_color_index)
        settings.selection_box_color_listbox.grid(
            row=5, column=0, columnspan=2, padx=5, pady=5)

        save_button = tk.Button(
            settings_window,
            text="Save",
            command=lambda: self.save_settings(
                settings_window,
                settings))
        save_button.grid(row=6, column=0, padx=5, pady=5)

        cancel_button = tk.Button(
            settings_window,
            text="Cancel",
            command=lambda: self.cancel_settings(settings_window))
        cancel_button.grid(row=6, column=1, padx=5, pady=5)

    def save_settings(self, settings_window: Toplevel,
                      settings: types.SimpleNamespace):
        if settings.aspect_ratio_checked.get():
            self.controller.model.args.aspect_ratio = (
                int(settings.aspect_ratio_x.get()), int(settings.aspect_ratio_y.get()))
        else:
            self.controller.model.args.aspect_ratio = None
        if settings.resize_checked.get():
            self.controller.model.args.resize = (
                int(settings.resize_x.get()), int(settings.resize_y.get()))
        else:
            self.controller.model.args.resize = None
        if settings.selection_box_color_listbox.curselection():
            self.controller.model.args.selection_box_color = settings.selection_box_color_choices[settings.selection_box_color_listbox.curselection()[
                0]]
        else:
            self.controller.model.args.selection_box_color = "yellow"
        settings_window.destroy()

    def cancel_settings(self, settings_window: Toplevel):
        settings_window.destroy()

    def show_about_dialog(self):
        messagebox.showinfo("About", "inbac " +
                            inbac.__version__, parent=self.master)
    
    def remove_gaps_latest(self):
        self.controller.fill_filename_gaps(self.controller.model.args.output_dir, process_all=False)
    
    def remove_gaps_all(self):
        self.controller.fill_filename_gaps(self.controller.model.args.output_dir)
    
    def show_insert_gaps(self):
        insert_gaps_window = tk.Toplevel(self.master)
        insert_gaps_window.title("Insert Filename Gaps")
        insert_gaps_window.geometry("{}x{}".format(400, 400))
        settings = types.SimpleNamespace()

        selection_box_color_label = tk.Label(
            insert_gaps_window, text='Crop number to insert the gap after:')
        selection_box_color_label.grid(
            row=4, column=0, columnspan=2, padx=5, pady=5)

        settings.gap_index = tk.IntVar()
        gap_index_entry = tk.Entry(
            insert_gaps_window,
            width=5,
            textvariable=settings.gap_index,
            bg="white")
        gap_index_entry.grid(row=1, column=0, padx=5, pady=5)


        apply_button = tk.Button(
            insert_gaps_window,
            text="Insert Gaps",
            command=lambda: self.insert_gaps(settings)
            )
        apply_button.grid(row=6, column=0, padx=5, pady=5)

        close_button = tk.Button(
            insert_gaps_window,
            text="Close",
            command=lambda: self.cancel_settings(insert_gaps_window))
        close_button.grid(row=6, column=1, padx=5, pady=5)


    def insert_gaps(self, settings: types.SimpleNamespace):
        gap_index = settings.gap_index.get()
        if gap_index is not None and gap_index < 1:
            # No valid index - return
            return
        
        # Actually insert the gaps
        self.controller.fill_filename_gaps(
            self.controller.model.args.output_dir,
            process_all=False,
            gap_after=gap_index
        )

    def show_error(self, title: str, message: str):
        messagebox.showerror(title, message, parent=self.master)

    def display_image(self, image: PhotoImage) -> Any:
        return self.image_canvas.create_image(0, 0, anchor=tk.NW, image=image)

    def remove_from_canvas(self, obj: Any):
        self.image_canvas.delete(obj)

    def create_line(self, coords: Tuple[int, int, int, int], fill="gold", dash=(4, 2)):
        return self.image_canvas.create_line(coords[0], coords[1], coords[2], coords[3], fill=fill, dash=dash)

    def create_rectangle(
            self, box: Tuple[int, int, int, int], outline_color: str) -> Any:
        return self.image_canvas.create_rectangle(box, outline=outline_color)
    
    def create_overlay(
            self, box: Tuple[int, int, int, int], outline="", fill="black", stipple="gray25") -> Any:
        return self.image_canvas.create_rectangle(box, outline=outline, fill=fill, stipple=stipple)

    def change_canvas_object_coords(self, obj: Any, coords: Tuple[int, int]):
        self.image_canvas.coords(obj, coords)

    def change_canvas_overlay_coords(self, obj: Any, coords: Tuple[int, int, int, int]):
        self.image_canvas.coords(obj, coords[0], coords[1], coords[2], coords[3])

    def get_canvas_object_coords(self, obj: Any) -> Any:
        return self.image_canvas.coords(obj)
    
    def tag_raise(self, obj: Any):
        self.image_canvas.tag_raise(obj)

    def move_canvas_object_by_offset(
            self,
            obj: Any,
            offset_x: int,
            offset_y: int):
            self.image_canvas.move(obj, offset_x, offset_y)
    
    def enable_selection_mode(self, event: Event = None):
        """
        Enables the selection mode in case a selection is performed for the image on the image canvas (-> dragging with left mouse).
        In case of zooming/ scrolling (-> with mouse wheel) enables smooth scrolling
        """
        self.controller.model.enabled_selection_mode = True
        self.controller.model.effective_scrolling_speed_in_px = self.controller.model.smooth_scrolling_speed_in_px

    def disable_selection_mode(self, event: Event = None):
        """
        Disables the selection mode in case a selection is performed for the image on the image canvas (-> dragging with left mouse).
        In case of zooming/ scrolling (-> with mouse wheel) disables smooth scrolling and returns to normal scrolling
        """
        self.controller.model.enabled_selection_mode = False
        self.controller.model.effective_scrolling_speed_in_px = self.controller.model.default_scrolling_speed_in_px

    def on_mouse_down(self, event: Event):
        self.controller.start_selection((event.x, event.y))

    def on_mouse_drag(self, event: Event):
        self.controller.move_selection((event.x, event.y))

    def on_mouse_up(self, event: Event):
        self.controller.stop_selection()

    def on_mouse_wheel(self, event: Event):
        self.controller.on_mouse_wheel_zoom(event.delta)

    def on_escape(self, event: Event):
        self.controller.clear_selection_box()

    def next_image(self, event: Event = None):
        self.controller.next_image()

    def previous_image(self, event: Event = None):
        self.controller.previous_image()

    def on_resize(self, event: Event = None):
        if self.controller.model.current_image is not None:
            self.controller.display_image_on_canvas(
                self.controller.model.current_image)

    def save_next(self, event: Event = None):
        self.controller.save_next()

    def save(self, event: Event = None):
        self.controller.save()

    def set_title(self, title: str):
        self.master.title(title)

    def rotate_image(self, event: Event = None):
        self.controller.rotate_image()

    def rotate_aspect_ratio(self, event: Event = None):
        self.controller.rotate_aspect_ratio()
