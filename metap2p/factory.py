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

