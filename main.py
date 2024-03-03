import pygame
import pygame as pg
import pygame_menu
import sys
import pygame_gui as pg_gui
import random
import config
from pygame_gui.core.utility import create_resource_path


class Game:

    def __init__(self):
        pg.init()
        self.width = config.width
        self.height = config.height
        self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
        pg.display.set_caption("D&D Companion")
        pg.display.set_icon(pg.image.load('images/dice.png'))
        # self.ui_surface = pg.Surface((config.width, config.height//4))
        self.map_surface = pg.Surface((self.width, self.height - self.height // 4))
        self.map = pg.Surface((0, 0))
        self.map_surface_rect = self.map_surface.get_rect()
        self.manager = pg_gui.UIManager((self.width, self.height), "resources/theme.json")
        self.fps_clock = pg.time.Clock()
        self.running = True
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0

        self.ui = pg_gui.elements.UIPanel(manager=self.manager,
                                          relative_rect=pg.Rect(0, self.height - self.height // 4, self.width,
                                                                self.height // 4))
        self.char_btn = pg_gui.elements.UIButton(relative_rect=pg.Rect((10, 10), (
            self.ui.relative_rect.width // 4, (self.ui.relative_rect.height - 30) // 2)), text='CHARACTER LIST',
                                                 manager=self.manager, container=self.ui)
        self.roll_btn = pg_gui.elements.UIButton(
            relative_rect=pg.Rect((10, (self.ui.relative_rect.height - 30) // 2 + 20),
                                  (self.ui.relative_rect.width // 4, (self.ui.relative_rect.height - 30) // 2)),
            text='ROLL THE DICE',
            manager=self.manager, container=self.ui)
        self.load_btn = pg_gui.elements.UIButton(
            relative_rect=pg.Rect((self.ui.relative_rect.width // 4 + 20, 10),
                                  (self.ui.relative_rect.width // 4, (self.ui.relative_rect.height - 30) // 2)),
            text='Upload sprite',
            manager=self.manager, container=self.ui)
        self.map_btn = pg_gui.elements.UIButton(
            relative_rect=pg.Rect(
                (self.ui.relative_rect.width // 4 + 20, (self.ui.relative_rect.height - 30) // 2 + 20),
                (self.ui.relative_rect.width // 4, (self.ui.relative_rect.height - 30) // 2)),
            text='Change map',
            manager=self.manager, container=self.ui)
        self.MapEntities = pg.sprite.RenderUpdates()
        self.active_entity = None
        self.map_file_dialog = None
        self.sprite_file_dialog = None
        self.sprites_id_increment = 0 # found no way to give unique id to sprites, need it to link entities to kill_btn

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
        self.MapEntities.draw(self.map_surface)
        self.screen.blit(self.map_surface, (0, 0))
        self.manager.draw_ui(self.screen)
        # self.screen.blit(self.ui_surface, (0, config.height - config.height // 4))

        pg.display.update()

    def process_events(self):
        for event in pg.event.get():
            self.manager.process_events(event)
            if event.type == pg.QUIT:
                self.running = False
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                print(event.ui_object_id)
            if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_object_id[0]=='k':
                entity_id = int(event.ui_object_id[1:])
                for entity in self.MapEntities:
                    if entity.id == entity_id:
                        event.ui_element.kill()
                        entity.kill()
                        break
            if event.type == pygame.VIDEORESIZE:
                self.resize_screen(event)
            if (event.type == pg_gui.UI_BUTTON_PRESSED and
                    event.ui_element == self.load_btn):
                self.sprite_file_dialog = pg_gui.windows.UIFileDialog(pygame.Rect(0, 0, 400, 600),
                                                                      self.manager,
                                                                      window_title='Upload sprite',
                                                                      initial_file_path='images/',
                                                                      allow_picking_directories=True,
                                                                      allow_existing_files_only=True,
                                                                      allowed_suffixes={""})
                self.load_btn.disable()
            if (event.type == pg_gui.UI_BUTTON_PRESSED and
                    event.ui_element == self.map_btn):
                self.map_file_dialog = pg_gui.windows.UIFileDialog(pygame.Rect(0, 0, 400, 600),
                                                                   self.manager,
                                                                   window_title='Upload map',
                                                                   initial_file_path='images/maps/',
                                                                   allow_picking_directories=True,
                                                                   allow_existing_files_only=True,
                                                                   allowed_suffixes={""})
                self.map_btn.disable()

            if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
                if event.ui_element == self.map_file_dialog:
                    try:
                        resource_path = pg_gui.core.utility.create_resource_path(event.text)
                        loaded_image = pg.image.load(resource_path).convert_alpha()
                        image_rect = loaded_image.get_rect()
                        aspect_ratio = image_rect.width / image_rect.height
                        need_to_scale = False
                        if image_rect.width > self.map_surface_rect.width:
                            image_rect.width = self.map_surface_rect.width
                            image_rect.height = int(image_rect.width / aspect_ratio)
                            need_to_scale = True
                        if image_rect.height > self.map_surface_rect.height:
                            image_rect.height = self.map_surface_rect.height
                            image_rect.width = int(image_rect.height * aspect_ratio)
                            need_to_scale = True
                        if need_to_scale:
                            loaded_image = pygame.transform.smoothscale(loaded_image,
                                                                        image_rect.size)
                        self.map = loaded_image
                    except pg.error:
                        print("Error while changing map, path = ", event.text)
                elif event.ui_element == self.sprite_file_dialog:
                    Entity(event.text, self.sprites_id_increment).add(self.MapEntities)
                    self.sprites_id_increment+=1
            if event.type == pg_gui.UI_WINDOW_CLOSE and event.ui_element == self.map_file_dialog:
                self.map_btn.enable()
                self.map_file_dialog = None
            if event.type == pg_gui.UI_WINDOW_CLOSE and event.ui_element == self.sprite_file_dialog:
                self.load_btn.enable()
                self.sprite_file_dialog = None

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


class Entity(pg.sprite.Sprite):
    def __init__(self, image_path, given_id):
        try:
            pg.sprite.Sprite.__init__(self)
            resource_path = pg_gui.core.utility.create_resource_path(image_path)
            loaded_image = pg.image.load(resource_path).convert_alpha()
            image_rect = loaded_image.get_rect()
            aspect_ratio = image_rect.width / image_rect.height
            need_to_scale = False
            if image_rect.width > config.entity_maxw:
                image_rect.width = config.entity_maxw
                image_rect.height = int(image_rect.width / aspect_ratio)
                need_to_scale = True

            if image_rect.height > config.entity_maxh:
                image_rect.height = config.entity_maxh
                image_rect.width = int(image_rect.height * aspect_ratio)
                need_to_scale = True
            if need_to_scale:
                loaded_image = pygame.transform.smoothscale(loaded_image,
                                                            image_rect.size)
            self.image = loaded_image
            self.rect = image_rect
            self.id = given_id
            self.kill_btn = pg_gui.elements.UIButton(relative_rect = pg.Rect(10, 10, -1, -1), text='X', object_id=f"k{given_id}")

        except pygame.error:
            print("Error while creating sprite, path = ", image_path)
            pass


if __name__ == "__main__":
    game = Game()
    game.run()
