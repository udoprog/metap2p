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
from metap2p.protocol import conversations
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
  
  server = Server(ServerSession, ClientSession, **settings)
  
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
  conversations = {
    # Authenticates peer in order to connect.
    # Sets uuid for peer (during Handshake)
    #
    # Looses connection if:
    #   Peer is self (also removes connection from list of persistent if existing)
    #
    'cl_register': conversations.ClientRegister,
    'sv_register': conversations.ServerRegister,
    'sv_init': conversations.ServerInit,
    'cl_ping': conversations.Ping
  }
  
  multiplex = False
  headerframe = frames.Header
  
  """
  TestSession is a multiplexer, therefore it needs to know who the information is meant for.
  """
  def getFrameSentTo(self, headerframe):
    return headerframe.send_to
  
  def getFrameSentFrom(self, headerframe):
    return headerframe.send_from
  
  def getFrameSize(self, headerframe):
    return headerframe.size
  
  def validateFrame(self, headerframe):
    return headerframe.valid();
  
  def loseConnection(self):
    self.peer.connector.loseConnection();
    pass
  
  def connectionMade(self):
    pass
    #self.peer.debug("Session started");
  
  def prepareFrame(self, conv, frame):
    frame.send_from = conv.id
    frame.send_to = conv.send_to
  
  def sendMessage(self, data):
    self.peer.connector.write(data);

class ServerSession(PeerSession):
  def sessionInit(self):
    self.registered = False
    self.uuid = None
  
  def connectionMade(self):
    self.debug("SERVER Connection Made")
    
    if not self.registered:
      return self.spawn('sv_register')
    else:
      return self.spawn('sv_init')

class ClientSession(PeerSession):
  def sessionInit(self):
    self.registered = False
    self.uuid = None
  
  def connectionMade(self):
    self.debug("CLIENT Connection Made")
    
    if not self.registered:
      return self.spawn('cl_register')
