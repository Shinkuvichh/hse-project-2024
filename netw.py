from PodSixNet.Channel import Channel
from PodSixNet.Server import Server

class Player(Channel):
    def network(self, data): # called when client uses conn.Send
        print(data)
    #Network_myaction() #when called with action: myaction
class Master(Server):
    channelClass = Player
    def connected(self, channel, addr): # when user conns
        print("connected", channel)


