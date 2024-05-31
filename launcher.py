import pickle

from pygame_gui.windows import UIFileDialog, UIMessageWindow

from commonn import *
from pygame_gui.elements import UIButton, UIDropDownMenu
import config
import sys
from pygame_gui import UIManager


class Launcher:
    def __init__(self):
        self.char_file_dialog = None
        self.width = 600
        self.height = 600
        self.new_scene = None
        self.fps_clock = pg.time.Clock()
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
        self.screen = pg.display.set_mode((self.width, self.height))
        self.character_data = None
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        self.join_btn = UIButton(pg.Rect(150, 200, 300, 60), text="JOIN AS PLAYER", manager=self.manager,
                                 tool_tip_text=f"You will connect to {config.host} via port {config.port}. You can change it in config.py")
        self.host_btn = UIButton(pg.Rect(150, 270, 300, 60), text="HOST AS MASTER", manager=self.manager,
                                 tool_tip_text=f"You are using port {config.port}. You can change port in config.py")
        self.editor_btn = UIButton(pg.Rect(150, 340, 300, 60), text="OPEN EDITOR", manager=self.manager,
                                   tool_tip_text="Create new characters and edit old ones.")
        self.fullscreen_btn = UIButton(pg.Rect(120, 530, 150, 60), manager=self.manager,
                                       text="Fullscreen: on" if config.fullscreen == pg.FULLSCREEN else "Fullscreen: off")
        self.resolution_drop_down = UIDropDownMenu(config.resolutions.keys(),
                                                   starting_option=f"{config.width}x{config.height}",
                                                   relative_rect=pg.Rect(10, 530, 100, 60), manager=self.manager)
        self.pop_up = None
        self.char_file_dialog = None

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
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
                try:
                    with open(event.text, 'rb') as file:
                        self.character_data = pickle.load(file)
                except Exception as e:
                    self.pop_up = UIMessageWindow(rect=(100, 100, 300, 300),
                                                  html_message=f"Encountered error while loading character: {e}.<br> Please, try again.",
                                                  manager=self.manager)
                else:
                    self.new_scene = "Client"

            if event.type == pg_gui.UI_WINDOW_CLOSE:
                self.join_btn.enable()
                self.char_file_dialog = None
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.join_btn:
                    self.char_file_dialog = UIFileDialog(
                        pg.Rect(10, 10, 300, 300),
                        self.manager,
                        window_title='Choose character to join game',
                        initial_file_path=config.characters_path,
                        allow_picking_directories=False,
                        allow_existing_files_only=True,
                        allowed_suffixes={""})
                    self.join_btn.disable()

                if event.ui_element == self.host_btn:
                    self.new_scene = "Host"
                if event.ui_element == self.editor_btn:
                    self.new_scene = "Editor"
                if event.ui_element == self.fullscreen_btn:
                    if config.fullscreen:
                        with open('config.py', 'r') as file:
                            lines = file.readlines()
                            lines[2] = f'fullscreen = False\n'
                        with open('config.py', 'w') as file:
                            file.writelines(lines)
                        self.fullscreen_btn.set_text("Fullscreen: off")
                        config.fullscreen = False
                    else:
                        with open('config.py', 'r') as file:
                            lines = file.readlines()
                            lines[2] = f'fullscreen = True\n'
                        with open('config.py', 'w') as file:
                            file.writelines(lines)
                        self.fullscreen_btn.set_text("Fullscreen: on")
                        config.fullscreen = True

            if event.type == pg_gui.UI_DROP_DOWN_MENU_CHANGED and event.ui_element == self.resolution_drop_down:
                x, y = event.text.split('x')
                config.width = int(x)
                config.height = int(y)
                with open('config.py', 'r') as file:
                    lines = file.readlines()
                    lines[0] = f'width = {x}\n'
                    lines[1] = f'height = {y}\n'
                with open('config.py', 'w') as file:
                    file.writelines(lines)

    def render_screen(self):
        self.screen.fill((15, 15, 15))
        self.manager.draw_ui(self.screen)
        pg.display.flip()
