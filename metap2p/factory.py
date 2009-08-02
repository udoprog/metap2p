import sys

from twisted.internet.protocol import Factory, ClientFactory, Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, task
import twisted.internet.error as errors

import ipaddr
#used temporarily to enable ports on ipaddr objects
import ipaddr_ext

import uuid

import metap2p.rest.routes as routes

class Peer:
  connectionAttemptLimit = 10

  def __init__(self, server, sessionklass, host, port, connector = None, persistent = False, ip = None):
    self.host = host
    self.port = port

    self.set_ip(ip)
    
    self.connectionAttempts = 0
    
    self.uri = "%s:%s"%(host, port)
    
    self.connected = connector != None
    self.connector = connector
    self.persistent = persistent
    self.server = server
    self.disabled = False
    
    self.sessionklass = sessionklass;
  
  def __eq__(self, other):
    if isinstance(other, Peer):
      return self.host == other.host and self.port == other.port
    return NotImplemented
  
  def __ne__(self, other):
    result = self.__eq__(other)
    
    if result is NotImplemented:
      return result
    
    return not result
  
  def connectionMade(self, connector):
    self.debug("Connection Made")

    # reset the counter for connection attempts
    self.connectionAttempts = 0
    
    self.connector = connector
    self.connected = True

    #makes no sense to append a persistent connection (outwars connection to list of peers)
    if not self.persistent:
      self.server.peers.append(self)
    
    self.session = self.sessionklass(self)
  
  def dataReceived(self, data):
    self.session.feed(data)
  
  def write(self, data):
    self.session.write(data)
  
  def connectionLost(self, reason):
    self.debug("Connection Lost")
    
    self.session._connectionLost(reason)
    
    del self.session
    
    if not self.persistent:
      self.server.peers.remove(self)
    
    self.connected = False
    self.connector = None

  def connectionFailed(self, reason):
    self.connectionAttempts += 1
    
    if self.connectionAttempts > self.connectionAttemptLimit:
      self.server.debug("Removing Peer due to too many connection attempts:", self)
      self.server.peers.remove(self)
  
  def connect(self):
    # if connection is not persistent, then there is no reason to try and connect.
    # the connection is made when it has been accepted.
    if not self.persistent:
      return
    
    # will refuse to connect if disabled
    # done deal : P
    if self.disabled:
      return
    
    if self.connector == None:
      self.connector = reactor.connectTCP(self.host, self.port, PeerFactory(self), timeout = 30)
  
  def disconnect(self):
    if self.connected:
      self.connector.loseConnection();
      self.connector = None
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s   %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))

  def set_ip(self, ip=None):
    if ip:
      self.ip = ipaddr.IP(ip)
    else:
      self.ip = None
  
  def __str__(self):
    return "<Peer ip=%s host=%s port=%s persistent=%s connected=%s>"%(repr(self.ip), repr(self.host), self.port, self.persistent, self.connected)

class ListenProtocol(Protocol):
  def __init__(self, factory, peer):
    self.peer = Peer(factory.server, factory.server.session, peer.host, peer.port, connector = self.transport, ip=peer.host);
  
  def connectionMade(self):
    self.peer.connectionMade(self.transport)
  
  def dataReceived(self, data):
    self.peer.dataReceived(data)
  
  def connectionLost(self, reason):
    self.peer.connectionLost(reason)

class ServerFactory(Factory):
  protocol = ListenProtocol
  
  def __init__(self, server):
    print "Initiated the ServerFactory"
    self.server = server

  def buildProtocol(self, peer):
    return self.protocol(self, peer)

class PeerProtocol(Protocol):
  def __init__(self, factory, peer):
    self.peer = peer;
  
  def connectionMade(self):
    self.peer.connectionMade(self.transport)
  
  def dataReceived(self, data):
    self.peer.dataReceived(data)
  
  def connectionLost(self, reason):
    self.peer.connectionLost(reason)

class PeerFactory(ClientFactory):
  protocol = PeerProtocol
  
  def __init__(self, peer):
    self.server = peer.server
    self.peer = peer
  
  def buildProtocol(self, peer):
    self.peer.set_ip(peer.host)
    return self.protocol(self, self.peer)
  
  def clientConnectionFailed(self, connector, reason):
    if reason.type is errors.DNSLookupError:
      self.server.debug("Removing invalid Peer due to DNS Lookup Error:", self.peer)
      self.server.peers.remove(self.peer)
    else:
      self.peer.connectionFailed(reason)

class ServiceProtocol(LineReceiver):
  delimiter = "\n"

  def __init__(self, server):
    self.server = server
    self.router = routes.setup_routes()
  
  def lineReceived(self, data):
    parts = data.split()
    command = parts[0].lower()

    if command == "list-peers":
      self.list_peers(parts[1:])
    else:
      self.transport.write("UNKNOWN\n")
  
  def list_peers(self, argv):
    peerlist = list()
    for peer in self.server.peers:
      if peer.connected:
        peerlist.append("%s %d"%(peer.ip.ip_ext, peer.port))
    self.writelist(peerlist)

  def writelist(self, list):
    self.transport.write("LIST\n")
    for item in list:
      self.transport.write(":%s\n"%(item))
    self.transport.write("END\n")
  
  def connectionMade(self):
    self.server.debug("connection made")
    self.transport.write("OK\n")

  def connectionLost(self, reason):
    self.server.debug("connection lost")

class ServiceFactory(Factory):
  protocol = ServiceProtocol
  
  def __init__(self, server):
    print "Initiated the ServiceFactory"
    self.server = server
  
  def buildProtocol(self, peer):
    return ServiceProtocol(self.server)

class Server:
  def __init__(self, session, **settings):
    self.uuid = uuid.uuid1();
    
    self.session = session

    self.settings = settings
    
    if self.settings['passive']:
      self.host = "<passive>"
      self.port = 0
    else:
      self.host = self.settings['listen_host']
      self.port = int(self.settings['listen_port'])
    
    if self.settings['service']:
      self.servicehost = self.settings['service_host']
      self.serviceport = int(self.settings['service_port'])
    
    self.uri = "%s:%s"%(self.host, self.port)
    
    self.peers = list();
    
    self.task_connectionLoop = task.LoopingCall(self.connectionLoop)
    self.task_statusLoop = task.LoopingCall(self.statusLoop)
  
  def run(self):
    if not self.settings['passive']:
      try:
        reactor.listenTCP(self.port, ServerFactory(self), interface = self.host)
      except errors.CannotListenError, e:
        print e
        return 1
    
    if self.settings['service']:
      try:
        reactor.listenTCP(self.serviceport, ServiceFactory(self), interface = self.servicehost)
      except error.CannotListenError, e:
        print e
        return 1
    
    self.task_connectionLoop.start(10)
    self.task_statusLoop.start(10)
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
        port = self.settings['defaultport']
    else:
      host = ip.ip_ext
      
      if ip.port:
        port = ip.port
      else:
        port = self.settings['defaultport']
    
    self.peers.append(Peer(self, self.session, host, port, persistent=True))
  
  def removePeer(self, host, port):
    pass
  
  def connectionLoop(self):
    for peer in self.peers:
      if not peer.connected:
        peer.connect();

  def statusLoop(self):
    import time
    self.debug("My list of Peers:")
    
    if len(self.peers) == 0:
      self.debug("<NO PEERS>")
    else:
      counter = 0
      for peer in self.peers:
        self.debug("%04d"%(counter), str(peer))
        counter += 1
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s S %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))
