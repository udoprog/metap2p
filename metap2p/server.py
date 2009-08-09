from metap2p.service  import Service
from metap2p.peers    import Peer
from metap2p.factory  import ServerFactory, PeerFactory

import metap2p.modules  as modules
import metap2p.utils    as utils

from twisted.internet import task, reactor
from twisted.internet import error

#import ipaddr
#used temporarily to enable ports on ipaddr objects
#import ipaddr_ext

import uuid

import sys, os

def validate_port(p):
  if isinstance(p, int):
    return p >= 0 and p < 2**16
  elif isinstance(p, str) or isinstance(p, unicode):
    p = p.strip()

    if not p.isdigit():
      return False
    
    p = int(p)
    return validate_port(p)
  return False

def parse_port(p):
  if isinstance(p, int):
    if p >= 0 and p < 2**16:
      return p
  elif isinstance(p, str) or isinstance(p, unicode):
    p = p.strip()

    if not p.isdigit():
      return False
    
    return parse_port(int(p))
  
  return None

class Server:
  def __init__(self, serversession, clientsession, **settings):
    self.uuid = uuid.uuid1();
    
    self.serversession = serversession
    self.clientsession = clientsession
    
    self.defaultport = 8040
    self.service_loaded = False
    self.is_passive = False
    self.reload = False
    
    self.peers = list();
    self.tasks = list();
    
    self.__setup_settings(settings)
    
    self.tasks.append(task.LoopingCall(self.__connectionLoop))
    self.tasks.append(task.LoopingCall(self.__statusLoop))
  
  def __setup_settings(self, settings):
    self.settings = settings
    self.reloader = None
    
    if "reload" in self.settings:
      self.reload = self.settings['reload']
    
    if self.reload:
      self.__setup_reload();
    
    self.basedir = self.settings['base_dir']
    assert isinstance(self.basedir, str) and os.path.isdir(self.basedir),\
      "base_dir: is not a directory"
    
    if "defaultport" in self.settings:
      assert parse_port(self.settings['default_port']) is not None,\
        "default_port: is not a valid port; %s"%(self.port)
      self.defaultport = parse_port(self.settings['default_port'])
    
    if self.settings['passive']:
      self.host = "<passive>"
      self.port = 0
      self.is_passive = True
    else:
      try:
        ip = utils.IP(self.settings['listen_address'], port=self.defaultport)
      except:
        self.debug("Invalid Listen Address; assuming 0.0.0.0:defaultport")
        self.host = "0.0.0.0"
        self.port = self.defaultport
      else:
        if ip.version == 0:
          self.host = ip.host
        else:
          self.host = ip.ip_ext
        
        self.port = ip.port
    
    # set uri from loaded settings
    self.uri = "%s:%d"%(self.host, self.port)
    
    if self.settings['service']:
      sys.path.append(self.basedir)
      
      self.servicepath = self.get_root(settings['service_path'])
      assert isinstance(self.servicepath, str) and os.path.isdir(self.servicepath),\
        "service_path: is not a directory; %s"%(self.servicepath)
      
      try:
        ip = utils.IP(self.settings['service_address'], port=8080)
      except:
        self.debug("Invalid Service Listen Address; assuming 0.0.0.0:8080")
        self.servicehost = "0.0.0.0"
        self.serviceport = 8080
      else:
        if ip.version == 0:
          self.servicehost = ip.host
        else:
          self.servicehost = ip.ip_ext
        
        self.serviceport = ip.port
      
      self.servicepublic = settings['service_public']
      assert isinstance(self.servicepublic, str),\
        "service_public: is not a proper string; %s"%(self.servicepublic)
      
      assert self.settings['service_protocol'] in ["http", "https"],\
        "service_protocol: not a valid protocol, must be one of; http, https. Is: %s"%(self.port)
      self.serviceprotocol = self.settings['service_protocol']
      
      self.service_loaded = self.__setup_servicesite();
  
  def __setup_servicesite(self):
    try:
      self.metap2p_app = __import__('metap2p_service')
    except ImportError, e:
      self.debug(str(e))
      self.debug("Unable to import service application 'metap2p_service', is it in sys.path?")
      return False
    
    self.service = Service(self,
      self.servicehost,
      self.serviceport,
      self.servicepath,
      self.servicepublic,
      self.serviceprotocol)
    
    return True
  
  def __setup_reload(self):
    # overrides the import statement to keep track of what happens.
    self.reloader = modules.ModuleReloader()
    self.tasks.append(task.LoopingCall(self.__reloadLoop))
  
  def __reloadLoop(self):
    self.reloader.run()
  
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
        self.listen(reactor)
      except error.CannotListenError, e:
        print e
        return 1
    
    if self.service_loaded:
      try:
        self.service.listen(reactor);
      except error.CannotListenError, e:
        print e
        return 1
    
    for task in self.tasks:
      task.start(10)
    
    return reactor.run()
  
  def addPeers(self, peers):
    for peer in peers:
      self.addPeer(peer)
  
  def addPeer(self, peer):
    self.debug(peer)
    try:
      ip = utils.IP(peer, port=self.defaultport)
    except:
      return False
    
    self.debug("adding:", repr(ip.__class__))
    self.debug("    ip:", str(ip))
    
    if ip.version == 0:
      #we have a hostname
      self.peers.append(Peer(self, self.clientsession, ip.host, ip.port, persistent=True))
    else:
      self.peers.append(Peer(self, self.clientsession, ip.ip_ext, ip.port, persistent=True))
    
    return True
  
  def removePeer(self, host, port):
    pass
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s S %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))
  
  def get_root(self, *argv):
    import os
    return os.path.join(self.basedir, *argv)
  
  def connect(self, peer, timeout=2):
    return reactor.connectTCP(peer.host, peer.port, PeerFactory(peer), timeout = 2)
  
  def listen(self, reactor):
    reactor.listenTCP(self.port, ServerFactory(self, self.serversession), interface = self.host)
    self.debug("Listening at", self.uri)
