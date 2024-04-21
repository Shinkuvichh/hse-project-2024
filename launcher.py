from pathlib import Path
from random import randint
import pygame
import pygame as pg
import pygame_gui as pg_gui
from pygame_gui import UIManager
from pygame_gui.core.utility import create_resource_path
from pygame_gui.elements import UIButton, UIWindow, UIImage, UIPanel, UIDropDownMenu, UITextBox, UITextEntryLine
from pygame_gui.windows import UIFileDialog


class Launcher:
    def __init__(self):
        pg.init()
        self.width = 600
        self.height = 600
        self.running = True
        self.screen = pg.display.set_mode((self.width, self.height))
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        self.join_btn = UIButton(pg.Rect(150, 200, 300, 60), text="JOIN AS PLAYER")
        self.host_btn = UIButton(pg.Rect(150, 270, 300, 60), text="HOST AS MASTER")
        self.res_btn = UIButton(pg.Rect(150, 340, 300, 60), text="RESOLUTION")

    def run(self):
        while self.running:
            self.fps_clock = pg.time.Clock()
            self.running = True
            self.time_delta = self.fps_clock.tick(60) / 1000.0
            self.manager.update(self.time_delta)
            self.render_screen()

    def render_screen(self):
        self.manager.draw_ui(self.screen)
        pg.display.update()


if __name__ == "__main__":
    game = Launcher()
    game.run()
