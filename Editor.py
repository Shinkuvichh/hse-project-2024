import pickle
import sys
from pathlib import Path

from pygame_gui import UIManager
from pygame_gui.windows import UIFileDialog, UIMessageWindow

from commonn import *


class Editor:
    def __init__(self):
        self.fps_clock = pg.time.Clock()
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
        self.character_data = None
        self.width = config.width
        self.height = config.height
        self.new_scene = None
        self.screen = pg.display.set_mode((self.width, self.height), pg.FULLSCREEN if config.fullscreen else 0)
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        self.exit_btn = UIButton(relative_rect=pg.Rect(10, 10, 200, 60), manager=self.manager, text="Back to menu")
        self.load_char_btn = UIButton(relative_rect=pg.Rect(10, 80, 200, 60), manager=self.manager,
                                      text="Load character")
        self.char_file_dialog = None
        self.create_btn = UIButton(relative_rect=pg.Rect(10, 150, 200, 60), manager=self.manager,
                                   text="Create character")
        self.char_name = None
        self.char_sheet = CharacterSheet(scene_ui_manager=self.manager)
        self.char_sheet.hide()
        self.save_char_btn = UIButton(relative_rect=pg.Rect(10, 220, 200, 60), manager=self.manager,
                                      text="Save character")
        self.save_char_btn.disable()
        self.load_btn = UIButton(relative_rect=pg.Rect(220, 10, 200, 60), text="Load portrait", manager=self.manager)
        self.load_btn.disable()
        self.load_file_dialog = None
        init_rect = pg.Rect(0, 0, 150, 200)
        init_rect.center = self.screen.get_rect().center
        self.char_sprite = UIImage(
            relative_rect=init_rect,
            image_surface=pg.Surface((config.entity_maxw, config.entity_maxh)),
            manager=self.manager, visible=0)
        init_rect.size = (300, 50)
        init_rect.centerx -= 75
        init_rect.centery -= 75
        self.char_label = UILabel(relative_rect=init_rect,
                                  text="Your character in-game portrait.", manager=self.manager, visible=0)
        init_rect.centery += 300
        self.name_label = UILabel(relative_rect=init_rect, text="Your character name is",
                                  manager=self.manager, visible=0)
        init_rect.centery += 65
        self.name_line = UITextEntryLine(relative_rect=init_rect, placeholder_text="Enter name",
                                         manager=self.manager, visible=0)
        self.save_popup = None

    def run(self):
        while self.new_scene is None:
            self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
            self.process_events()
            self.manager.update(self.time_delta)
            self.render_screen()
            self.fps_clock.tick(config.fps)

    def process_events(self):
        for event in pg.event.get():
            self.manager.process_events(event)
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.save_char_btn:
                    self.character_data = {}  # name str image sheet size
                    self.char_name = self.name_line.get_text()
                    self.character_data['name'] = self.char_name if self.char_name is not None else "New char"
                    self.character_data['string'] = (
                        pg.image.tobytes(self.char_sprite.image, format="RGBA").decode('latin1'))
                    self.character_data['width'] = self.char_sprite.image.get_width()
                    self.character_data['height'] = self.char_sprite.image.get_height()
                    self.character_data['sheet'] = self.char_sheet.dump_to_list()
                    filename = (Path(config.characters_path) / self.char_name).resolve()
                    try:
                        with open(filename, 'wb') as file:
                            pickle.dump(self.character_data, file)
                    except OSError as e:
                        self.save_popup = UIMessageWindow(rect=(100, 100, 300, 300),
                                                          html_message=f"Encountered error while saving character:"
                                                                       f" {e}.<br> Please, try again.",
                                                          manager=self.manager)
                    else:
                        self.save_popup = UIMessageWindow(rect=(100, 100, 300, 300),
                                                          html_message=f"Saved {self.char_name} successfully!",
                                                          manager=self.manager)
                if event.ui_element == self.exit_btn:
                    self.new_scene = "Launcher"
                if event.ui_element == self.create_btn:
                    if self.char_sheet is not None:
                        self.char_sheet.kill()
                        self.char_sheet = None
                    self.save_char_btn.enable()
                    self.char_sheet = CharacterSheet(scene_ui_manager=self.manager)
                    self.char_sheet.show()
                    self.char_sheet.close_window_button.disable()
                    self.char_sprite.show()
                    self.char_label.show()
                    self.name_label.show()
                    self.name_line.show()
                    self.load_btn.enable()
                if event.ui_element == self.load_char_btn:
                    self.char_file_dialog = UIFileDialog(pg.Rect(200, 200, config.width // 3, (config.height * 2) // 3),
                                                         self.manager,
                                                         window_title='Choose character to load',
                                                         initial_file_path=config.characters_path,
                                                         allow_picking_directories=False,
                                                         allow_existing_files_only=True,
                                                         allowed_suffixes={""})
                    self.load_char_btn.disable()
                if event.ui_element == self.load_btn:
                    self.load_file_dialog = LoadFileDialog(scene_ui_manager=self.manager)
            if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
                if event.__dict__['text'] == '__generated':
                    self.char_sprite.set_image(event.__dict__['image'])
                    self.load_file_dialog.kill()
                    self.load_file_dialog = None
                    self.load_btn.enable()
                    return
                if event.ui_element == self.char_file_dialog:
                    with open(event.text, 'rb') as file:
                        self.character_data = pickle.load(file)
                    self.save_char_btn.enable()
                    self.char_name = self.character_data['name']
                    if self.char_sheet is not None:
                        self.char_sheet.kill()
                        self.char_sheet = None
                    self.char_sheet = CharacterSheet(scene_ui_manager=self.manager, name=self.char_name)
                    self.char_sheet.load_from_list(
                        self.character_data['sheet'])
                    self.char_sprite.set_image(pg.image.frombytes(self.character_data['string'].encode('latin1'),
                                                                  size=(
                                                                      self.character_data['width'],
                                                                      self.character_data['height']),
                                                                  format="RGBA")),
                    self.char_label.show()
                    self.char_sprite.show()
                    self.name_label.show()
                    self.name_line.set_text(self.char_name)
                    self.name_line.show()
                    self.save_char_btn.enable()
                if event.ui_element == self.load_file_dialog:
                    try:
                        self.char_sprite.set_image(
                            img_path_to_surface(event.text, config.entity_maxw, config.entity_maxh))
                    except pg.error as e:
                        print(f"Error while loading character portrait: {e}")
            if event.type == pg_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.char_file_dialog:
                    self.load_char_btn.enable()
                    self.char_file_dialog = None
                if event.ui_element == self.load_file_dialog:
                    self.load_btn.enable()
                    self.load_file_dialog = None
            if event.type == pg_gui.UI_TEXT_ENTRY_FINISHED:
                self.char_name = self.name_line.get_text()
                self.char_sheet.set_display_title(f'{self.char_name} character sheet')

    def render_screen(self):
        self.screen.fill((15, 15, 15))
        self.manager.draw_ui(self.screen)
        pg.display.flip()


class LoadFileDialog(UIFileDialog):
    def __init__(self, scene_ui_manager):
        super().__init__(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                         window_title="Choose image or generate by description",
                         initial_file_path=config.images_path,
                         allow_picking_directories=False,
                         allow_existing_files_only=True,
                         allowed_suffixes={""}, object_id="#editor_load_dialog", manager=scene_ui_manager)
        self.refresh_button.kill()
        self.delete_button.kill()
        self.parent_directory_button.kill()
        self.home_button.kill()
        self.prompt_text_line = UITextEntryLine(
            relative_rect=pg.Rect(10, 10, self.get_container().get_size()[0] - 20, -1), container=self,
            placeholder_text="Type in prompt and press enter for generation",
            object_id="#prompt_textline", manager=scene_ui_manager)

    def process_event(self, event):
        super().process_event(event)
        if event.type == pg_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.prompt_text_line:
            image = generate_portrait(self.prompt_text_line.get_text())
            event_data = {'text': "__generated",
                          'ui_element': self,
                          'ui_object_id': self.most_specific_combined_id,
                          'image': image}
            pg.event.post(pg.event.Event(pg_gui.UI_FILE_DIALOG_PATH_PICKED, event_data))
            self.kill()
