import pygame
import pygame as pg
import pygame_gui as pg_gui
from pygame_gui.core import ObjectID
from pygame_gui.core.utility import create_resource_path
from pygame_gui.elements import UIWindow, UITextEntryLine, UILabel, UITextBox, UITextEntryBox, UIImage, UIButton

import config


class PlayerEntity(UIWindow):
    def __init__(self, manager, character_data, ident, client_mode=False):
        super().__init__(pg.Rect(30, 30, config.entity_maxw, config.entity_maxh), manager=manager,
                         draggable=not client_mode, object_id="#player_entity")
        self.portrait = UIImage(relative_rect=pg.Rect((0, 0), self.get_container().get_size()),
                                image_surface=pg.image.frombytes(character_data['string'].encode('latin1'),
                                                                 size=(
                                                                     character_data['width'],
                                                                     character_data['height']),
                                                                 format="RGBA"),
                                manager=self.ui_manager,
                                container=self)
        self.char_name = character_data['name']
        self.char_sheet = CharacterSheet(scene_ui_manager=self.ui_manager, name=self.char_name, client_mode=client_mode)
        self.char_sheet.load_from_list(character_data['sheet'])
        self.char_sheet.hide()
        self.title_bar.allow_double_clicks = True
        self.set_display_title(character_data['name'])
        self.close_window_button.set_text("-")
        self.icon_btn = None
        self.id = str(ident)

    def show(self):
        super().show()
        self.icon_btn.kill()

    def kill(self):
        if self.icon_btn is not None:
            self.icon_btn.kill()
        self.char_sheet.kill()
        super().kill()

    def process_event(self, event: pg.event.Event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_DOUBLE_CLICKED and event.ui_element == self.title_bar:
            self.char_sheet.show()

    def on_close_window_button_pressed(self):
        self.hide()
        self.icon_btn = UIButton(relative_rect=self.close_window_button.rect,
                                 object_id=ObjectID(class_id="@player_entity", object_id="#char_icon_button"),
                                 manager=self.ui_manager, visible=True, command=self.show, text="")

    def dump(self):
        character_data = {'name': self.char_name if self.char_name is not None else "New char", 'string': (
            pg.image.tobytes(self.portrait.image, format="RGBA").decode('latin1')),
                          'width': self.portrait.image.get_width(), 'height': self.portrait.image.get_height(),
                          'sheet': self.char_sheet.dump_to_list()}
        return character_data


class CharacterSheet(UIWindow):
    def __init__(self, scene_ui_manager, name=None, client_mode=False):
        super().__init__(rect=pg.Rect(10, 10, 600, 800),
                         manager=scene_ui_manager,
                         window_display_title="New character sheet" if name is None else f'{name} character sheet')
        self.lvl_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                 relative_rect=pg.Rect(90, 10, 35, 30),
                                                 object_id=ObjectID(class_id="@charsheet", object_id="#lvl_line"),
                                                 blocked=client_mode)
        self.lvl_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(10, 10, 80, 33),
                                 text="LEVEL", object_id=ObjectID(class_id="@charsheet_label", object_id="#lvl_label"))
        self.lvl_line.set_allowed_characters('numbers')
        self.lvl_line.set_text_length_limit(2)
        self.race_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(135, 10, 70, 33),
                                  text="RACE", object_id=ObjectID(class_id="@charsheet_label", object_id="#race_label"))
        self.race_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                  relative_rect=pg.Rect(205, 10, 150, 30),
                                                  object_id=ObjectID(class_id="@charsheet", object_id="#race_line"),
                                                  blocked=client_mode)
        self.align_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(365, 10, 150, 33),
                                   text="ALIGNMENT",
                                   object_id=ObjectID(class_id="@charsheet_label", object_id="#align_label"))
        self.align_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                   relative_rect=pg.Rect(515, 10, 45, 30),
                                                   object_id=ObjectID(class_id="@charsheet",
                                                                      object_id="#align_line"), blocked=client_mode)
        self.align_line.set_text_length_limit(2)

        self.health_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                    relative_rect=pg.Rect(113, 43, 50, 33),
                                                    object_id=ObjectID(class_id="@charsheet", object_id="#health_line"),
                                                    blocked=client_mode)
        self.health_line.set_text_length_limit(3)
        self.health_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(10, 43, 100, 33),
                                    text="HEALTH",
                                    object_id=ObjectID(class_id="@charsheet_label", object_id="#health_label"))

        self.exp_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                 relative_rect=pg.Rect(223, 43, 50, 33),
                                                 object_id=ObjectID(class_id="@charsheet", object_id="#exp_line"))
        self.exp_line.set_text_length_limit(3)
        self.exp_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(173, 43, 50, 33),
                                 text="EXP",
                                 object_id=ObjectID(class_id="@charsheet_label", object_id="#exp_label"))
        self.speed_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                   relative_rect=pg.Rect(355, 43, 50, 33),
                                                   object_id=ObjectID(class_id="@charsheet", object_id="#speed_line"),
                                                   blocked=client_mode)
        self.speed_line.set_text_length_limit(3)
        self.speed_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(282, 43, 71, 33),
                                   text="SPEED",
                                   object_id=ObjectID(class_id="@charsheet_label", object_id="#speed_label"))

        self.armor_line = UIBlockableTextEntryLine(manager=self.ui_manager, container=self,
                                                   relative_rect=pg.Rect(505, 43, 50, 33),
                                                   object_id=ObjectID(class_id="@charsheet", object_id="#armor_line"),
                                                   blocked=client_mode)
        self.armor_line.set_text_length_limit(3)
        self.armor_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(415, 43, 90, 33),
                                   text="ARMOR",
                                   object_id=ObjectID(class_id="@charsheet_label", object_id="#armor_label"))

        self.skills_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(10, 99, 80, 33),
                                    text="SKILLS",
                                    object_id=ObjectID(class_id="@charsheet_label", object_id="#skills_label"))
        self.skills_box = UITextBox(manager=self.ui_manager, container=self,
                                    relative_rect=pg.Rect(45, 132, 200, 558),
                                    object_id=ObjectID(class_id="@charsheet", object_id="#skills_box"),
                                    html_text="Acrobatics<br>Animal Handling<br>Arcana<br>Athletics<br>Deception<br"
                                              ">History<br>Insight<br>Intimidation<br>Investigation<br>Medicine<br"
                                              ">Nature<br>Perception<br>Performance<br>Persuasion<br>Religion<br"
                                              ">Sleight of Hand<br>Stealth<br>")
        if self.skills_box.scroll_bar is not None:
            self.skills_box.scroll_bar.kill()
        self.skills_lines = []
        for skill_n in range(17):
            self.skills_lines.append(
                UITextEntryLine(manager=self.ui_manager, container=self,
                                relative_rect=pg.Rect(10, 132 + skill_n * 31, 35, 31),
                                object_id=ObjectID(class_id="@charsheet", object_id="#skills_line")))
            self.skills_lines[skill_n].set_text_length_limit(2)

        self.other_label = UILabel(manager=self.ui_manager, container=self, relative_rect=pg.Rect(255, 99, 335, 33),
                                   text="OTHER STATS AND INFO",
                                   object_id=ObjectID(class_id="@charsheet_label", object_id="#other_label"))
        self.other_textbox = UIBlockableTextEntryBox(manager=self.ui_manager, container=self,
                                                     relative_rect=pg.Rect(255, 132, 335, 558),
                                                     object_id=ObjectID(class_id="@charsheet", object_id="#other_box"),
                                                     placeholder_text="Write anything here!", initial_text="",
                                                     blocked=client_mode)
        self.changed = False

    def on_close_window_button_pressed(self):
        self.hide()

    def dump_to_list(self):  #
        dump = []
        for line in self.skills_lines:
            dump.append(line.get_text())
        dump.append(self.lvl_line.get_text())
        dump.append(self.race_line.get_text())
        dump.append(self.align_line.get_text())
        dump.append(self.health_line.get_text())
        dump.append(self.exp_line.get_text())
        dump.append(self.speed_line.get_text())
        dump.append(self.armor_line.get_text())
        dump.append(self.other_textbox.get_text())
        return dump

    def load_from_list(self, dump):
        self.other_textbox.set_text(dump[24])
        self.armor_line.set_text(dump[23])
        self.speed_line.set_text(dump[22])
        self.exp_line.set_text(dump[21])
        self.health_line.set_text(dump[20])
        self.align_line.set_text(dump[19])
        self.race_line.set_text(dump[18])
        self.lvl_line.set_text(dump[17])
        for i in range(16, -1, -1):
            self.skills_lines[i].set_text(dump[i])

    def process_event(self, event: pg.event.Event):
        if event.type == pg_gui.UI_TEXT_ENTRY_CHANGED:
            if self.__contains__(event.ui_element):
                self.changed = True
                return False
        return super().process_event(event)


