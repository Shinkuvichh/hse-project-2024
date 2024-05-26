from pathlib import Path
from random import randint
import pygame as pg
import pygame_gui as pg_gui
from pygame_gui import UIManager
from pygame_gui.core.utility import create_resource_path
from pygame_gui.elements import UIButton, UIWindow, UIImage, UIPanel, UIDropDownMenu, UITextBox, UITextEntryLine
from pygame_gui.windows import UIFileDialog
import config
import sys
import trio


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
