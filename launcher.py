from commonn import *
from pygame_gui.elements import UIButton, UIDropDownMenu
import config
import sys
from pygame_gui import UIManager


class Launcher:
    def __init__(self):
        self.width = 600
        self.height = 600
        self.new_scene = None
        self.screen = pg.display.set_mode((self.width, self.height))
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        self.join_btn = UIButton(pg.Rect(150, 200, 300, 60), text="JOIN AS PLAYER")
        self.host_btn = UIButton(pg.Rect(150, 270, 300, 60), text="HOST AS MASTER")
        self.resolution_drop_down = UIDropDownMenu(config.resolutions.keys(),
                                                   starting_option=f"{config.width}x{config.height}",
                                                   relative_rect=pg.Rect(150, 340, 300, 60))

    def run(self):
        while self.new_scene is None:
            self.fps_clock = pg.time.Clock()
            self.process_events()
            self.time_delta = self.fps_clock.tick(60) / 1000.0
            self.manager.update(self.time_delta)
            self.render_screen()

    def process_events(self):
        for event in pg.event.get():
            self.manager.process_events(event)
            if event.type == pg.QUIT:
                self.running = False
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.join_btn:
                    self.new_scene = "Client"
                if event.ui_element == self.host_btn:
                    self.new_scene = "Host"
            if (event.type == pg_gui.UI_DROP_DOWN_MENU_CHANGED
                    and event.ui_element == self.resolution_drop_down):
                with open('config.py', 'r') as file:
                    lines = file.readlines()
                newres = event.text.split('x')
                lines[0] = f'width = {newres[0]}\n'
                lines[1] = f'height = {newres[1]}\n'
                with open('config.py', 'w') as file:
                    file.writelines(lines)

    def render_screen(self):
        self.screen.fill((0, 0, 0))
        self.manager.draw_ui(self.screen)
        pg.display.flip()