class UIBlockableTextEntryLine(UITextEntryLine):
    def __init__(self, relative_rect, manager, container, object_id, blocked: bool = False):
        super().__init__(relative_rect=relative_rect, manager=manager, container=container, object_id=object_id)
        self.blocked = blocked

    def _process_mouse_button_event(self, event: pygame.event.Event) -> bool:
        if self.blocked:
            return False
        return super()._process_mouse_button_event(event)


class UIBlockableTextEntryBox(UITextEntryBox):
    def __init__(self, relative_rect, manager, container, object_id, initial_text, placeholder_text,
                 blocked: bool = False, ):
        super().__init__(relative_rect=relative_rect, manager=manager, container=container, object_id=object_id,
                         initial_text=initial_text, placeholder_text=placeholder_text)
        self.blocked = blocked

    def _process_mouse_button_event(self, event) -> bool:
        if self.blocked:
            return False
        return super()._process_mouse_button_event(event)


def generate_portrait(prompt):
    pass


def scale_image(image, maxw, maxh):
    image_rect = image.get_rect()
    aspect_ratio = image_rect.width / image_rect.height
    need_to_scale = False
    if image_rect.width > maxw:
        image_rect.width = maxw
        image_rect.height = int(image_rect.width / aspect_ratio)
        need_to_scale = True
    if image_rect.height > maxh:
        image_rect.height = maxh
        image_rect.width = int(image_rect.height * aspect_ratio)
        need_to_scale = True
    if need_to_scale:
        image = pg.transform.smoothscale(image,
                                         image_rect.size)
    return image


def img_path_to_surface(image_path, maxw, maxh):
    resource_path = pg_gui.core.utility.create_resource_path(image_path)
    loaded_image = pg.image.load(resource_path).convert_alpha()
    return scale_image(loaded_image, maxw, maxh)


font_paths = ("CrimsonText",
              "resources/fonts/CrimsonText-Regular.ttf",
              "resources/fonts/CrimsonText-Bold.ttf",
              "resources/fonts/CrimsonText-Italic.ttf",
              "resources/fonts/CrimsonText-BoldItalic.ttf")

fonts = [{'name': 'CrimsonText', 'point_size': 22, 'style': 'bold'},
         {'name': 'CrimsonText', 'point_size': 22, 'style': 'italic'},
         {'name': 'CrimsonText', 'point_size': 22, 'style': 'bold_italic'}]
