from commonn import *
import json
from pygame_gui.elements import UIButton, UIWindow, UIImage, UIPanel, UIDropDownMenu, UITextBox
import config
import sys
import trio
from pygame_gui import UIManager


class ClientEntity(UIWindow):
    def __init__(self, string_surface: bytes, scene_ui_manager, width, height, topright, ident):  # may throw
        init_rect = pg.Rect(0, 0, config.entity_maxw, config.entity_maxh)
        init_rect.topright = topright
        super().__init__(rect=init_rect, object_id="#entity",
                         manager=scene_ui_manager, draggable=False)
        formatted_surface = scale_image(pg.image.frombuffer(buffer=string_surface, size=(width, height),
                                                            format="RGBA"), maxw=config.entity_maxw,
                                        maxh=config.entity_maxh)
        self.id = ident
        self.portrait = UIImage(relative_rect=pg.Rect((0, 0), self.get_container().get_size()),
                                container=self,
                                image_surface=formatted_surface,
                                object_id="#portrait",
                                manager=scene_ui_manager)

        if self.close_window_button is not None:
            self.close_window_button.set_text("-")
        self.title_bar.allow_double_clicks = True
        self.set_display_title("DEBUG MONSTER")
        self.char_list = ClientEntityList(self, scene_ui_manager=self.ui_manager)
        self.icon_btn = None

    def process_event(self, event: pg.event.Event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_DOUBLE_CLICKED and event.ui_element == self.title_bar:
            self.char_list.show()

    def show(self):
        super().show()
        self.icon_btn.kill()

    def on_close_window_button_pressed(self):
        self.hide()
        self.icon_btn = UIButton(relative_rect=self.close_window_button.rect,
                                 object_id="#icon_button",
                                 manager=self.ui_manager, visible=True, command=self.show, text="")


class ClientEntityList(UIWindow):  # to remake
    def __init__(self, owner: ClientEntity, scene_ui_manager):
        super().__init__(rect=pg.Rect(0, 0, config.width // 3, config.height // 2),
                         window_display_title=f'{owner.title_bar.text} character list',
                         object_id="#character_list", visible=False, resizable=False, manager=scene_ui_manager)

        self.close_window_button.set_text("×")
        w = self.get_container().get_rect().width
        h = self.get_container().get_rect().height
        title_h = self.title_bar.relative_rect.height
        self.textbox = UITextBox(relative_rect=pg.Rect(0, 0, w, h - title_h - 20),
                                 container=self, html_text="No character list for this entity!",
                                 object_id="#text_box")
        self.owner_entity = owner

    def process_event(self, event):
        super().process_event(event)

    def on_close_window_button_pressed(self):
        self.hide()


class ClientBoard:
    def __init__(self):
        global NET_RECEIVED_UPDATE
        NET_RECEIVED_UPDATE = pg.event.custom_type()
        self.bytebuffer = bytearray()
        self.name = "ClientB"
        self.width = config.width
        self.height = config.height
        self.send_channel, self.receive_channel = trio.open_memory_channel(max_buffer_size=config.max_buffer_size)
        self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
        pg.display.set_caption("D&D Companion")

        self.map_surface = pg.Surface((self.width, self.height - self.height / 4))
        self.map = pg.Surface((0, 0))
        self.map_surface_rect = self.map_surface.get_rect()
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        self.manager.add_font_paths(*font_paths)
        self.manager.preload_fonts(fonts)
        self.fps_clock = pg.time.Clock()
        self.running = True
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0

        self.ui = UIPanel(manager=self.manager,
                          relative_rect=pg.Rect(0, self.height - self.height // 4, self.width,
                                                self.height // 4))
        self.char_btn = UIButton(relative_rect=pg.Rect((10, 10), (
            (self.ui.relative_rect.width - 50) // 4, (self.ui.relative_rect.height - 30) // 2)), text='CHARACTER LIST',
                                 manager=self.manager, container=self.ui)
        self.roll_btn = UIButton(relative_rect=pg.Rect((10, (self.ui.relative_rect.height - 30) // 2 + 20), (
            (self.ui.relative_rect.width - 50) / 16 * 3, (self.ui.relative_rect.height - 30) // 2)), text='ROLL',
                                 manager=self.manager, container=self.ui)
        self.dice_btn = UIDropDownMenu(options_list=["D4", "D6", "D8", "D10", "D12", "D16", "D20"],
                                       relative_rect=pg.Rect((10 + (self.ui.relative_rect.width - 50) / 16 * 3,
                                                              (self.ui.relative_rect.height - 30) // 2 + 20),
                                                             ((self.ui.relative_rect.width - 50) // 16,
                                                              (self.ui.relative_rect.height - 30) // 2)),
                                       manager=self.manager, container=self.ui, starting_option="D20")

        self.game_log = UITextBox("Game started.\n", relative_rect=pg.Rect(
            (self.ui.relative_rect.width - 50) // 4 + 20, 0,
            (self.ui.relative_rect.width - 50) // 4, self.ui.relative_rect.height), container=self.ui,
                                  manager=self.manager)
        self.game_log.set_active_effect(pg_gui.TEXT_EFFECT_FADE_IN)
        self.client_stream = None
        self.MapEntities = []

    async def run(self):
        self.client_stream = await trio.open_tcp_stream("127.0.0.1", config.port)
        async with self.client_stream:
            async with trio.open_nursery() as nursery:
                print("Starting listener..\n")
                nursery.start_soon(self.listener, self.client_stream)
                print("Starting sender..\n")
                nursery.start_soon(self.sender, self.client_stream)
                print("Starting mainloop..\n")
                nursery.start_soon(self.main_loop)

    async def listener(self, client_stream):
        print("listener started!")  # debug
        async for data in client_stream:  # use length prefixes
            self.bytebuffer.extend(data)
            if len(self.bytebuffer) >= 4:
                packet_size = int.from_bytes(self.bytebuffer[:4], byteorder='big')
                if len(self.bytebuffer) >= 4 + packet_size:
                    packet = json.loads((self.bytebuffer[4:4 + packet_size]).decode())
                    del self.bytebuffer[0:4 + packet_size]
                    event = pg.event.Event(NET_RECEIVED_UPDATE, packet)
                    pg.event.post(event)
                    await trio.sleep(0)
        print("receiver: connection closed")

    async def sender(self, client_stream):
        while True:  # change to while scene
            data = await self.receive_channel.receive()
            await client_stream.send_all(data)
            await trio.sleep(0)

    async def main_loop(self):
        while self.running:
            self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
            self.process_net_updates()
            self.process_events()
            self.manager.update(self.time_delta)
            self.render_screen()
            self.fps_clock.tick(config.fps)
            await trio.sleep(0)

    def process_net_updates(self):
        try:
            pass
        except trio.WouldBlock:
            return

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
            if event.type == pg.QUIT:
                self.running = False
                pg.quit()
                sys.exit()

            if (event.type == pg_gui.UI_BUTTON_PRESSED and
                    event.ui_element == self.roll_btn):
                dice_type = int(self.dice_btn.selected_option[0][1:])
                data = json.dumps({"update": 'roll', "name": self.name, "dice": dice_type}).encode()
                try:
                    self.send_channel.send_nowait(data)
                except trio.WouldBlock:
                    print(f"Blocked request for dice roll")
                    return
            if event.type == NET_RECEIVED_UPDATE:
                dict = event.__dict__
                match dict['update']:
                    case 'delete_entity':
                        for entity in self.MapEntities:
                            if entity.id == dict['id']:
                                self.MapEntities.remove(entity)
                                entity.kill()
                    case 'new_entity':
                        try:

                            self.MapEntities.append(
                                ClientEntity(string_surface=dict['string'].encode('latin1'),
                                             scene_ui_manager=self.manager,
                                             width=dict['width'], height=dict['height'],
                                             topright=self.get_cords_from_ratio(dict['ratio_x'], dict['ratio_y']),
                                             ident=dict['id']))
                        except pg.error:
                            print(pg.error)
                    case 'roll':
                        self.game_log.append_html_text(
                            f'<p><strong>{dict["name"]}</strong> rolled <strong>D{dict["dice"]}</strong> and got {dict["result"]}.</p>')
                    case 'player_left':
                        self.game_log.append_html_text(
                            f'<p><strong>{dict["name"]}</strong> left the game.</p>')
                    case 'map':
                        self.map = scale_image(
                            pg.image.frombuffer(dict['string'].encode('latin1'), size=(dict['width'], dict['height']),
                                                format="RGBA"), maxw=self.map_surface_rect.w,
                            maxh=self.map_surface_rect.h)
                    case 'cords':
                        cords = dict['entity:topright']
                        for entity in self.MapEntities:
                            id = str(entity.id)
                            if id in cords:
                                x, y = self.get_cords_from_ratio(*cords[id])
                                x -= entity.relative_rect.width
                                entity.set_position((x,y))

            if config.debug:
                if event.type == pg.KEYDOWN and event.key == pg.K_d:
                    print('debug mode on')
                    self.manager.set_visual_debug_mode(True)
                if event.type == pg.KEYUP and event.key == pg.K_d:
                    print('debug mode off')
                    self.manager.set_visual_debug_mode(False)
                if event.type == pg_gui.UI_BUTTON_PRESSED:
                    print(event.ui_object_id)

    def get_cords_from_ratio(self, ratio_x, ratio_y):
        delta_x, delta_y = self.map.get_rect().topleft
        x = delta_x + self.map.get_rect().width * ratio_x
        y = delta_y + self.map.get_rect().height * ratio_y
        return (x, y)
