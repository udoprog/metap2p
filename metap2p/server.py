from metap2p.service  import Service
from metap2p.peers    import Peer
from metap2p.factory  import ServerFactory, PeerFactory
import metap2p.metafile as metafile
import metap2p

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
    
    self.files = list();
    self.files_dir = "files";
    
    self.peers = list();
    self.tasks = list();

    self.basedir = "."

    self.listenaddress = "0.0.0.0:9040"
    
    self.is_service = True
    self.servicepath = "metap2p_service"
    self.servicepublic = "public"
    self.serviceaddress = "0.0.0.0:8080"
    self.serviceprotocol = "http"
    self.peers = list()
    
    self.__setup_settings(settings)
    
    self.tasks.append(task.LoopingCall(self.__connectionLoop))
    self.tasks.append(task.LoopingCall(self.__statusLoop))
  
  def __setup_settings(self, settings):
    self.settings = settings
    self.reloader = None
    
    self.reload = self.settings.get('reload', self.reload)
    self.peers = self.settings.get('peers', self.peers)
    
    if self.reload:
      # if we wish to reload already loaded modules.
      self.__setup_reload();
    
    self.basedir = self.settings.get('base_dir', self.basedir)
    assert isinstance(self.basedir, str) and os.path.isdir(self.basedir),\
      "base_dir: is not a directory"
    
    if "defaultport" in self.settings:
      self.defaultport = parse_port(self.settings.get('default_port', self.defaultport))
      assert self.defaultport is not None,\
        "default_port: is not a valid port; %s"%(self.defaultport)
    
    self.is_passive = self.settings.get('passive', self.is_passive)
    
    if self.is_passive:
      self.host = "<passive>"
      self.port = 0
    else:
      try:
        ip = utils.IP(self.settings.get('listen_address', self.listenaddress), port=self.defaultport)
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
    
    self.files_dir = self.get_root(settings.get('files_dir', self.files_dir))
    
    assert isinstance(self.files_dir, str) and os.path.isdir(self.files_dir),\
      "files_dir: is not a directory; %s"%(self.files_dir)

    self.is_service = self.settings.get('service', self.is_service)
    
    if self.is_service:
      sys.path.append(self.basedir)
      
      self.servicepath = self.get_root(settings.get('service_path', self.servicepath))
      assert isinstance(self.servicepath, str) and os.path.isdir(self.servicepath),\
        "service_path: is not a directory; %s"%(self.servicepath)
      
      try:
        ip = utils.IP(self.settings.get('service_address', self.serviceaddress), port=8080)
      except:
        self.debug("Invalid Service Listen Address; assuming 0.0.0.0:8080")
        self.servicehost = "0.0.0.0"
        self.serviceport = 8080
      else:
        if ip.version == 0:
          # if type is hostname
          self.servicehost = ip.host
        else:
          # IPv4 or IPv6
          self.servicehost = ip.ip_ext
        
        # Port
        self.serviceport = ip.port
      
      self.servicepublic = settings.get('service_public', self.servicepublic)
      assert isinstance(self.servicepublic, str),\
        "service_public: is not a proper string; %s"%(self.servicepublic)
      
      self.serviceprotocol = self.settings.get('service_protocol', self.serviceprotocol)
      assert self.serviceprotocol in ["http", "https"],\
        "service_protocol: not a valid protocol, must be one of; http, https. Is: %s"%(self.serviceprotocol)
      
      self.service_loaded = self.__setup_servicesite();

  def __reload_files(self):
    for f in os.listdir(self.files_dir):
      fp = os.path.join(self.files_dir, f)
      
      if os.path.isfile(fp):
        mf = metafile.MetaFile(self.files_dir, digest=False)
        fs = open(fp)
        
        try:
          mf.loads(fs.read())
          
          file_exists = False

          for ffm in self.files:
            if ffm.digest_id == mf.digest_id:
              file_exists = True
              break

          if file_exists:
            break
          
          # add file
          self.debug(fp)
          self.files.append(mf)
        except metap2p.trdparty.bencode.BTFailure:
          continue
        finally:
          fs.close();

  
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
    """
    Attempt to connect to all peers.
    """
    
    for peer in self.peers:
      if not peer.connected:
        peer.connect();
  
  def __statusLoop(self):
    """
    Just a status loop printing informtion about peers to terminal.
    """
    
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
    # reload files in files directory
    self.__reload_files();

    # load peers
    self.addPeers(self.peers)
    
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
    
    #self.debug("adding:", repr(ip.__class__))
    #self.debug("    ip:", str(ip))
    
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
 
  def get_file(self, *argv):
    import os
    return os.path.join(self.files_dir, *argv)
  
  def connect(self, peer, timeout=2):
    return reactor.connectTCP(peer.host, peer.port, PeerFactory(peer), timeout = 2)
  
  def listen(self, reactor):
    reactor.listenTCP(self.port, ServerFactory(self, self.serversession), interface = self.host)
    self.debug("Listening at", self.uri)

  def listfiles(self):
    return self.files
