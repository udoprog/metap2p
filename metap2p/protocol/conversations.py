from metap2p.session import Conversation
from metap2p.protocol import frames

class ClientRegister(Conversation):
  id = 0x0020
  send_to = 0x0010
  
  def conversationStarted(self):
    self.debug("ClientRegister")
    self.send(frames.Handshake(uuid=self.session.server.uuid.hex))
    self.recv(frames.HandshakeResponse, self.recv_response)

  def recv_response(self, frame):
    if frame.ack:
      self.debug("Received handshake ACK")
      self.session.uuid = frame.uuid
      self.session.registered = True
      self.end()
    else:
      self.debug("Removing peer since handshake was denied")
      self.session.server.peers.remove(self.session.peer)
      self.lose()

class ServerRegister(Conversation):
  id = 0x0010
  send_to = 0x0020
  
  def conversationStarted(self):
    self.debug("ServerRegister")
    self.recv(frames.Handshake, self.recv_handshake)
  
  def recv_handshake(self, frame):
    self.debug("Received Handshake")

    if self.session.server.uuid.hex == frame.uuid and False:
      self.debug("Refusing to speek to self")
      self.send(frames.HandshakeResponse(uuid=frame.uuid, ack=False))
      return self.lose()
    
    self.session.uuid = frame.uuid
    self.session.registered = True
    self.send(frames.HandshakeResponse(uuid=frame.uuid, ack=True))
    self.end()

class ServerInit(Conversation):
  # 0x0 id will receive all messages
  id = 0x0
  send_to = None
  
  def conversationStarted(self):
    self.debug("ServerSpawn")
    self.recv(frames.Spawn, self.recv_spawn)
  
  def recv_spawn(self, frame):
    self.debug("spawn:", frame.conv)
    self.session.spawn(frame.conv)
    self.end()

class Ping(Conversation):
  id = 0x7777
  send_to = 0x8888
  
  def conversationStarted(self):
    self.debug("Ping")
    self.send(frames.Spawn(conv="pong"))
    self.send(frames.Ping())
    self.recv(frames.Pong, self.recv_pong)
  
  def recv_pong(self, frame):
    self.end()

class Pong(Conversation):
  id = 0x8888
  send_to = 0x7777

  def conversationStarted(self):
    self.debug("Pong")
    self.recv(frames.Ping, self.recv_ping)

  def recv_ping(self, frame):
    self.send(frames.Pong())
    self.end()
