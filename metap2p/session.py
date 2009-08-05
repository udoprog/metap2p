from twisted.internet import task
from metap2p.buffer import Buffer

class Conversation:
  allow_next = False
  
  def __init__(self, session):
    self.session = session
    self.periodcalls = list()
  
  def recv(self, frameklass, cb):
    return self.session.recv(frameklass, cb)
  
  def send(self, frame):
    return self.session.send(frame)
  
  def period(self, time, cb, *args, **kw):
    start_kw = {}
    if 'now' in kw:
      start_kw['now'] = kw.pop('now')
    
    loop = task.LoopingCall(cb, *args, **kw)
    loop.start(time, **start_kw)
    self.periodcalls.append(loop)
    return True
  
  def switch(self, conv):
    self.session.switch_conversation(conv)
    return True
  
  def debug(self, *msg):
    self.session.peer.debug(*msg);

  def _conversationStarted(self):
    self.conversationStarted();
  
  def _conversationEnded(self):
    """
    destroy the conversation in an internal matter.
    """
    while len(self.periodcalls) > 0:
      periodcall = self.periodcalls.pop()
      periodcall.stop();
    
    self.conversationEnded();

  def _conversationLost(self):
    self._conversationEnded();
  
  def conversationStarted(self):
    pass
  
  def conversationEnded(self):
    pass

import struct

class Session:
  conversations = {}
  default = None

  tx = 0
  rx = 0
  
  def __init__(self, peer):
    self.recvstack = list()
    self.sendstack = list()
    self.inbuffer = Buffer();

    self.peer = peer
    self.running_conversation = None
    self.next_conversation = list()
    
    if self.default:
      self.switch_conversation(self.default)
    
    self._connectionMade()
  
  def switch_conversation(self, conv):
    if conv not in self.conversations:
      self.peer.debug("Switching to invalid conversation: %s"%(conv))
      return
    
    if self.running_conversation:
      self.running_conversation._conversationEnded();
      del self.running_conversation
      self.running_conversation = None
    
    if self.__check_for_next():
      return
    
    self.running_conversation = self.conversations[conv](self)
    self.running_conversation._conversationStarted()
  
  def next(self, conv):
    """
    either queue up the next conversation or switch emmidiately if the current allows it.
    """
    
    self.next_conversation.insert(0, conv);
    return self.__check_for_next()
  
  def __check_for_next(self):
    if self.running_conversation is None:
      return False
    
    if self.running_conversation.allow_next:
      if len(self.next_conversation) > 0:
        switch_to = self.next_conversation.pop()
        return self.switch_conversation(switch_to)
    
    return False
  
  def feed(self, bytes):
    self.inbuffer.write(bytes)
    while self.__handle_recvstack():
      pass

  def has_digest(self, frames = 0):
    return len(self.sendstack) > frames
  
  def digest(self):
    if len(self.sendstack) > 0:
      sendstack = self.sendstack
      self.sendstack = list();
      return ''.join(map(lambda frame: frame._digest_(), sendstack))
    
    return ''
  
  def __handle_recvstack(self):
    if len(self.recvstack) <= 0:
      return
    
    frameklass, cb = self.recvstack[-1]
    frame = frameklass()
    
    if self.inbuffer.has(frame._size_()):
      self.rx += frame._size_()
      frame._feed_(self.inbuffer.read(frame._size_()))
      
      if not cb(frame):
        self.loseConnection()
        return False
      
      self.recvstack.pop()
      return True
    
    return False

  def __handle_sendstack(self):
    if self.has_digest():
      tx_digest = self.digest()
      self.tx += len(tx_digest)
      self.write(tx_digest)
  
  def recv(self, frameklass, cb):
    self.recvstack.insert(0, (frameklass, cb))
    return True
  
  def send(self, frame):
    self.sendstack.append(frame)
    self.__handle_sendstack();
    return True
  
  def _connectionMade(self):
    self.connectionMade();
  
  def _connectionLost(self, reason):
    self.connectionLost(reason)
    if self.running_conversation:
      self.running_conversation._conversationLost();
  
  def connectionLost(self, reason):
    pass
  
  def connectionMade(self):
    pass
  
  def loseConnection(self):
    self.peer.connector.loseConnection();

  def write(sellf):
    pass
