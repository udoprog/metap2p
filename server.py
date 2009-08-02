#from metap2p.factory import ServerFactory
from metap2p.session import Session, Conversation
import metap2p.protocol.frames as frames
from metap2p.factory import Server
from metap2p.modules import require_dep

import sys
import os
import time
import md5

if not require_dep('yaml'):
  print "Unable to import PyYAML"
  print "  please install it somewhere!"
  sys.exit(99)
else:
  import yaml

program_name = sys.argv[0]

settings = {
  'config': ['/etc/metap2p.conf', '~/.metap2p', './conf/metap2p.conf'],
  'peers': [],
  'defaultport': 8042,
  'listen': {
    'host': '0.0.0.0',
    'port': 8040
  },
  'passive': True
}

def main(argv):
  global settings
  
  import getopt

  try:
    arguments, args = getopt.gnu_getopt(argv, "c:p:l:")
  except getopt.GetoptError, e:
    print e
    return 1

  for argument, value in arguments:
    if argument == "-c":
      settings['config'].insert(0, value)
      continue

  config_f = None
  
  for conf in settings['config']:
    if os.path.isfile(conf):
      config_f = open(conf, 'r')
      break
  
  if config_f is None:
    print "Could not read configuration"
    return 1
  
  settings.update(yaml.load(config_f))
  
  for argument, value in arguments:
    if argument == "-p":
      settings['defaultport'] = int(value)
      continue

    if argument == "-l":
      if ':' in value:
        host, port = value.split(':')
        port = port.strip()

        settings['listen']['host'] = host.strip();
        
        if port.isdigit():
          settings['listen']['port'] = int(port.strip())
        
        settings['passive'] = False
      else:
        settings['listen']['host'] = value.strip()
        settings['passive'] = False
      continue
  
  server = Server(PeerSession, **settings)
  
  if type(settings['peers']) is str:
    peer_f = open(settings['peers'], 'r')
    settings['peers'] = list()
    for line in peer_f:
      settings['peers'].append(line.strip())
  
  for peer in settings['peers']:
    if ':' in peer:
      host, port = peer.split(':')
      host = host.strip()
      port = int(port.strip())
    else:
      host = peer.strip()
      port = settings['defaultport']
    
    server.addPeer(host, port)
  
  server.run()
  return 0

class MetaP2P:
  class Stage:
    """
    Just a list of the different stages in order to sanity check messages...
    Gotta find out a more sane way to do these.
    Also; uniqueness is all that counts. Not that they can be packed into the same variable : P.
    """
    Handshake = 0x0001
    Handshake_Ack = 0x0002
    
    Ping = 0x1000
    Pong = 0x2000
    
    """
    Request a discover session.
    """
    Discover_Req = 0x0100
    
    """
    Acknowledge the request of a discover session.
    """
    Discover_Ack = 0x0200

def expect_header(expected_stage):
  """
  Used to decorate Session methods in order to expect a certain header type
  """
  def retfunc(func):
    def wrapper(self, frame):
      if frame.stage is not expected_stage:
        self.debug("BAD HEADER, unexpected stage")
        if self.session.peer.persistent:
          self.debug("Connection is persistent, will be removed")
          self.session.peer.server.peers.remove(self.session.peer)
        
        return False
      
      return func(self, frame)
    #wrapper
    return wrapper
  #override function
  return retfunc

class DiscoverConversation(Conversation):
  def conversationStarted(self):
    import copy

    self.recv_done = False
    self.send_done = False
    
    self.debug("DiscoverConversation")

    self.peers = copy.copy(self.session.peer.server.peers)
    
    self.period(10, self.send_discover)
    self.recv(frames.Discover, self.recv_discover)

  def send_discover(self, frame):
    print "I WANT TO SEND", len(self.peers), "PEERS"
    peer = self.peers.pop()
    return switch('base')
  
  def recv_discover(self, frame):
    if not frame.hasnext:
      return self.recv_done()
    return True

  def recv_done(self):
    self.recv_done = True
    
    if self.recv_done and self.send_done:
      return self.switch('base')

  def send_done(self):
    self.send_done = True
    
    if self.recv_done and self.send_done:
      return self.switch('base')

