import sys

from metap2p.modules import require_dep

if not require_dep('twisted'):
  print "Unable to import Twisted"
  print "  please install twisted from:"
  print "  http://twistedmatrix.com"
  sys.exit(99)
else:
  from twisted.internet.protocol import Factory, ClientFactory, Protocol
  from twisted.internet import reactor, task
  import twisted.internet.error as errors

import uuid

class Peer:
  connectionAttemptLimit = 10

  def __init__(self, server, sessionklass, host, port, connector = None, persistent = False, ip = None):
    self.host = host
    self.port = port
    self.ip = ip
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
  
  def __str__(self):
    return "<Peer ip=%s host=%s port=%s persistent=%s connected=%s>"%(repr(self.ip), repr(self.host), self.port, self.persistent, self.connected)

class ListenProtocol(Protocol):
  def __init__(self, factory, peer):
    self.peer = Peer(factory.server, factory.server.session, peer.host, peer.port, connector = self.transport, ip = peer.host);
  
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
    self.peer.ip = peer.host
    return self.protocol(self, self.peer)
  
  def clientConnectionFailed(self, connector, reason):
    if reason.type is errors.DNSLookupError:
      self.server.debug("Removing invalid Peer due to DNS Lookup Error:", self.peer)
      self.server.peers.remove(self.peer)
    else:
      self.peer.connectionFailed(reason)

class Server:
  def __init__(self, session, **settings):
    self.uuid = uuid.uuid1();
    
    self.session = session

    self.settings = settings
    
    if self.settings['passive']:
      self.host = "<passive>"
      self.port = 0
    else:
      self.host = self.settings['listen']['host']
      self.port = self.settings['listen']['port']
    
    self.uri = "%s:%s"%(self.host, self.port)
    
    self.peers = list();
    
    self.task_connectionLoop = task.LoopingCall(self.connectionLoop)
    self.task_statusLoop = task.LoopingCall(self.statusLoop)
  
  def run(self):
    if not self.settings['passive']:
      reactor.listenTCP(self.port, ServerFactory(self), interface = self.host)
    
    self.task_connectionLoop.start(10)
    self.task_statusLoop.start(10)
    return reactor.run()

  def addPeer(self, host, port):
    self.peers.append(Peer(self, self.session, host, port, persistent = True))

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
