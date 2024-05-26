import json
import queue
import os

import trio

from commonn import *
from itertools import count
from base64 import b64encode, b64decode


class Player:
    def __init__(self, ident):
        self.id = ident
        self.name = 'clientName'
        self.send_channel, self.receive_channel = trio.open_memory_channel(max_buffer_size=config.max_buffer_size)
        self.sent_sprites = []
        self.ingame = True


class Entity(UIWindow):
    def __init__(self, image_path, scene_ui_manager, id):  # may throw
        super().__init__(rect=pg.Rect((30, 30), (config.entity_maxw, config.entity_maxh)), object_id="#entity",
                         manager=scene_ui_manager)
        self.portrait = UIImage(relative_rect=pg.Rect((0, 0), self.get_container().get_size()),
                                container=self,
                                image_surface=img_path_to_surface(image_path, config.entity_maxw, config.entity_maxh),
                                object_id="#portrait",
                                manager=self.ui_manager)
        self.title_bar.allow_double_clicks = True
        self.set_display_title(image_path[image_path.rfind('/') + 1:image_path.rfind('.')])
        self.char_list = CharacterList(self, scene_ui_manager=self.ui_manager)
        if self.close_window_button is not None:
            self.close_window_button.set_text("-")  # override
        self.id = id
        self.icon_btn = None

    def show(self):
        super().show()
        self.icon_btn.kill()

    def process_event(self, event: pg.event.Event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_DOUBLE_CLICKED and event.ui_element == self.title_bar:
            self.char_list.show()

    def on_close_window_button_pressed(self):
        self.hide()
        self.icon_btn = UIButton(relative_rect=self.close_window_button.rect,
                                 object_id="#icon_button",
                                 manager=self.ui_manager, visible=True, command=self.show, text="")


class MapFileDialog(UIFileDialog):
    def __init__(self, text, init_path, scene_ui_manager):
        super().__init__(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                         window_title=text,
                         initial_file_path=init_path,
                         allow_picking_directories=False,
                         allow_existing_files_only=True,
                         allowed_suffixes={""}, object_id="#map_dialog", manager=scene_ui_manager)
        self.refresh_button.kill()
        self.delete_button.kill()
        self.parent_directory_button.kill()
        self.home_button.kill()
        w, h = self.get_container().get_size()
        self.map_prompt_text_line = UITextEntryLine(
            relative_rect=pg.Rect(10, 40, self.get_container().get_size()[0] - 20, -1), container=self,
            initial_text="",
            object_id="#prompt_textline", manager=scene_ui_manager)
        self.map_prompt_text_line.hide()
        self.gen_btn = UIButton(relative_rect=pg.Rect(10, 10, -1, 30), text="Generate by description",
                                container=self, manager=scene_ui_manager)

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


class CharacterList(UIWindow):  # THIS IS HOST VERSION!
    def __init__(self, owner: Entity, scene_ui_manager):
        super().__init__(rect=pg.Rect(0, 0, config.width // 3, config.height // 2),
                         window_display_title=f'{owner.title_bar.text} character list',
                         object_id="#character_list", visible=False, resizable=False, manager=scene_ui_manager)
        self.close_window_button.set_text("×")
        w = self.get_container().get_rect().width
        h = self.get_container().get_rect().height
        title_h = self.title_bar.relative_rect.height
        self.textbox = UITextBox(relative_rect=pg.Rect(0, 0, w, h - title_h - 20),
                                 container=self, html_text="Upload this character's list from file.",
                                 object_id="#text_box", manager=scene_ui_manager)
        self.delete_btn = UIButton(relative_rect=pg.Rect(10, -title_h - 10, (w - 30) // 2, title_h), container=self,
                                   text="Delete entity",
                                   anchors={"bottom": "bottom"}, object_id="#delete_button", starting_height=2,
                                   manager=scene_ui_manager)
        self.upload_btn = UIButton(
            relative_rect=pg.Rect(-10 - (w - 30) // 2, -title_h - 10, (w - 30) // 2, title_h),
            container=self, text="Upload", anchors={"bottom": "bottom", "right": "right"},
            object_id="#upload_button", starting_height=2, manager=scene_ui_manager)
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
                                                 allowed_suffixes={""}, manager=self.ui_manager)

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


class HostBoard:

    def __init__(self):

        self.NET_RECEIVED_UPDATE = pg.event.custom_type()
        self.debug_ev = pg.event.Event(self.NET_RECEIVED_UPDATE, {'update': 'roll', 'name': 'ClientB', 'dice': 20})
        self.data_queue = None
        self.players = []

        self.put_channel, self.get_channel = trio.open_memory_channel(max_buffer_size=100)
        self.connection_counter = count()
        self.sprites_counter = count()
        self.width = config.width
        self.height = config.height
        self.screen = pg.display.set_mode((self.width, self.height))
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
        self.send_btn = UIButton(relative_rect=pg.Rect(10, 10, (self.ui.relative_rect.width - 50) // 8,
                                                       (self.ui.relative_rect.height - 30) // 2), text='Send map',
                                 manager=self.manager, container=self.ui)
        self.save_btn = UIButton(relative_rect=pg.Rect(10 + (self.ui.relative_rect.width - 50) // 8, 10,
                                                       (self.ui.relative_rect.width - 50) // 8,
                                                       (self.ui.relative_rect.height - 30) // 2), text='Save game',
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
            (self.ui.relative_rect.width - 50) // 4, self.ui.relative_rect.height), container=self.ui,
                                  manager=self.manager)
        self.game_log.set_active_effect(pg_gui.TEXT_EFFECT_FADE_IN)
        self.MapEntities = []
        self.map_file_dialog = None
        self.sprite_file_dialog = None

    async def initialize_player(self, server_stream):
        ident = next(self.connection_counter)
        print(f"echo_server {ident}: started")
        try:
            player = Player(ident)
            self.players.append(player)
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self.listener, server_stream, nursery.cancel_scope)
                nursery.start_soon(self.sender, server_stream, player.receive_channel, nursery.cancel_scope)
        except Exception as exc:
            print(f"server {ident}: crashed: {exc!r}")
        finally:
            self.remove_player(ident)

    def remove_player(self, id):
        for p in self.players:
            if p.id == id:
                packet = {'update': 'player_left', 'name': p.name}
                self.game_log.append_html_text(
                    f'<p><strong>{p.name}</strong> left the game.</p>')
                self.players.remove(p)
                # delete from bottom panel
                self.send_packet(packet)
                return

    async def listener(self, server_stream, cancel_scope):
        async for data in server_stream:
            data_decoded = json.loads(data.decode())
            event = pg.event.Event(self.NET_RECEIVED_UPDATE, data_decoded)
            pg.event.post(event)
        cancel_scope.cancel()

    async def sender(self, server_stream, game_stream, cancel_scope):
        async for data in game_stream:
            try:
                await server_stream.send_all(data)
            except trio.BrokenResourceError:
                break
        cancel_scope.cancel()

    async def run(self):
        async with trio.open_nursery() as nursery:
            print("Starting mainloop..\n")
            nursery.start_soon(self.main_loop)
            nursery.start_soon(trio.serve_tcp, self.initialize_player, config.port)

    async def main_loop(self):
        while self.running:
            self.time_delta = self.fps_clock.tick(config.fps) / 1000.0
            self.process_events()
            self.manager.update(self.time_delta)
            self.render_screen()
            self.fps_clock.tick(config.fps)
            await trio.sleep(0)

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
                self.running = False
                pg.quit()
                sys.exit()
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                print(event.ui_object_id)
                if event.ui_element == self.load_btn:
                    self.sprite_file_dialog = UIFileDialog(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
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
                if event.ui_element == self.map_btn:
                    self.map_file_dialog = MapFileDialog(text="Upload map", init_path=config.player_maps_path,
                                                         scene_ui_manager=self.manager)
                    self.map_btn.disable()
                if event.ui_element == self.roll_btn:
                    self.roll_dice("Master", self.dice_btn.selected_option[1:])
                if event.ui_element == self.send_btn:
                    for entity in self.MapEntities:
                        surface = entity.portrait.image
                        bytes = pg.image.tobytes(surface, format="RGBA")
                        packet = {'update': 'surface', 'string': bytes.decode(encoding='latin1'),
                                  'width': surface.get_width(), 'height': surface.get_height()}
                        packet = json.dumps(packet).encode()
                        packet_size = len(packet).to_bytes(4, byteorder='big')
                        for player in self.players:
                            if entity.id not in player.sent_sprites:
                                player.send_channel.send_nowait(packet_size)
                                player.send_channel.send_nowait(packet)
                                player.sent_sprites.append(entity.id)
                    self.send_map()
                if event.ui_object_id == "icon_button":
                    event.ui_element.entity.show()
                    event.ui_element.kill()

            if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
                if event.ui_element == self.map_file_dialog:
                    try:
                        self.map = img_path_to_surface(event.text, self.map_surface_rect.w, self.map_surface_rect.h)
                    except pg.error:
                        print("Error while changing map, path = ", event.text)
                elif event.ui_element == self.sprite_file_dialog:
                    try:
                        self.MapEntities.append(
                            Entity(event.text, scene_ui_manager=self.manager, id=next(self.sprites_counter)))
                    except pg.error as error:
                        print(f'Error while creating entity: {error}')

            if event.type == pg_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.map_file_dialog:
                    self.map_btn.enable()
                    self.map_file_dialog = None
                if event.ui_element == self.sprite_file_dialog:
                    self.load_btn.enable()
                    self.sprite_file_dialog = None
            if event.type == self.NET_RECEIVED_UPDATE:
                print(event)
                print(event.__dict__)
                if event.__dict__['update'] == 'roll':
                    print("got event")
                    data = event.__dict__
                    self.roll_dice(data['name'], data['dice'])
            if config.debug:
                if event.type == pg.KEYDOWN and event.key == pg.K_d:
                    print('debug mode on')
                    self.manager.set_visual_debug_mode(True)
                if event.type == pg.KEYUP and event.key == pg.K_d:
                    print('debug mode off')
                    self.manager.set_visual_debug_mode(False)
                if event.type == pg_gui.UI_BUTTON_PRESSED:
                    print(event.ui_object_id)

    def roll_dice(self, roller_name, dice_type):
        result = randint(1, int(dice_type))
        self.game_log.append_html_text(
            f'<p><strong>{roller_name}</strong> rolled <strong>D{dice_type}</strong> and got {result}.</p>')
        data = {"update": 'roll', "name": roller_name, "dice": dice_type, "result": result}
        self.send_packet(data)

    def send_map(self):
        bytes = pg.image.tobytes(self.map, format="RGBA")
        packet = {'update': 'map', 'string': bytes.decode(encoding='latin1'), 'width': self.map.get_width(),
                  'height': self.map.get_height()}
        self.send_packet(packet)

    def send_surface(self, surface):  # remake for client pp send
        bytes = pg.image.tobytes(surface, format="RGBA")
        packet = {'update': 'surface', 'string': bytes.decode(encoding='latin1'), 'width': surface.get_width(),
                  'height': surface.get_height()}
        self.send_packet(packet)

    def send_packet(self, unencoded_packet):
        packet = json.dumps(unencoded_packet).encode()
        packet_size = len(packet).to_bytes(4, byteorder='big')
        try:
            for player in self.players:
                player.send_channel.send_nowait(packet_size)
                player.send_channel.send_nowait(packet)
        except trio.WouldBlock:  # raise a warning for host
            return

    def get_relative_cords(self):
        pass
