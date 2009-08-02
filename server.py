#from metap2p.factory import ServerFactory
from metap2p.session import Session, Conversation
from metap2p.factory import Server
from metap2p.modules import require_dep
from metap2p.protocol import conversations

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
