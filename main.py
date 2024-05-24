import trio
from launcher import Launcher

if __name__ == "__main__":
    Scene = Launcher()
    Scene.run()
    if Scene.new_scene == "Host":
        from HostBoard import HostBoard

        Scene = HostBoard()
        trio.run(Scene.run)
    if Scene.new_scene == "Client":
        from ClientBoard import ClientBoard

        Scene = ClientBoard()
        trio.run(Scene.run)
