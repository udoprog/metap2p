# -*- encoding: utf-8 -*-
#
# When this has been included, assume all is OK
#

from metap2p.modules import require_all

depend = dict()

depend['yaml'] = dict()
depend['yaml']['checks'] = dict(gte='3.08')
depend['yaml']['message'] = ( "Unable to import PyYAML\n" + 
                              "  please install it from:\n" + 
                              "  http://pyyaml.org/wiki/PyYAML\n"
                              "  or use: easy_install PyYAML")

#depend['ipaddr'] = dict()
#depend['ipaddr']['checks'] =  dict(gte='1.1.1')
#depend['ipaddr']['message'] = ("Unable to import ipaddr-py\n" +
#                              "  please install it from:\n" +
#                              "  http://code.google.com/p/ipaddr-py/\n" +
#                              "\n" +
#                              "  If you have a source release of this project, the\n" +
#                              "  recommended version of ipaddr-py should be present\n" +
#                              "  in ./3rdparty")
    
depend['twisted'] = dict()
depend['twisted']['checks'] =   dict(gte='8.2.0')
depend['twisted']['message'] =  ("Unable to import Twisted\n" +
                                "  please install it from:\n" +
                                "  http://twistedmatrix.com\n" + 
                                "  or use: easy_install twisted")

depend['routes'] = dict()
#depend['routes']['checks'] =   dict(gte='100.0')
depend['routes']['message'] =  ("Unable to import Python Routes\n" +
                                "  please install it from somewhere!" + 
                                "  it's needed for local webservice!" +
                                "  use: easy_install routes")

import os, sys

if not require_all(depend):
  print ""
  print "!!! One or more library dependancy was not met, please install them !!!"
  sys.exit(99)

import yaml

from metap2p.server   import Server
#from metap2p.protocol import conversations
from metap2p.protocol import frames
from metap2p.session  import Session

program_name = sys.argv[0]

root = "/"
pwd = os.path.dirname(os.path.abspath(__file__))

settings = {
  'peers': [],
  'default_port': 8040,
  'listen_host': '0.0.0.0',
  'listen_port': 8040,
  
  'passive': True,

  'service': False,
  'service_host': "0.0.0.0",
  'service_port': 9042,
  'service_path': 'metap2p_app',
  'service_public': 'public',
  'service_protocol': 'http',
  'base_dir': None,
  'reload': True
}
  
import getopt

def initenv(metap2p_root, config=None):
  global settings
  
  if not config:
    raise Exception("Cannot Continue without Configuration")
  
  config_path = os.path.join(config, "metap2p.conf")
  
  if not os.path.isfile(config_path):
    raise Exception("Configuration does not exist; %s"%(config_path))
  
  config_f = open(config_path, 'r')
  
  try:
    settings.update(yaml.load(config_f))
  finally:
    config_f.close()
  
  if not settings['base_dir']:
    print "!!! No base_dir in configuration, assuming base_dir =", metap2p_root
    settings['base_dir'] = metap2p_root
  
  server = Server(ClientSession, ClientSession, **settings)
  
  if type(settings['peers']) is str:
    peers_path = os.path.join(config, settings['peers'])
    peer_f = open(peers_path, 'r')
    
    try:
      settings['peers'] = list()
      for line in peer_f:
        settings['peers'].append(line.strip())
      peer_f.close()
    finally:
      peer_f.close()
  
  server.addPeers(settings['peers'])
  return server

class PeerSession(Session):
  """
  The different available conversations.
  Use Conversation#switch inside a conversation in order to switch.
  """
  headerframe = frames.Header
  
  """
  TestSession is a multiplexer, therefore it needs to know who the information is meant for.
  """

  def buildHeaderFrame(self, headerframe, frame):
    header = headerframe(size=frame._size(), type=frame.type)
    ## create digest for payload
    header.generatePayloadDigest(frame._pack())
    ## create digest for header only.
    #header.hdigest()
    return header._pack()
  
  def getFrameSize(self, headerframe):
    return headerframe._size()
  
  def getPayloadSize(self, headerframe):
    return headerframe.size
  
  def loseConnection(self):
    self.peer.connector.loseConnection();
    pass
  
  def prepareFrame(self, frame):
    pass
  
  def sendMessage(self, data):
    self.peer.connector.write(data);

#class ServerSession(PeerSession):
#  def sessionInit(self):
#    self.registered = False
#    self.uuid = None
#
#  def receiveFrame(self, header, frame):
#    self.debug("Received anonymous frame")
#
#  def connectionMade(self):
#    if not self.registered:
#      self.switch('handshake')
#      return
#    
#    self.debug("Registered")

class ClientSession(PeerSession):
  def sessionInit(self):
    self.registered = False
    self.uuid = None
  
  def validateHeader(self, headerframe):
    """
    This is just meta-validation.
    """
    if headerframe.magic != self.headerframe.magic:
      self.debug("Magic bytes suck")
      return False

    #if not headerframe.hvalidate():
    #  self.debug("Header digest does not validate")
    #  return False
    
    if self.registered:
      if headerframe.size <= headerframe.MAX_SIZE:
        return True
      else:
        self.debug("Frame to big for registered peer")
        return False
    else:
      if headerframe.size <= 2**8:
        return True
      else:
        self.debug("Frame to big for non-registered peer")
        return False
  
  def validatePayload(self, headerframe, data):
    return headerframe.validatePayloadDigest(data)
  
  def receiveFrame(self, header, data):
    if not self.registered:
      if header.type == frames.Handshake.type:
        frame = frames.Handshake()._unpack(data)

        if self.server.uuid.hex == frame.uuid and False:
          self.debug("Will not connect to self!")
          if self.peer.persistent:
            self.server.peers.remove(self.peer)
          return self.lose()
        
        self.registered = True
        self.uuid = frame.uuid
        self.debug("Registered peer as", repr(self.uuid))
        return

      self.debug("Losing connection since it has not been registered")
      return self.lose();
    
    if not self.registered:
      self.debug("Connection has not been registered yet, sorry dude, you have to die")
      return self.lose()

    if header.type == frames.MessageHead.type:
      self.debug("received a message head")
      frame = frames.MessageHead()._unpack(data)

      if frame.id in self.peer.queue:
        self.debug("Message already exists in queue")
        return self.lose()
      
      self.peer.queue[frame.id] = self.peer.recv_message(frame)
      return

    if header.type == frames.MessagePart.type:
      frame = frames.MessagePart()._unpack(data)

      if not frame.id in self.peer.queue:
        self.debug("Message does not exist in queue, losing connection")
        return self.lose()
      
      self.peer.queue[frame.id].feed(frame)
      return
    
    self.debug("Received anonymous frame")

  def connectionMade(self):
    # first thing you do when connecting, send uuid hex
    self.debug("Connection Made")
    self.send(frames.Handshake(uuid=self.server.uuid.hex))
