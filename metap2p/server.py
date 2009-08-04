from metap2p.service import ServiceResource
from metap2p.peers import Peer
from metap2p.factory import ServerFactory, PeerFactory

from twisted.web import server
from twisted.internet import task, reactor
import twisted.internet.error as errors

import ipaddr
#used temporarily to enable ports on ipaddr objects
import ipaddr_ext

import uuid

import sys, os

def validate_port(p):
  if isinstance(p, int):
    return p >= 0 and p < 2**16
  elif isinstance(p, str) or isinstance(p, unicode):
    if not p.isdigit():
      return False
    
    p = int(p)
    return validate_port(p)
  return False

class Server:
  def __init__(self, session, **settings):
    self.uuid = uuid.uuid1();
    self.session = session
    
    self.defaultport = 8040
    self.service_loaded = False
    self.is_passive = False
    
    self.__setup_settings(settings)
    
    self.peers = list();
    self.tasks = list()
    
    self.tasks.append(task.LoopingCall(self.__connectionLoop))
    self.tasks.append(task.LoopingCall(self.__statusLoop))
  
  def __setup_settings(self, settings):
    self.settings = settings
    
    self.basedir = self.settings['base_dir']
    assert isinstance(self.basedir, str) and os.path.isdir(self.basedir),\
      "base_dir: is not a directory"
    
    if self.settings['passive']:
      self.host = "<passive>"
      self.port = 0
      self.is_passive = True
    else:
      self.host = self.settings['listen_host']
      assert isinstance(self.host, str),\
        "listen_host: is not a valid host"
      
      assert validate_port(self.settings['listen_port']),\
        "listen_port: is not a valid port; %s"%(self.port)
      self.port = int(self.settings['listen_port'])
    
    # set uri from loaded settings
    self.uri = "%s:%d"%(self.host, self.port)
    
    if self.settings['service']:
      self.debug("Adding", self.basedir, "to sys.path")
      sys.path.append(self.basedir)
      
      self.servicepath = self.get_root(settings['service_path'])
      assert isinstance(self.servicepath, str) and os.path.isdir(self.servicepath),\
        "service_path: is not a directory; %s"%(self.servicepath)
      
      self.servicepublic = settings['service_public']
      assert isinstance(self.servicepublic, str),\
        "service_public: is not a proper string; %s"%(self.servicepublic)
      
      self.servicehost = self.settings['service_host']
      assert isinstance(self.servicehost, str),\
        "service_host: is not a valid host"
      
      assert validate_port(self.settings['service_port']),\
        "service_port: is not a valid port; %s"%(self.port)
      self.serviceport = int(self.settings['service_port'])
      
      self.service_loaded = self.__setup_servicesite();

    if "defaultport" in self.settings:
      assert validate_port(self.settings['default_port']),\
        "default_port: is not a valid port; %s"%(self.port)
      self.defaultport = int(self.settings['default_port'])
  
  def __setup_servicesite(self):
    try:
      self.metap2p_app = __import__('metap2p_service')
    except ImportError, e:
      self.debug(str(e))
      self.debug("Unable to import service application 'metap2p_service', is it in sys.path?")
      return False
    
    serviceresource = ServiceResource(self, self.servicehost, self.serviceport)
    self.servicesite = server.Site(serviceresource)
    
    return True
  
  def __connectionLoop(self):
    for peer in self.peers:
      if not peer.connected:
        peer.connect();
  
  def __statusLoop(self):
    import time
    self.debug("My list of Peers:")
    
    if len(self.peers) == 0:
      self.debug("<NO PEERS>")
    else:
      counter = 0
      for peer in self.peers:
        self.debug("%04d"%(counter), str(peer))
        counter += 1
  
  def run(self):
    """
    Sets up listeners and queues tasks.
    """
    if not self.is_passive:
      try:
        reactor.listenTCP(self.port, ServerFactory(self), interface = self.host)
      except errors.CannotListenError, e:
        print e
        return 1
    
    if self.service_loaded:
      try:
        reactor.listenTCP(self.serviceport, self.servicesite, interface = self.servicehost)
      except errors.CannotListenError, e:
        print e
        return 1
    
    for task in self.tasks:
      task.start(10)
    
    return reactor.run()
  
  def addPeers(self, peers):
    for peer in peers:
      self.addPeer(peer)
  
  def addPeer(self, peer):
    ip = ipaddr_ext.IP(peer.strip())
    
    # not a valid ip-addr, assume it's a hostname then.
    if not ip:
      if ':' in peer:
        host, port = peer.split(':')
        host = host.strip()
        port = int(port.strip())
      else:
        host = peer.strip()
        port = self.defaultport
    else:
      host = ip.ip_ext
      
      if ip.port:
        port = ip.port
      else:
        port = self.defaultport
    
    self.peers.append(Peer(self, self.session, host, port, persistent=True))
  
  def removePeer(self, host, port):
    pass
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s S %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))
  
  def get_root(self, *argv):
    import os
    return os.path.join(self.basedir, *argv)
  
  def connect(self, peer, timeout=30):
    return reactor.connectTCP(peer.host, peer.port, PeerFactory(peer), timeout = 30)
