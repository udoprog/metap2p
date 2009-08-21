import sys

from twisted.internet.protocol import Factory, ClientFactory, Protocol
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, task
from twisted.web import server, static
import twisted.internet.error as errors

from metap2p.peers import Peer

#import metap2p.rest.router as router

class ListenProtocol(Protocol):
  def __init__(self, factory, peer):
    self.peer = Peer(factory.server, factory.serversession, peer.host, peer.port, connector=self.transport);
  
  def connectionMade(self):
    self.peer.connectionMade(self.transport)
  
  def dataReceived(self, data):
    self.peer.dataReceived(data)
  
  def connectionLost(self, reason):
    self.peer.connectionLost(reason)

class ServerFactory(Factory):
  protocol = ListenProtocol
  
  def __init__(self, server, serversession):
    print "Initiated the ServerFactory"
    self.server = server
    self.serversession = serversession

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
