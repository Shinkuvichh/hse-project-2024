import pickle
from pathlib import Path

from pygame_gui.windows import UIMessageWindow
from commonn import *
import json
from pygame_gui.elements import UIButton, UIWindow, UIImage, UIPanel, UIDropDownMenu, UITextBox
import config
import sys
import trio
from pygame_gui import UIManager

NET_RECEIVED_UPDATE = 0


class ClientEntity(UIWindow):
    # noinspection PyArgumentList
    def __init__(self, string_surface: bytes, scene_ui_manager, width, height, topright, ident,
                 name="New monster"):  # may throw
        init_rect = pg.Rect(0, 0, config.entity_maxw, config.entity_maxh)
        init_rect.topright = topright
        super().__init__(rect=init_rect, object_id="#entity",
                         manager=scene_ui_manager, draggable=False)
        formatted_surface = scale_image(pg.image.frombuffer(buffer=string_surface, size=(width, height),
                                                            format="RGBA"), maxw=config.entity_maxw,
                                        maxh=config.entity_maxh)
        # pycharm thinks that first arg is bytes, however, only buffer= works
        self.id = str(ident)
        self.portrait = UIImage(relative_rect=pg.Rect((0, 0), self.get_container().get_size()),
                                container=self,
                                image_surface=formatted_surface,
                                object_id="#portrait",
                                manager=scene_ui_manager)
        self.name = name
        self.set_display_title(self.name)
        if self.close_window_button is not None:
            self.close_window_button.set_text("-")
        self.title_bar.allow_double_clicks = True
        self.entity_list = ClientEntityList(owner=self, scene_ui_manager=self.ui_manager, name=self.name)
        self.icon_btn = None

    def process_event(self, event: pg.event.Event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_DOUBLE_CLICKED and event.ui_element == self.title_bar:
            self.entity_list.show()

    def show(self):
        super().show()
        self.icon_btn.kill()

    def on_close_window_button_pressed(self):
        self.hide()
        self.icon_btn = UIButton(relative_rect=self.close_window_button.rect,
                                 object_id="#client_entity_icon_button",
                                 manager=self.ui_manager, visible=True, command=self.show, text="")


class ClientEntityList(UIWindow):  # to remake
    def __init__(self, owner: ClientEntity, scene_ui_manager, name):
        super().__init__(rect=pg.Rect(0, 0, config.width // 3, config.height // 2),
                         window_display_title=f'{owner.title_bar.text} character list',
                         object_id="#character_list", visible=False, resizable=False, manager=scene_ui_manager)
        self.set_display_title(f'{name} info list')
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

    def remake_text(self, text):
        self.textbox = UITextBox(relative_rect=self.textbox.relative_rect,
                                 container=self, html_text=text,
                                 object_id="#text_box")

    def on_close_window_button_pressed(self):
        self.hide()


class ClientBoard:
    def __init__(self, character_data):
        self.id = "-1"
        global NET_RECEIVED_UPDATE
        NET_RECEIVED_UPDATE = pg.event.custom_type()
        self.bytebuffer = bytearray()
        self.name = character_data['name']
        self.width = config.width
        self.height = config.height
        self.new_scene = None
        self.send_channel, self.receive_channel = trio.open_memory_channel(max_buffer_size=config.max_buffer_size)
        self.screen = pg.display.set_mode((self.width, self.height), pg.FULLSCREEN if config.fullscreen else 0)
        pg.display.set_caption("D&D Companion")
        self.player_entities = []
        self.map_surface = pg.Surface((self.width, self.height - self.height / 4))
        self.map = pg.Surface((0, 0))
        self.map_surface_rect = self.map_surface.get_rect()
        self.manager = UIManager((self.width, self.height), "resources/theme.json")
        self.manager.add_font_paths(*font_paths)
        self.manager.preload_fonts(fonts)
        self.fps_clock = pg.time.Clock()
        self.time_delta = self.fps_clock.tick(config.fps) / 1000.0

        self.ui = UIPanel(manager=self.manager,
                          relative_rect=pg.Rect(0, self.height - self.height // 4, self.width,
                                                self.height // 4))
        self.save_btn = UIButton(relative_rect=pg.Rect((10, 10), (
            (self.ui.relative_rect.width - 50) // 4, (self.ui.relative_rect.height - 30) // 2)), text='SAVE CHARACTER',
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
            (self.ui.relative_rect.width - 50) // 2, self.ui.relative_rect.height), container=self.ui,
                                  manager=self.manager)
        self.game_log.set_active_effect(pg_gui.TEXT_EFFECT_FADE_IN)
        self.exit_btn = UIButton(relative_rect=pg.Rect(self.width - (self.ui.relative_rect.width - 50) // 4 - 10,
                                                       (self.ui.relative_rect.height - 30) // 2 + 20,
                                                       (self.ui.relative_rect.width - 50) // 4,
                                                       (self.ui.relative_rect.height - 30) // 2), text="LEAVE GAME",
                                 manager=self.manager, container=self.ui)
        self.client_stream = None
        self.map_entities = []
        self.save_popup = None
        try:
            character_data['update'] = 'new_player'
            packet = json.dumps(character_data).encode()
            packet_size = len(packet).to_bytes(4, byteorder='big')
            self.send_channel.send_nowait(packet_size)
            self.send_channel.send_nowait(packet)
        except trio.WouldBlock:
            print("Blocked registration packet")  # can't happen, send channel is empty while initting
            sys.exit()

    async def run(self):
        self.client_stream = await trio.open_tcp_stream(config.host, config.port)
        async with self.client_stream:
            try:
                async with trio.open_nursery() as nursery:
                    print("Starting listener..\n")
                    nursery.start_soon(self.listener, self.client_stream, nursery.cancel_scope)
                    print("Starting sender..\n")
                    nursery.start_soon(self.sender, self.client_stream, nursery.cancel_scope)
                    print("Starting mainloop..\n")
                    nursery.start_soon(self.main_loop, nursery.cancel_scope)
            except Exception as e:
                print(f'Client init failed: {e}')

    async def listener(self, client_stream, cancel_scope):
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
        print("listener: connection closed")
        cancel_scope.cancel()
        self.new_scene = "Launcher"

    async def sender(self, client_stream, cancel_scope):
        while self.new_scene is None:
            try:
                data = await self.receive_channel.receive()
                await client_stream.send_all(data)
            except Exception as e:
                print(f'Sender crashed:{e}')
        cancel_scope.cancel()

    async def main_loop(self, cancel_scope):
        while self.new_scene is None:
            self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
            self.process_events()
            self.manager.update(self.time_delta)
            self.render_screen()
            self.fps_clock.tick(config.fps)
            await trio.sleep(0)
        cancel_scope.cancel()

    def render_screen(self):
        self.map_surface.fill(config.fill_color)
        self.map_surface.blit(self.map, self.map.get_rect(center=self.map_surface_rect.center))
        self.screen.blit(self.map_surface, (0, 0))
        self.manager.draw_ui(self.screen)
        pg.display.update()

    def process_events(self):
        for event in pg.event.get():
            self.manager.process_events(event)
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.exit_btn:
                    self.new_scene = "Launcher"
                if event.ui_element == self.roll_btn:
                    dice_type = int(self.dice_btn.selected_option[0][1:])
                    data = json.dumps({"update": 'roll', "name": self.name, "dice": dice_type}).encode()
                    try:
                        self.send_channel.send_nowait((len(data)).to_bytes(4, "big"))
                        self.send_channel.send_nowait(data)
                    except trio.WouldBlock:
                        print(f"Blocked request for dice roll")
                        return
                if event.ui_element == self.save_btn:
                    for p in self.player_entities:
                        if p.id == self.id:
                            character_data = p.dump()
                            filename = (Path(config.characters_path) / p.char_name).resolve()
                            try:
                                with open(filename, 'wb') as file:
                                    pickle.dump(character_data, file)
                            except OSError as e:
                                self.save_popup = UIMessageWindow(rect=(100, 100, 300, 300),
                                                                  html_message=f"Encountered error while saving"
                                                                               f" character: {e}.<br> Please, try again.",
                                                                  manager=self.manager)
                            else:
                                self.save_popup = UIMessageWindow(rect=(100, 100, 300, 300),
                                                                  html_message=f"Saved {p.char_name} successfully!",
                                                                  manager=self.manager)
                            finally:
                                break

            if event.type == NET_RECEIVED_UPDATE:
                e_dict = event.__dict__
                match e_dict['update']:
                    case 'delete_entity':
                        for entity in self.map_entities:
                            if entity.id == (e_dict['id']):
                                self.map_entities.remove(entity)
                                entity.kill()
                    case 'new_entity':
                        try:
                            self.map_entities.append(
                                ClientEntity(string_surface=e_dict['string'].encode('latin1'),
                                             scene_ui_manager=self.manager,
                                             width=e_dict['width'], height=e_dict['height'],
                                             topright=self.get_cords_from_ratio(e_dict['ratio_x'], e_dict['ratio_y']),
                                             ident=e_dict['id'], name=e_dict['name']))
                        except pg.error:
                            print(pg.error)
                    case 'roll':
                        self.game_log.append_html_text(
                            f'<p><strong>{e_dict["name"]}</strong> rolled <strong>D{e_dict["dice"]}</strong> '
                            f'and got {e_dict["result"]}.</p>')
                    case 'player_left':
                        self.game_log.append_html_text(
                            f'<p><strong>{e_dict["name"]}</strong> left the game.</p>')
                        removed_id = e_dict['id']
                        for p in self.player_entities:
                            if p.id == removed_id:
                                p.kill()
                                self.player_entities.remove(p)
                                break

                    case 'map':
                        self.map = scale_image(
                            pg.image.frombuffer(e_dict['string'].encode('latin1'),
                                                size=(e_dict['width'], e_dict['height']),
                                                format="RGBA"), maxw=self.map_surface_rect.w,
                            maxh=self.map_surface_rect.h)
                    case 'cords':
                        cords = e_dict['entity:topright']
                        for entity in self.map_entities:
                            if entity.id in cords:
                                x, y = self.get_cords_from_ratio(*cords[entity.id])
                                x -= entity.relative_rect.width
                                entity.set_position((x, y))
                    case 'new_player':
                        self.player_entities.append(
                            PlayerEntity(manager=self.manager, character_data=e_dict, ident=e_dict['id'],
                                         client_mode=True))
                    case 'player_sheet':
                        for p in self.player_entities:
                            if p.id == e_dict['id']:
                                p.char_sheet.load_from_list(e_dict['list'])
                    case 'player_cords':
                        cords = e_dict['entity:topright']
                        for player in self.player_entities:
                            p_id = str(player.id)
                            if p_id in cords:
                                x, y = self.get_cords_from_ratio(*cords[p_id])
                                x -= player.relative_rect.width
                                player.set_position((x, y))

                    case 'entity_list':
                        for entity in self.map_entities:
                            if entity.id == e_dict['id']:
                                entity.entity_list.remake_text(e_dict['list'])
                    case 'load_game':
                        for entity in self.map_entities:
                            entity.kill()
                            self.map_entities.remove(entity)
                    case 'init':
                        self.id = str(e_dict['id'])
                        self.save_btn.enable()

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
        return x, y
