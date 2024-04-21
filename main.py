# cant prevent UserWarning, details : https//github.com/MyreMylar/pygame_gui/issues/192
import sys
from launcher import *

import config
from maps.maps_issue import similar_description


class Game:

    def __init__(self):
        pg.init()
        self.width = config.width
        self.height = config.height
        # self.screen = pg.display.set_mode((0,0), pg.FULLSCREEN)
        self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
        pg.display.set_caption("D&D Companion")
        # pg.display.set_icon(pg.image.load('images/dice.png'))
        # self.ui_surface = pg.Surface((config.width, config.height//4))
        self.map_surface = pg.Surface((self.width, self.height - self.height / 4))
        self.map = pg.Surface((0, 0))
        self.map_surface_rect = self.map_surface.get_rect()
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        # self.manager.add_font_paths()
        self.fps_clock = pg.time.Clock()
        self.running = True
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0

        self.ui = UIPanel(manager=self.manager,
                          relative_rect=pg.Rect(0, self.height - self.height // 4, self.width,
                                                self.height // 4))
        self.char_btn = UIButton(relative_rect=pg.Rect((10, 10), (
            (self.ui.relative_rect.width - 50) // 4, (self.ui.relative_rect.height - 30) // 2)), text='CHARACTER LIST',
                                 manager=self.manager, container=self.ui)
        self.char_btn.disable()
        self.roll_btn = UIButton(relative_rect=pg.Rect((10, (self.ui.relative_rect.height - 30) // 2 + 20), (
            (self.ui.relative_rect.width - 50) / 16 * 3, (self.ui.relative_rect.height - 30) // 2)), text='ROLL',
                                 manager=self.manager, container=self.ui)
        self.dice_btn = UIDropDownMenu(options_list=["D4", "D6", "D8", "D10", "D12", "D16", "D20"],
                                       relative_rect=pg.Rect((10 + (self.ui.relative_rect.width - 50) / 16 * 3,
                                                              (self.ui.relative_rect.height - 30) // 2 + 20),
                                                             ((self.ui.relative_rect.width - 50) // 16,
                                                              (self.ui.relative_rect.height - 30) // 2)),
                                       manager=self.manager, container=self.ui, starting_option="D20")
        self.load_btn = UIButton(
            relative_rect=pg.Rect(((self.ui.relative_rect.width - 50) // 4 + 20, 10),
                                  ((self.ui.relative_rect.width - 50) // 4, (self.ui.relative_rect.height - 30) // 2)),
            text='Upload sprite',
            manager=self.manager, container=self.ui)
        self.map_btn = UIButton(
            relative_rect=pg.Rect(
                ((self.ui.relative_rect.width - 50) // 4 + 20, (self.ui.relative_rect.height - 30) // 2 + 20),
                ((self.ui.relative_rect.width - 50) // 4, (self.ui.relative_rect.height - 30) // 2)),
            text='Change map',
            manager=self.manager, container=self.ui)
        self.game_log = UITextBox("Game started.\n", relative_rect=pg.Rect(
            (self.ui.relative_rect.width - 50) // 4 * 2 + 30, 0,
            (self.ui.relative_rect.width - 50) // 4, self.ui.relative_rect.height), container=self.ui)
        self.game_log.set_active_effect(pg_gui.TEXT_EFFECT_FADE_IN)
        self.MapEntities = []
        self.active_entity = None
        self.map_file_dialog = None
        self.sprite_file_dialog = None

    def resize_screen(self, event):
        self.width = event.w
        self.height = event.h
        pass

    def run(self):
        while self.running:
            self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
            self.process_events()
            self.manager.update(self.time_delta)
            self.render_screen()
            self.fps_clock.tick(config.fps)

    def render_screen(self):
        self.map_surface.fill(config.fill_color)
        self.map_surface.blit(self.map, self.map.get_rect(center=self.map_surface_rect.center))
        # self.MapEntities.draw(self.map_surface)
        self.screen.blit(self.map_surface, (0, 0))
        self.manager.draw_ui(self.screen)
        # self.screen.blit(self.ui_surface, (0, config.height - config.height // 4))

        pg.display.update()

    def process_events(self):
        for event in pg.event.get():
            self.manager.process_events(event)
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                print(event.ui_object_id)
            if event.type == pg.QUIT:
                self.running = False
                pg.quit()
                sys.exit()
            if event.type == pg.VIDEORESIZE:
                self.resize_screen(event)

            if (event.type == pg_gui.UI_BUTTON_PRESSED and
                    event.ui_element == self.load_btn):
                self.sprite_file_dialog = UIFileDialog(pygame.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                                                       self.manager,
                                                       window_title='Upload sprite',
                                                       initial_file_path='images/',
                                                       allow_picking_directories=False,
                                                       allow_existing_files_only=True,
                                                       allowed_suffixes={""})

                self.sprite_file_dialog.refresh_button.kill()
                self.sprite_file_dialog.delete_button.kill()
                self.sprite_file_dialog.parent_directory_button.kill()
                self.sprite_file_dialog.home_button.kill()
                self.load_btn.disable()
            if (event.type == pg_gui.UI_BUTTON_PRESSED and
                    event.ui_element == self.map_btn):
                self.map_file_dialog = MapFileDialog(text="Upload map",init_path=config.player_maps_path)
                self.map_btn.disable()
            if (event.type == pg_gui.UI_BUTTON_PRESSED and
                    event.ui_element == self.roll_btn):
                dice_type = int(self.dice_btn.selected_option[1:])
                self.game_log.append_html_text(
                    f'<p><strong>You</strong> rolled <strong>D{dice_type}</strong> and got {randint(1, dice_type)}.</p>')
            if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
                if event.ui_element == self.map_file_dialog:
                    try:
                        self.map = image_to_surface(event.text, self.map_surface_rect.w, self.map_surface_rect.h)
                    except pg.error:
                        print("Error while changing map, path = ", event.text)
                elif event.ui_element == self.sprite_file_dialog:
                    try:
                        self.MapEntities.append(Entity(event.text))
                    except pg.error:
                        print(pg.error)

            if event.type == pg_gui.UI_WINDOW_CLOSE and event.ui_element == self.map_file_dialog:
                self.map_btn.enable()
                self.map_file_dialog = None
            if event.type == pg_gui.UI_WINDOW_CLOSE and event.ui_element == self.sprite_file_dialog:
                self.load_btn.enable()
                self.sprite_file_dialog = None
            if config.debug:
                if event.type == pg.KEYDOWN and event.key == pg.K_d:
                    print('debug mode on')
                    self.manager.set_visual_debug_mode(True)
                if event.type == pg.KEYUP and event.key == pg.K_d:
                    print('debug mode off')
                    self.manager.set_visual_debug_mode(False)


def dragndrop(event, self):  # unused
    if event.type == pg.MOUSEBUTTONDOWN:
        if event.button == 1:
            for entity in self.MapEntities:
                if entity.rect.collidepoint(event.pos):
                    self.active_entity = entity
    if event.type == pg.MOUSEBUTTONUP:
        if event.button == 1:
            self.active_entity = None
    if event.type == pg.MOUSEMOTION:
        if self.active_entity is not None:
            self.active_entity.rect.move_ip(event.rel)
            self.active_entity.rect.clamp_ip(self.map_surface_rect)


def image_to_surface(image_path, maxw, maxh):
    resource_path = pg_gui.core.utility.create_resource_path(image_path)
    loaded_image = pg.image.load(resource_path).convert_alpha()
    image_rect = loaded_image.get_rect()
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
        loaded_image = pygame.transform.smoothscale(loaded_image,
                                                    image_rect.size)
    return loaded_image


class Entity(UIWindow):
    def __init__(self, image_path):  # may throw
        super().__init__(rect=pg.Rect((30, 30), (config.entity_maxw, config.entity_maxh)), object_id="#entity")

        self.portrait = UIImage(relative_rect=pg.Rect((0, 0), self.get_container().get_size()),
                                container=self,
                                image_surface=image_to_surface(image_path, config.entity_maxw, config.entity_maxh),
                                object_id="#portrait")

        self.title_bar.allow_double_clicks = True
        self.set_display_title(image_path[image_path.rfind('/')+1:image_path.rfind('.')])
        self.char_list = CharacterList(self)
        if self.close_window_button is not None:
            self.close_window_button.set_text("...")  # override

    def process_event(self, event: pygame.event.Event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_DOUBLE_CLICKED and event.ui_element == self.title_bar:
            self.char_list.show()


class CharacterList(UIWindow):
    def __init__(self, owner: Entity):
        super().__init__(rect=pg.Rect(0, 0, config.width // 3, config.height // 2),
                         window_display_title=f'{owner.title_bar.text} character list',
                         object_id="#character_list", visible=False, resizable=False)
        self.close_window_button.set_text("×")
        w = self.get_container().get_rect().width
        h = self.get_container().get_rect().height
        title_h = self.title_bar.relative_rect.height
        print(self.relative_rect.w)
        self.textbox = UITextBox(relative_rect=pg.Rect(0, 0, w, h - title_h - 20),
                                 container=self, html_text="Upload this character's list from file.",
                                 object_id="#text_box")
        self.delete_btn = UIButton(relative_rect=pg.Rect(10, -title_h - 10, (w - 30) // 2, title_h), container=self,
                                   text="Delete entity",
                                   anchors={"bottom": "bottom"}, object_id="#delete_button", starting_height=2)
        self.upload_btn = UIButton(relative_rect=pg.Rect(-10 - (w - 30) // 2, -title_h - 10, (w - 30) // 2, title_h),
                                   container=self, text="Upload", anchors={"bottom": "bottom", "right": "right"},
                                   object_id="#upload_button", starting_height=2)
        self.owner_entity = owner
        self.list_file_dialog = None

    def process_event(self, event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_element == self.delete_btn:
            self.owner_entity.kill()
            self.kill()
        if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_element == self.upload_btn:
            self.list_file_dialog = UIFileDialog(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                                                 window_title='Choose file',
                                                 initial_file_path='character lists/',
                                                 allow_picking_directories=False,
                                                 allow_existing_files_only=True,
                                                 allowed_suffixes={""}, manager=None)

            self.list_file_dialog.refresh_button.kill()
            self.list_file_dialog.delete_button.kill()
            self.list_file_dialog.parent_directory_button.kill()
            self.list_file_dialog.home_button.kill()
            self.upload_btn.disable()
        if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
            if event.ui_element == self.list_file_dialog:
                try:
                    resource_path = pg_gui.core.utility.create_resource_path(event.text)
                    text = Path(resource_path).read_text()
                    self.textbox.set_text(text)
                except pg.error:
                    print("Error while uploading char list, path = ", event.text)
        if event.type == pg_gui.UI_WINDOW_CLOSE and event.ui_element == self.list_file_dialog:
            self.upload_btn.enable()
            self.list_file_dialog = None

    def on_close_window_button_pressed(self):
        self.hide()


class MapFileDialog(UIFileDialog):
    def __init__(self, text, init_path):
        super().__init__(pygame.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                         window_title=text,
                         initial_file_path=init_path,
                         allow_picking_directories=False,
                         allow_existing_files_only=True,
                         allowed_suffixes={""}, object_id="#map_dialog", manager=None)
        self.refresh_button.kill()
        self.delete_button.kill()
        self.parent_directory_button.kill()
        self.home_button.kill()
        w, h = self.get_container().get_size()
        self.map_prompt_text_line = UITextEntryLine(
            relative_rect=pg.Rect(10, 40, self.get_container().get_size()[0] - 20, -1), container=self, initial_text="", object_id="#prompt_textline")
        self.map_prompt_text_line.hide()
        self.gen_btn = UIButton(relative_rect=pg.Rect(10, 10, -1, 30), text="Generate by description", container=self)

    def process_event(self, event):
        super().process_event(event)
        if event.type == pg_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.map_prompt_text_line:
            generated_map_path = similar_description(self.map_prompt_text_line.get_text())[0]
            event_data = {'text': str(generated_map_path),
                          'ui_element': self,
                          'ui_object_id': self.most_specific_combined_id}
            pg.event.post(pg.event.Event(pg_gui.UI_FILE_DIALOG_PATH_PICKED, event_data))
            self.kill()
        if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_element == self.gen_btn:
            self.file_path_text_line.hide()
            self.map_prompt_text_line.show()




if __name__ == "__main__":
    game = Game()
    game.run()