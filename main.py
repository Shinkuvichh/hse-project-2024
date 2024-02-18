import pygame as pg
import pygame_menu
import sys
import pygame_gui as pg_gui
import random
import config


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
        self.manager = pg_gui.UIManager((self.width, self.height), "resources/theme.json")
        self.fps_clock = pg.time.Clock()
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
        self.running = True
        # self.char_btn = pg_gui.elements.UIButton(relative_rect=pg.Rect((350, 275), (100, 50)),
        #  text='Say Hello',
        #  manager=self.manager)
        self.ui = pg_gui.elements.UIPanel(manager=self.manager,
                                          relative_rect=pg.Rect(0, self.height - self.height // 4, self.width,
                                                                self.height // 4))
        self.char_btn = pg_gui.elements.UIButton(relative_rect=pg.Rect((10, 10), (self.ui.relative_rect.width // 4, (self.ui.relative_rect.height - 30) // 2)), text='CHARACTER LIST',
                                                 manager=self.manager, container=self.ui)
        self.roll_btn = pg_gui.elements.UIButton(relative_rect=pg.Rect((10, (self.ui.relative_rect.height - 30) // 2 + 20 ), (self.ui.relative_rect.width // 4, (self.ui.relative_rect.height - 30) // 2)), text='ROLL THE DICE',
                                                 manager=self.manager, container=self.ui)

    def run(self):
        while self.running:
            self.process_events()
            self.render_screen()
            self.fps_clock.tick(config.fps)

    def render_screen(self):
        self.screen.fill((84, 87, 91))
        self.manager.draw_ui(self.screen)
        # self.screen.blit(self.ui_surface, (0, config.height - config.height // 4))
        self.screen.blit(self.map_surface, (0, 0))
        pg.display.update()

    def process_events(self):
        for event in pg.event.get():
            self.manager.update(self.time_delta)
            self.manager.process_events(event)
            if event.type == pg.QUIT:
                self.running = False
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                pass

    def dragdrop(self, event, boxes):
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 1:
                for num, box in enumerate(boxes):
                    if box.collidepoint(event.pos):
                        active_box = num
        if event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                active_box = None
        if event.type == pg.MOUSEMOTION:
            if active_box is not None:
                boxes[active_box].move_ip(event.rel)

    class Entity(pg.sprite.Sprite):
        pass

game = Game()
game.run()
