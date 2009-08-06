import metap2p.utils as utils

class Message:
  def __init__(self, length, data=None):
    self.received = 0
    self.length = length
    self.complete = False
    self.queue = list()
    self.data = data
  
  def feed(self, data):
    self.received += len(data)
    self.queue.append(data)
    
    if self.received >= self.length:
      self.complete = True
      self.data = ''.join(self.queue)
      del self.queue

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

    # messages to send
    self.messages = list()
    
    # messages received
    self.queue = list()
    
    self.sessionklass = sessionklass;
    self.session = None
  
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
      self.connector = self.server.connect(self)
  
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
      self.ip = utils.IP(ip)
    else:
      self.ip = None
  
  def __str__(self):
    return "<Peer ip=%s host=%s port=%s persistent=%s connected=%s>"%(repr(self.ip), repr(self.host), self.port, self.persistent, self.connected)
  
  def send_message(self, data):
    self.messages.append(Message(len(data), data))
    # this will trigger this channel to go into a specific conversation when it is ready.
    self.session.spawn_conversation('send_message')
  
  def recv_message(self, length):
    newmessage = Message(length)
    self.queue.append(newmessage)
    return newmessage
