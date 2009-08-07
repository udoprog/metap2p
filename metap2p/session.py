from twisted.internet import task

if __name__ == "__main__":
  from buffer import Buffer
  from binaryframe import Frame, Integer, String
else:
  from metap2p.buffer import Buffer
  from metap2p.binaryframe import Frame, Integer, String

class Conversation:
  def __init__(self, id, session):
    self.id = id;
    self.session = session;
    self._buffer = Buffer();
    self._recv_frames = list();
  
  def begin(self):
    self.conversationStarted();
  
  def debug(self, *msg):
    self.session.debug(*msg)
    return True
  
  def recv(self, frame, cb):
    self._recv_frames.insert(0, (frame, cb))
    return True

  def send(self, frame):
    self.session.prepareFrame(self, frame)
    self.session.send(frame._pack())
    return True
  
  def _session_recv_check(self):
    if len(self._recv_frames) == 0:
      return
    
    frame, cb = self._recv_frames[-1]

    if self._buffer.has(frame._size()):
      cb(frame()._unpack(self._buffer.read(frame._size())))
      self._recv_frames.pop();
  
  def _session_recv(self, data):
    self._buffer.write(data)
    self._session_recv_check();
    return None
  
  def conversationStarted(self):
    pass

class Session:
  multiplex = True
  headerframe = None
  
  def __init__(self):
    self.ccounter = 0
    ## list containing all receivers
    self.receivers = list();
    ## fast lookup dictionary
    self.receivers_ff = dict();
    ## queue containing all received data
    self.buffer = Buffer();
    
    assert self.headerframe is not None, "headerframe is None"
  
  def spawn(self, c):
    if not callable(c):
      self.debug("argument is not callable");
      return
    
    conv = c(self.ccounter, self);
    
    if not isinstance(conv, Conversation):
      del conv
      self.debug("argument is not a Conversation");
      return
    
    self.ccounter += 1
    self.receivers.append(conv);
    conv.begin();
  
  def send_to(self, receiver_id, data):
    """
    send data directly to a specific conversation.
    Not very useful when using session as a multiplexer but will allow certain types of data to pass right through.
    """
    
    for recv in self.receivers:
      if recv.id == receiver_id:
        recv._session_recv(data)
        return True
    
    return False
  
  def check_recv(self):
    """
    Check receiver queue and pack the header frame when possible.
    """

    # nothing to do since we have not received any header frames yet...
    if not self.buffer.has(self.headerframe._size()):
      self.debug("buffer does not have anough data for header frame")
      return
    
    header = self.headerframe()._unpack(self.buffer.read(self.headerframe._size(), buffered=True))
    
    if not self.buffer.has(self.getFrameSize(header)):
      self.debug("Buffer does not contain enough data")
      return
    
    if not self.validateFrame(header):
      self.debug("Losing connection since frame not valid")
      return self.loseConnection();
    
    receiver_id = self.getReceiverID(header)

    if not self.send_to(receiver_id, self.buffer.read(self.getFrameSize(header))):
      self.debug("Receiver does not exist")
  
  def recv(self, data):
    self.buffer.write(data)
    self.check_recv();
  
  def send(self, data):
    self.debug("write:", repr(data))
  
  def getReceiverID(self, headerframe):
    """
    Figure out which conversation is suppose to receive this frame.
    """
    return 0

  def getFrameSize(self, headerframe):
    """
    Figure out the entire frame size from the header.
    Override this method when used as multiplexer.
    """
    return 0
  
  def validateFrame(self, headerframe):
    """
    Override this method to implement early frame validation.
    Return false in order to lose connection.
    """
    return True

  def loseConnection(self):
    """
    Override this method in order to specify how to lose the connection.
    """
    pass
  
  def debug(self, *msg):
    print ' '.join(msg)

