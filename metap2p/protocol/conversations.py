from metap2p.session import Conversation
from metap2p.protocol import frames

class Handshake(Conversation):
  def conversationStarted(self):
    self.debug("Handshake")
    self.send(frames.Handshake(uuid=self.session.server.uuid.hex))
  
  def recv_and_respond(self, frames):
    self.debug("Received Handshake")
