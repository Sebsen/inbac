import tkinter as tk
import os

from tkinter import filedialog, Tk
from argparse import Namespace

import inbac.parse_arguments as parse_args
from inbac.model import Model
from inbac.view import View
from inbac.controller import Controller


class Application():
    def __init__(self, args: Namespace, master: Tk):
        self.model: Model = Model(args)

        self.controller: Controller = Controller(self.model)
        self.view: View = View(master, self.controller, args.window_size, args.no_fullscreen)

        self.controller.view = self.view

        self.controller.run()


    def run(self):
        self.view.master.mainloop()


def main():
    root = tk.Tk()
    root.title("inbac")
    app = Application(parse_args.parse_arguments(), master=root)

    app.run()


if __name__ == "__main__":
    main()
