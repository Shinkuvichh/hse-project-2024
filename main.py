import pygame as pg
import trio

from launcher import Launcher

if __name__ == "__main__":
    pg.init()
    character_data = None
    Scene = Launcher()
    Scene.run()
    while True:
        if Scene.new_scene == "Launcher":
            Scene = Launcher()
            Scene.run()
        if Scene.new_scene == "Host":
            from HostBoard import HostBoard
            Scene = HostBoard()
            trio.run(Scene.run)
        if Scene.new_scene == "Client":
            character_data = Scene.character_data
            from ClientBoard import ClientBoard
            Scene = ClientBoard(character_data)
            trio.run(Scene.run)
        if Scene.new_scene == "Editor":
            from Editor import Editor
            Scene = Editor()
            Scene.run()
