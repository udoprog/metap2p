import metap2p.utils as utils
from metap2p.buffer import Buffer
import metap2p.protocol.frames as frames

import uuid

class RecvMessage:
  def __init__(self, messageheader):
    self.messageheader = messageheader
    self.id = self.messageheader.id
    self.buffer = Buffer()
    self.received = -1
    self.completed = False
    self.message = ""
    self.mime = messageheader.mime
    self.name = messageheader.name

  def feed(self, frame):
    if frame.id != self.messageheader.id:
      return False
    
    if self.received >= self.messageheader.parts:
      return False
    
    self.received += 1

    self.buffer.write(str(buffer(frame.message, 0, frame.length)))
    
    if self.received == self.messageheader.parts:
      self.completed = True
      self.message = self.buffer.read()
      
      f = open('/tmp/%s'%(self.name), 'w')
      f.write(self.message)
      f.close()
      
      del self.buffer
    
    return True

class SendMessage:
  PART_SIZE = 2**15
  
  def __init__(self, message, mime, name):
    self.id = uuid.uuid1().hex
    self.length = len(message)
    self.parts = self.length / self.PART_SIZE
    self.sent = -1
    self.buffer = Buffer()
    self.buffer.write(message)
    self.mime = mime
    self.name = name
  
  def getHead(self):
    return frames.MessageHead(id=self.id, length=self.length, parts=self.parts, mime=self.mime, name=self.name)
  
  def getPart(self):
    if self.sent >= self.parts:
      return None
    
    self.sent += 1
    
    if self.buffer.has(self.PART_SIZE):
      length = self.PART_SIZE
      data = self.buffer.read(self.PART_SIZE);
    else:
      length = self.buffer.size
      data = self.buffer.read();
    
    return frames.MessagePart(id=self.id, part=self.sent, message=data, length=length)

class Peer:
  connectionAttemptLimit = 10
  
  def __init__(self, server, sessionklass, host, port, connector = None, persistent = False, ip = None):
    self.host = host
    self.port = port
    
    self.set_ip(self.host, self.port)
    
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
    self.queue = dict()
    
    self.sessionklass = sessionklass;
    self.session = self.sessionklass(self)

    self.messagequeue = list()
  
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
    # reset the counter for connection attempts
    self.connectionAttempts = 0
    
    self.connector = connector
    self.connected = True

    #makes no sense to append a persistent connection (outwars connection to list of peers)
    if not self.persistent:
      self.server.peers.append(self)
    
    self.session._connectionMade()
  
  def dataReceived(self, data):
    self.session.recv(data)
  
  def write(self, data):
    self.session.write(data)
  
  def connectionLost(self, reason):
    self.debug("Connection Lost")
    self.session._connectionLost(reason)
    
    if not self.persistent:
      self.server.peers.remove(self)
    
    self.connected = False
    self.connector = None

    # create a brand new session
    del self.session
    self.session = self.sessionklass(self)

  def connectionFailed(self, reason):
    self.connectionAttempts += 1
    
    if self.connectionAttempts > self.connectionAttemptLimit:
      self.server.debug("Removing Peer due to too many connection attempts:", self)
      self.server.peers.remove(self)
  
  def connect(self):
    # if connection is not persistent, then there is no reason to try and connect.
    # the connection is made when it has been accepted by the listen server.
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
  
  def set_ip(self, ip=None, port=None):
    if ip:
      self.ip = utils.IP(ip, port=port)
    else:
      self.ip = None
  
  def __str__(self):
    return "<Peer ip=%s host=%s port=%s persistent=%s connected=%s>"%(repr(self.ip), repr(self.host), self.port, self.persistent, self.connected)
  
  def send_message(self, data, mime="plain/text", name="message.txt"):
    message = SendMessage(data, mime, name)

    self.session.send(message.getHead())
    self.session.later(self._send_message_part, message)

  def _send_message_part(self, message):
    i = 0

    while i < 16:
      i += 4
      part = message.getPart()
      
      if not part:
        return
      
      if not self.session.send(part):
        self.debug("unable to send message part!")
        return
    
    self.session.later(self._send_message_part, message)

  def recv_message(self, frame):
    return RecvMessage(frame)
  
  def __del__(self):
    del self.session