class BaseConversation(Conversation):
  def conversationStarted(self):
    self.debug("BaseConversation")
    self.recv(frames.Header, self.recv_header)
    self.period(10, self.send_ping)
    self.period(10, self.send_discover, now=False)
  
  def send_ping(self):
    self.debug("Sent a ping to")
    self.send(frames.Header(stage=MetaP2P.Stage.Ping))
  
  def recv_header(self, frame):
    if frame.stage == MetaP2P.Stage.Ping:
      self.debug("Got a ping from, sent a response to")
      #set it up for another receive later...
      self.recv(frames.Header, self.recv_header)
      return self.send(frames.Header(stage=MetaP2P.Stage.Pong))
    
    if frame.stage == MetaP2P.Stage.Pong:
      self.debug("Got a ping response from")
      #set it up for another receive later...
      return self.recv(frames.Header, self.recv_header)
    
    return False
  
  def send_discover(self):
    return self.switch('discover')

class AuthConversation(Conversation):
  def conversationStarted(self):
    self.debug("AuthConversation")
    
    self.got_handshake = False
    
    sendframe = frames.Handshake(stage=MetaP2P.Stage.Handshake, uuid=self.session.peer.server.uuid.hex) 
    sendframe.generate_digest()
    # just to make sure where we get our information.
    self.send(sendframe)
    
    #self.handshake(1, "dsd")
    # to recv the initial handshake
    return self.recv(frames.Handshake, self.handshake)
  
  @expect_header(MetaP2P.Stage.Handshake)
  def handshake(self, frame):
    #
    # Are we communicating with someone who has the same uuid as me?
    #
    if self.session.peer.server.uuid.hex == frame.uuid:
      self.debug("BAD Handshake, will not talk to self!")
      
      if self.session.peer.persistent:
        self.debug("Connection is persistent, will be removed")
        self.session.peer.server.peers.remove(self.session.peer)
      else:
        self.debug("Connection is volatile, no need to remove")
      
      return False
    
    #
    # Does the message digest work out?
    #
    if not frame.validate_digest():
      self.debug("BAD Handshake, integrity check fails!")
      return False
    #if uuid in self.session.server.connections:
    #  return False
    
    self.debug("OK Handshake")
    
    self.session.uuid = frame.uuid
    self.got_handshake = True

    sendframe = frames.Handshake_Ack(stage=MetaP2P.Stage.Handshake_Ack, uuid=self.session.uuid)
    sendframe.generate_digest()
    self.send(sendframe)

    #test = frames.Handshake_Ack()
    #test._feed_(sendframe._digest_())
    #raise repr(test.stage)
    
    # to recv the handshake ACK
    return self.recv(frames.Handshake_Ack, self.handshake_ack)
  
  @expect_header(MetaP2P.Stage.Handshake_Ack)
  def handshake_ack(self, frame):
    if not self.got_handshake:
      self.debug("BAD Handshake_Ack, no Handshake sent");
      return False
    
    if frame.uuid != self.session.peer.server.uuid.hex:
      self.debug("BAD Handshake_Ack, uuid mismatch");
      return False
    
    if not frame.validate_digest():
      self.debug("BAD Handshake_Ack, integrity check fails!")
      return False
    
    self.debug("OK Handshake ACK")
    #switch conversation
    return self.switch('base')

  def conversationEnded(self):
    pass

class PeerSession(Session):
  """
  The different available conversations.
  Use Conversation#switch inside a conversation in order to switch.
  """
  conversations = {
    # Authenticates peer in order to connect.
    # Sets uuid for peer (during Handshake)
    #
    # Looses connection if:
    #   Peer is self (also removes connection from list of persistent if existing)
    #
    'auth': AuthConversation,
    # Set's a periodical caller to ping all connected peers
    'base': BaseConversation,
    'discover': DiscoverConversation
  }
  
  default = 'auth'
  
  def connectionMade(self):
    pass
    #self.peer.debug("Session started");
  
  def write(self, data):
    self.peer.connector.write(data);

if __name__ == "__main__":
  import sys
  sys.exit(main(sys.argv[1:]))
