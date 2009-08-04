#from metap2p.factory import ServerFactory
from metap2p.modules import require_all
import sys

depend = dict()

depend['yaml'] = dict()
depend['yaml']['checks'] = dict(gte='3.08')
depend['yaml']['message'] = ( "Unable to import PyYAML\n" + 
                              "  please install it from:\n" + 
                              "  http://pyyaml.org/wiki/PyYAML\n"
                              "  or use: easy_install PyYAML")

depend['ipaddr'] = dict()
depend['ipaddr']['checks'] =  dict(gte='1.1.1')
depend['ipaddr']['message'] = ("Unable to import ipaddr-py\n" +
                              "  please install it from:\n" +
                              "  http://code.google.com/p/ipaddr-py/\n" +
                              "\n" +
                              "  If you have a source release of this project, the\n" +
                              "  recommended version of ipaddr-py should be present\n" +
                              "  in ./3rdparty")
    
depend['twisted'] = dict()
depend['twisted']['checks'] =   dict(gte='8.2.0')
depend['twisted']['message'] =  ("Unable to import Twisted\n" +
                                "  please install it from:\n" +
                                "  http://twistedmatrix.com\n" + 
                                "  or use: easy_install twisted")

depend['routes'] = dict()

if not require_all(depend):
  print ""
  print "!!! One or more library dependancy was not met, please install them !!!"
  sys.exit(99)

import yaml

from metap2p.session import Session, Conversation
from metap2p.server import Server
from metap2p.protocol import conversations
from metap2p import ipaddr_ext

import os
import time
import md5

program_name = sys.argv[0]

settings = {
  'config': ['/etc/metap2p.conf', '~/.metap2p', './conf/metap2p.conf'],
  'peers': [],
  'defaultport': 8040,
  'listen_host': '0.0.0.0',
  'listen_port': 8040,

  'passive': True,

  'service': False,
  'service_host': "0.0.0.0",
  'service_port': 9042,
  'servicepath': 'shared'
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
    
    if argument == "-s":
      settings['service'] = True
    
    if argument == "-l":
      ip = ipaddr_ext.IP(value.strip())
      
      if not ip:
        print "listen address invalid"
        return 1
      
      settings['listen_host'] = ip.ip_ext
      
      if ip.port:
        settings['listen_port'] = ip.port
      
      settings['passive'] = False
      
      continue
  
  root = os.path.dirname(os.path.abspath(__file__))
  server = Server(root, PeerSession, **settings)
  
  if type(settings['peers']) is str:
    peer_f = open(settings['peers'], 'r')
    settings['peers'] = list()
    for line in peer_f:
      settings['peers'].append(line.strip())
  
  server.addPeers(settings['peers'])
  server.run()
  return 0

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
    'auth': conversations.AuthConversation,
    # Set's a periodical caller to ping all connected peers
    'base': conversations.BaseConversation,
    'discover': conversations.DiscoverConversation
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
