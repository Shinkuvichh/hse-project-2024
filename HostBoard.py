import json
import pickle
import sys
from itertools import count
from pathlib import Path
from random import randint

import trio
from pygame_gui import UIManager
from pygame_gui.elements import UIPanel, UIDropDownMenu
from pygame_gui.windows import UIFileDialog

from commonn import *

NET_RECEIVED_UPDATE = 0
ENTITY_DELETED = 0


class Entity(UIWindow):
    def __init__(self, scene_ui_manager, ident, image_path=None, bytes_image=None, list_text=None, size=None,
                 topright=None, name="New entity"):  # may throw
        init_rect = pg.Rect(30, 30, config.entity_maxw, config.entity_maxh)
        if topright is not None:
            init_rect.topright = topright
        super().__init__(rect=init_rect, object_id="#entity",
                         manager=scene_ui_manager)
        if bytes_image is not None:
            image = pg.image.frombytes(bytes_image, format="RGBA", size=size)
        else:
            image = img_path_to_surface(image_path, config.entity_maxw, config.entity_maxh)
        self.portrait = UIImage(relative_rect=pg.Rect((0, 0), self.get_container().get_size()),
                                container=self,
                                image_surface=image,
                                object_id="#portrait",
                                manager=self.ui_manager)
        self.title_bar.allow_double_clicks = True
        self.set_display_title(name)
        self.name = name
        self.entity_list = EntityList(self, scene_ui_manager=self.ui_manager, text=list_text)
        self.changed_list = False
        if self.close_window_button is not None:
            self.close_window_button.set_text("-")  # override
        self.id = str(ident)
        self.image_was_sent = False
        self.icon_btn = None

    def show(self):
        """Start rendering entity and it's parts. During game called by clicking on icon button (minimized entity)"""
        super().show()
        self.icon_btn.kill()

    def process_event(self, event: pg.event.Event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_DOUBLE_CLICKED and event.ui_element == self.title_bar:
            self.entity_list.show()

    def on_close_window_button_pressed(self):
        self.hide()
        self.icon_btn = UIButton(relative_rect=self.close_window_button.rect,
                                 object_id=ObjectID(class_id="entity", object_id="#entity_icon_button"),
                                 manager=self.ui_manager, visible=True, command=self.show, text="")


class EntityList(UIWindow):  # THIS IS HOST VERSION!
    def __init__(self, owner: Entity, scene_ui_manager, text=None):
        super().__init__(rect=pg.Rect(0, 0, config.width // 3, config.height // 2),
                         window_display_title=f'{owner.title_bar.text} character list',
                         object_id="#character_list", visible=False, resizable=False, manager=scene_ui_manager)
        self.close_window_button.set_text("×")
        w = self.get_container().get_rect().width
        h = self.get_container().get_rect().height
        title_h = self.title_bar.relative_rect.height
        self.textbox = UITextBox(relative_rect=pg.Rect(0, 0, w, h - title_h - 20),
                                 container=self,
                                 html_text="This entity's list isn't uploaded yet." if text is None else text,
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
        if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_element == self.upload_btn:
            self.list_file_dialog = UIFileDialog(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                                                 window_title='Choose file',
                                                 initial_file_path=config.entity_lists_path,
                                                 allow_picking_directories=False,
                                                 allow_existing_files_only=True,
                                                 allowed_suffixes={""}, manager=self.ui_manager)
            self.list_file_dialog.refresh_button.kill()
            self.list_file_dialog.delete_button.kill()
            self.list_file_dialog.parent_directory_button.kill()
            self.list_file_dialog.home_button.kill()
            self.upload_btn.disable()

        if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_element == self.delete_btn:
            pg.event.post(pg.event.Event(ENTITY_DELETED, {'id': self.owner_entity.id}))
            self.owner_entity.kill()
            self.kill()

        if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
            if event.ui_element == self.list_file_dialog:
                try:
                    # noinspection PyUnresolvedReferences
                    resource_path = pg_gui.core.utility.create_resource_path(event.text)
                    text = Path(resource_path).read_text()
                    self.textbox.set_text(text)
                except pg.error:
                    print("Error while uploading char list, path = ", event.text)
                else:
                    self.owner_entity.changed_list = True

        if event.type == pg_gui.UI_WINDOW_CLOSE and event.ui_element == self.list_file_dialog:
            self.upload_btn.enable()
            self.list_file_dialog = None

    def on_close_window_button_pressed(self):
        self.hide()


class HostBoard:

    def __init__(self):

        global NET_RECEIVED_UPDATE
        NET_RECEIVED_UPDATE = pg.event.custom_type()
        global ENTITY_DELETED
        ENTITY_DELETED = pg.event.custom_type()
        self.players = []
        self.new_scene = None
        self.put_channel, self.get_channel = trio.open_memory_channel(max_buffer_size=100)
        self.connection_counter = count()
        self.sprites_counter = count()
        self.width = config.width
        self.height = config.height
        self.screen = pg.display.set_mode((self.width, self.height), pg.FULLSCREEN if config.fullscreen else 0)
        pg.display.set_caption("D&D Companion")
        self.map_surface = pg.Surface((self.width, self.height - self.height / 4))
        self.changed_map = False
        self.map = pg.image.load('resources/__logo.png')
        self.old_map = None
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
        self.send_btn = UIButton(relative_rect=pg.Rect(10, 20 + (self.ui.relative_rect.height - 30) // 2,
                                                       (self.ui.relative_rect.width - 50) // 8,
                                                       (self.ui.relative_rect.height - 30) // 2), text='Send map',
                                 manager=self.manager, container=self.ui)
        self.save_btn = UIButton(relative_rect=pg.Rect(10 + (self.ui.relative_rect.width - 50) // 8, 10,
                                                       (self.ui.relative_rect.width - 50) // 8,
                                                       (self.ui.relative_rect.height - 30) // 2), text='Save game',
                                 manager=self.manager, container=self.ui)
        self.load_save_btn = UIButton(relative_rect=pg.Rect(10, 10, (self.ui.relative_rect.width - 50) // 8,
                                                            (self.ui.relative_rect.height - 30) // 2), text='Load game',
                                      manager=self.manager, container=self.ui)

        self.roll_btn = UIButton(relative_rect=pg.Rect(
            (10 + (self.ui.relative_rect.width - 50) // 8, (self.ui.relative_rect.height - 30) // 2 + 20), (
                (self.ui.relative_rect.width - 50) // 16 + 5, (self.ui.relative_rect.height - 30) // 2)), text='ROLL',
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
        self.exit_btn = UIButton(relative_rect=pg.Rect(self.width - (self.ui.relative_rect.width - 50) // 4 - 10,
                                                       (self.ui.relative_rect.height - 30) // 2 + 20,
                                                       (self.ui.relative_rect.width - 50) // 4,
                                                       (self.ui.relative_rect.height - 30) // 2), text="LEAVE GAME",
                                 manager=self.manager, container=self.ui)
        self.game_log.set_active_effect(pg_gui.TEXT_EFFECT_FADE_IN)
        self.map_entities = []
        self.deleted_entities = []
        self.send_channel, self.receive_channel = trio.open_memory_channel(max_buffer_size=config.max_buffer_size)
        self.map_file_dialog = None
        self.sprite_file_dialog = None
        self.save_file_dialog = None
        self.load_file_dialog = None
        self.player_entities = []

    async def initialize_player(self, server_stream):
        ident = next(self.connection_counter)
        print(f"Connection {ident} opened")
        try:
            player = PlayerData(ident)
            self.players.append(player)
            map_to_send = self.map
            init_packet = json.dumps({'update': 'init', 'id': player.id}).encode()
            init_packet_size = len(init_packet).to_bytes(4, byteorder='big')
            player.send_channel.send_nowait(init_packet_size)
            player.send_channel.send_nowait(init_packet)
            if self.changed_map:
                map_to_send = self.old_map  # if player left and reconnected before host sent new map
            image_bytes = pg.image.tobytes(map_to_send, format="RGBA")
            map_packet = {'update': 'map', 'string': image_bytes.decode(encoding='latin1'),
                          'width': map_to_send.get_width(),
                          'height': map_to_send.get_height()}
            map_packet = json.dumps(map_packet).encode()
            map_packet_size = len(map_packet).to_bytes(4, byteorder='big')
            try:
                player.send_channel.send_nowait(map_packet_size)
                player.send_channel.send_nowait(map_packet)
            except trio.WouldBlock:
                self.game_log.append_html_text(f"Can't sync with new player")  # can't happen with new empty buffer

            for entity in self.map_entities:
                if entity.image_was_sent:
                    x, y = self.get_cords_ratio(entity)
                    surface = entity.portrait.image
                    image_bytes = pg.image.tobytes(surface, format="RGBA")
                    entity_packet = {'update': 'new_entity', 'string': image_bytes.decode(encoding='latin1'),
                                     'width': surface.get_width(), 'height': surface.get_height(), 'ratio_x': x,
                                     'ratio_y': y, 'id': entity.id, 'name': entity.name}
                    entity_packet = json.dumps(entity_packet).encode()
                    entity_packet_size = len(entity_packet).to_bytes(4, byteorder='big')
                    try:
                        player.send_channel.send_nowait(entity_packet_size)
                        player.send_channel.send_nowait(entity_packet)
                    except trio.WouldBlock:  # may happen if you have config.max_buffer_size unsent packets
                        self.game_log.append_html_text(f"Can't send updates to new player")
            for old_player in self.player_entities:
                player_packet = old_player.dump()
                player_packet['update'] = 'new_player'
                player_packet['id'] = old_player.id
                player_packet = json.dumps(player_packet).encode()
                try:
                    player.send_channel.send_nowait(len(player_packet).to_bytes(4, byteorder='big'))
                    player.send_channel.send_nowait(player_packet)
                except trio.WouldBlock:  # may happen if you have config.max_buffer_size unsent packets
                    self.game_log.append_html_text(f"Can't send updates to new player")
            async with trio.open_nursery() as nursery:
                nursery.start_soon(self.listener, server_stream, nursery.cancel_scope, ident)
                nursery.start_soon(self.sender, server_stream, player.receive_channel, nursery.cancel_scope)
        except Exception as exc:
            print(f"player listener {ident}: crashed: {exc}")
        finally:
            self.remove_player(str(ident))

    def remove_player(self, removed_id):
        for p in self.players:
            if p.id == removed_id:
                packet = {'update': 'player_left', 'id': p.id, 'name': p.name}
                self.game_log.append_html_text(
                    f'<p><strong>{p.name}</strong> left the game.</p>')
                self.players.remove(p)
                # delete from bottom panel
                self.send_packet(packet)
                break
        for p in self.player_entities:
            if p.id == removed_id:
                p.kill()
                self.player_entities.remove(p)
                return

    async def listener(self, server_stream, cancel_scope, ident):
        try:
            bytebuffer = bytearray()
            print(f'Listener {ident} started')
            async for data in server_stream:
                bytebuffer.extend(data)
                if len(bytebuffer) >= 4:
                    packet_size = int.from_bytes(bytebuffer[:4], byteorder='big')
                    if len(bytebuffer) >= 4 + packet_size:
                        packet = json.loads((bytebuffer[4:4 + packet_size]).decode())
                        del bytebuffer[0:4 + packet_size]
                        packet['id'] = str(ident)
                        event = pg.event.Event(NET_RECEIVED_UPDATE, packet)
                        pg.event.post(event)
                        await trio.sleep(0)
            cancel_scope.cancel()
        except Exception as e:
            print(f'Listener {ident} crashed: {e}')

    async def sender(self, server_stream, game_stream, cancel_scope):
        async for data in game_stream:
            try:
                await server_stream.send_all(data)
            except trio.BrokenResourceError:
                break
            await trio.sleep(0)
        cancel_scope.cancel()

    async def run(self):
        async with trio.open_nursery() as nursery:
            print("Starting mainloop..\n")
            nursery.start_soon(self.main_loop, nursery.cancel_scope)
            nursery.start_soon(trio.serve_tcp, self.initialize_player, config.port)

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
                self.running = False
                pg.quit()
                sys.exit()
            if event.type == ENTITY_DELETED:
                deleted_entity_id = str(event.__dict__['id'])
                for entity in self.map_entities:
                    if entity.id == deleted_entity_id:
                        self.map_entities.remove(entity)
                        self.deleted_entities.append(deleted_entity_id)
            if event.type == pg_gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.exit_btn:
                    self.new_scene = "Launcher"
                if event.ui_element == self.load_save_btn:
                    self.load_file_dialog = UIFileDialog(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                                                         self.manager,
                                                         window_title='Choose savefile to load',
                                                         initial_file_path=config.saves_path,
                                                         allow_picking_directories=False,
                                                         allow_existing_files_only=True,
                                                         allowed_suffixes={""})
                    self.load_save_btn.disable()
                if event.ui_element == self.save_btn:
                    self.save_file_dialog = SaveFileDialog(text="Choose file to save game to", init_path="saves/",
                                                           scene_ui_manager=self.manager)
                    self.save_btn.disable()

                if event.ui_element == self.load_btn:
                    self.sprite_file_dialog = UIFileDialog(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                                                           self.manager,
                                                           window_title='Upload entity',
                                                           initial_file_path=config.images_path,
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
                    self.roll_dice("Master", self.dice_btn.selected_option[0][1:])

                if event.ui_element == self.send_btn:
                    if self.changed_map:
                        self.send_map()
                        self.changed_map = False
                    for deleted_entity_id in self.deleted_entities:
                        packet = {'update': 'delete_entity', 'id': deleted_entity_id}
                        self.send_packet(packet)
                        self.deleted_entities.remove(deleted_entity_id)
                    cords_packet = {'update': 'cords', 'entity:topright': {}}
                    updated_cords = []
                    for entity in self.map_entities:
                        x, y = self.get_cords_ratio(entity)
                        if entity.image_was_sent:
                            updated_cords.append((entity.id, (x, y)))
                            if entity.changed_list:
                                packet = {'update': 'entity_list', 'list': entity.entity_list.textbox.html_text,
                                          'id': entity.id}
                                self.send_packet(packet)
                                entity.changed_list = False
                        else:
                            surface = entity.portrait.image
                            image_bytes = pg.image.tobytes(surface, format="RGBA")
                            entity_packet = {'update': 'new_entity', 'string': image_bytes.decode(encoding='latin1'),
                                             'width': surface.get_width(), 'height': surface.get_height(), 'ratio_x': x,
                                             'ratio_y': y, 'id': entity.id, 'name': entity.name}
                            self.send_packet(entity_packet)
                            entity.image_was_sent = True
                    cords_packet['entity:topright'].update(updated_cords)
                    self.send_packet(cords_packet)
                    updated_cords = []
                    for player in self.player_entities:
                        updated_cords.append((player.id, self.get_cords_ratio(player)))
                        if player.char_sheet.changed:
                            packet = {'update': 'player_sheet', 'id': player.id,
                                      'list': player.char_sheet.dump_to_list()}
                            player.char_sheet.changed = False
                            self.send_packet(packet)
                    cords_packet = {'update': 'player_cords', 'entity:topright': {}}
                    cords_packet['entity:topright'].update(updated_cords)
                    self.send_packet(cords_packet)
            if event.type == pg_gui.UI_FILE_DIALOG_PATH_PICKED:
                if event.ui_element == self.save_file_dialog:
                    savefile = SaveFile(ident=self.sprites_counter)
                    for entity in self.map_entities:
                        image = entity.portrait.image
                        savefile.entities_data.append(
                            (pg.image.tobytes(image, format="RGBA"), (image.get_width(), image.get_height()),
                             self.get_cords_ratio(entity),
                             entity.entity_list.textbox.html_text, entity.id, entity.name))
                    savefile.map = pg.image.tobytes(self.map, format="RGBA")
                    savefile.map_size = self.map.get_size()
                    with open(event.text, 'wb') as file:
                        pickle.dump(savefile, file)
                    self.game_log.append_html_text("Game was successfully saved!<br/>")
                if event.ui_element == self.load_file_dialog:
                    for entity in self.map_entities:
                        entity.kill()
                    self.map_entities.clear()
                    self.deleted_entities.clear()
                    self.game_log.clear()
                    with open(event.text, 'rb') as file:
                        savefile = pickle.load(file)
                    self.map = pg.image.frombytes(savefile.map, savefile.map_size, format="RGBA")
                    self.sprites_counter = savefile.ident
                    for data_tuple in savefile.entities_data:
                        try:
                            cords = self.get_cords_from_ratio(*data_tuple[2])
                            self.map_entities.append(
                                Entity(scene_ui_manager=self.manager, bytes_image=data_tuple[0], size=data_tuple[1],
                                       topright=cords, list_text=data_tuple[3], ident=data_tuple[4],
                                       name=data_tuple[5]))
                        except pg.error as e:
                            print(f"Error while loading saved entity, {e}")
                    self.game_log.append_html_text("Game loaded successfully.<br/>")
                    self.send_packet({'update': 'load_game'})

                if event.ui_element == self.map_file_dialog:
                    try:
                        self.old_map = map
                        self.map = img_path_to_surface(event.text, self.map_surface_rect.w, self.map_surface_rect.h)
                        self.changed_map = True
                    except pg.error:
                        print("Error while changing map, path = ", event.text)
                        self.map = self.old_map
                if event.ui_element == self.sprite_file_dialog:
                    try:
                        name = Path(event.text).stem
                        self.map_entities.append(
                            Entity(image_path=event.text, scene_ui_manager=self.manager,
                                   ident=next(self.sprites_counter), name=name))
                    except pg.error as error:
                        print(f'Error while creating entity: {error}')

            if event.type == pg_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.map_file_dialog:
                    self.map_btn.enable()
                    self.map_file_dialog = None
                if event.ui_element == self.sprite_file_dialog:
                    self.load_btn.enable()
                    self.sprite_file_dialog = None
                if event.ui_element == self.save_file_dialog:
                    self.save_btn.enable()
                    self.save_file_dialog = None
                if event.ui_element == self.load_file_dialog:
                    self.load_save_btn.enable()
                    self.load_file_dialog = None

            if event.type == NET_RECEIVED_UPDATE:
                d = event.__dict__
                if d['update'] == 'roll':
                    self.roll_dice(d['name'], d['dice'])
                if d['update'] == 'new_player':
                    self.player_entities.append(
                        PlayerEntity(manager=self.manager, character_data=event.__dict__, ident=d['id']))
                    for p in self.players:
                        if p.id == str(d['id']):
                            p.name = d['name']
                            break
                    self.send_packet(d)

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
        image_bytes = pg.image.tobytes(self.map, format="RGBA")
        packet = {'update': 'map', 'string': image_bytes.decode(encoding='latin1'), 'width': self.map.get_width(),
                  'height': self.map.get_height()}
        self.send_packet(packet)
        self.changed_map = False

    def send_packet(self, unencoded_packet):
        packet = json.dumps(unencoded_packet).encode()
        packet_size = len(packet).to_bytes(4, byteorder='big')
        try:
            for player in self.players:
                player.send_channel.send_nowait(packet_size)
                player.send_channel.send_nowait(packet)
        except trio.WouldBlock:  # may happen if you have config.max_buffer_size unsent packets
            self.game_log.append_html_text(f"Can't send update to players, try again.")
            return

    def get_cords_ratio(self, entity: Entity):
        abs_x, abs_y = entity.close_window_button.rect.topright
        if self.map.get_size() != (0, 0):
            delta_x, delta_y = self.map.get_rect().topleft
            ratio_x = (abs_x - delta_x) / self.map.get_rect().width
            ratio_y = (abs_y - delta_y) / self.map.get_rect().height
        else:
            ratio_x = abs_x / self.width
            ratio_y = abs_y / self.height
        return ratio_x, ratio_y

    def write_save(self):
        savefile = SaveFile(ident=self.sprites_counter)
        for entity in self.map_entities:
            savefile.entities_data.append(
                (entity.portrait.image, self.get_cords_ratio(entity), entity.entity_list.textbox.html_text))
        savefile.map = self.map

    def get_cords_from_ratio(self, ratio_x, ratio_y):
        delta_x, delta_y = self.map.get_rect().topleft
        x = delta_x + self.map.get_rect().width * ratio_x
        y = delta_y + self.map.get_rect().height * ratio_y
        return x, y


class SaveFile:
    def __init__(self, ident):
        # can use pickle because saves are local for host
        # json for over-tcp packages
        self.entities_data = []
        self.ident = ident
        self.map = pg.Surface((10, 10))
        self.map_size = (0, 0)


class PlayerData:
    def __init__(self, ident):
        self.id = str(ident)
        self.name = 'clientName'
        self.send_channel, self.receive_channel = trio.open_memory_channel(max_buffer_size=config.max_buffer_size)


class SaveFileDialog(UIFileDialog):
    def __init__(self, text, init_path, scene_ui_manager):
        super().__init__(pg.Rect(0, 0, config.width // 3, (config.height * 2) // 3),
                         window_title=text,
                         initial_file_path=init_path,
                         allow_picking_directories=False,
                         allow_existing_files_only=True,
                         allowed_suffixes={""}, object_id="#save_dialog", manager=scene_ui_manager)
        self.refresh_button.kill()
        self.delete_button.kill()
        self.parent_directory_button.kill()
        self.home_button.kill()
        self.create_btn = UIButton(relative_rect=pg.Rect(10, 10, -1, 30), text="Or create new save with name:",
                                   container=self, manager=scene_ui_manager)
        self.new_save_text_line = UITextEntryLine(
            relative_rect=pg.Rect(self.create_btn.relative_rect.right, 10,
                                  self.file_path_text_line.rect.width - self.create_btn.relative_rect.width, 30),
            container=self,
            initial_text="",
            object_id="#save_textline", manager=scene_ui_manager)

    def process_event(self, event):
        super().process_event(event)
        if event.type == pg_gui.UI_BUTTON_PRESSED and event.ui_element == self.create_btn:
            filename = self.new_save_text_line.get_text()
            if not filename:
                return
            filename = Path(self.current_directory_path) / filename
            try:
                # noinspection PyUnusedLocal
                savefile = open(filename, 'w')
                # create savefile for future character
            except OSError:
                print(f'Error while creating savefile with name {filename}')
                return
            self.update_current_file_list()
            self.file_selection_list.set_item_list(self.current_file_list)


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
        self.map_prompt_text_line = UITextEntryLine(
            relative_rect=pg.Rect(10, 40, self.get_container().get_size()[0] - 20, -1), container=self,
            initial_text="",
            object_id="#prompt_textline", manager=scene_ui_manager)
        self.map_prompt_text_line.hide()
        self.gen_btn = UIButton(relative_rect=pg.Rect(10, 10, -1, 30), text="Generate by description",
                                container=self, manager=scene_ui_manager)
        self.gen_btn.disable()

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