#class Conversation:
#  allow_next = False
#  
#  def __init__(self, session):
#    self.session = session
#    self.periodcalls = list()
#    self._conversationStarted()
#  
#  def recv(self, frameklass, cb):
#    return self.session.recv(frameklass, cb)
#  
#  def send(self, frame):
#    return self.session.send(frame)
#  
#  def period(self, time, cb, *args, **kw):
#    start_kw = {}
#    if 'now' in kw:
#      start_kw['now'] = kw.pop('now')
#    
#    loop = task.LoopingCall(cb, *args, **kw)
#    loop.start(time, **start_kw)
#    self.periodcalls.append(loop)
#    return True
#  
#  def spawn(self, conv):
#    self.session.spawn_conversation(conv)
#    return True
#  
#  def debug(self, *msg):
#    self.session.peer.debug(*msg);
#    return True
#  
#  def end(self):
#    self._conversationEnded();
#    return True
#  
#  def _conversationStarted(self):
#    self.conversationStarted();
#  
#  def _conversationEnded(self):
#    """
#    destroy the conversation in an internal matter.
#    """
#    while len(self.periodcalls) > 0:
#      periodcall = self.periodcalls.pop()
#      periodcall.stop();
#    
#    self.conversationEnded();
#
#  def _conversationLost(self):
#    self.debug("Lost Conversation")
#    self._conversationEnded();
#  
#  def conversationStarted(self):
#    pass
#  
#  def conversationEnded(self):
#    pass
#
#import struct
#
#class Session:
#  conversations = {}
#  default = None
#
#  tx = 0
#  rx = 0
#  
#  def __init__(self, peer):
#    self.recvstack = list()
#    self.sendstack = list()
#    self.inbuffer = Buffer();
#
#    self.peer = peer
#    self.running_conversation = None
#    self.next_conversation = list()
#    
#    if self.default:
#      self.spawn_conversation(self.default)
#    
#    self._connectionMade()
#  
#  def spawn_conversation(self, conv):
#    if conv not in self.conversations:
#      self.peer.debug("Tried to spawn invalid conversation: %s"%(conv))
#      return True
#    
#    return self.conversations[conv](self)
#  
#  def feed(self, bytes):
#    self.inbuffer.write(bytes)
#    while self.__handle_recvstack():
#      pass
#  
#  def has_digest(self, frames = 0):
#    return len(self.sendstack) > frames
#  
#  def digest(self):
#    if len(self.sendstack) > 0:
#      frame = self.sendstack.pop()
#      return frame._pack();
#    
#    return ''
#  
#  def __handle_recvstack(self):
#    if len(self.recvstack) <= 0:
#      return
#    
#    frameklass, cb = self.recvstack[-1]
#    frame = frameklass()
#    
#    if self.inbuffer.has(frame._size()):
#      self.rx += frame._size()
#      frame._unpack(self.inbuffer.read(frame._size()))
#      
#      if not cb(frame):
#        self.loseConnection()
#        return False
#      
#      self.recvstack.pop()
#      return True
#    
#    return False
#  
#  def __handle_sendstack(self):
#    while self.has_digest():
#      tx_digest = self.digest()
#      self.tx += len(tx_digest)
#      self.write(tx_digest)
#  
#  def recv(self, frameklass, cb):
#    self.recvstack.insert(0, (frameklass, cb))
#    return True
#  
#  def send(self, frame):
#    self.sendstack.append(frame)
#    self.__handle_sendstack();
#    return True
#  
#  def _connectionMade(self):
#    self.connectionMade();
#  
#  def _connectionLost(self, reason):
#    self.connectionLost(reason)
#    if self.running_conversation:
#      self.running_conversation._conversationLost();
#  
#  def connectionLost(self, reason):
#    pass
#  
#  def connectionMade(self):
#    pass
#  
#  def loseConnection(self):
#    self.peer.connector.loseConnection();
#
#  def write(self, data):
#    """
#    discard the information if no bindings exist.
#    """
#    pass

if __name__ == "__main__":
  class HeaderFrame(Frame):
    type = Integer()
    receiver = Integer()
    digest = String(16)
    size = Integer()

    def _beforepack(self):
      self.size = self._size();
      self.digest = self._digest('digest');

    def valid(self):
      return self.digest == self._digest('digest')
  
  class TestConversation(Conversation):
    def conversationStarted(self):
      self.debug("Conversation Started")
      self.recv(HeaderFrame, self.recv_header)

    def recv_header(self, frame):
      print frame.type
  
  class TestSession(Session):
    multiplex = True
    headerframe = HeaderFrame
    
    """
    TestSession is a multiplexer, therefore it needs to know who the information is meant for.
    """
    def getReceiverID(self, headerframe):
      return headerframe.receiver
    
    def getFrameSize(self, headerframe):
      return headerframe.size
    
    def validateFrame(self, headerframe):
      return headerframe.valid();
    
    def loseConnection(self):
      self.debug("Suppose to lose connection, but this is a simulation")
      pass

    def prepareFrame(self, conv, frame):
      frane.receiver = conv.id
  
  session = TestSession();
  session.spawn(TestConversation);
  session.recv(HeaderFrame(receiver=0, type=100)._pack())
