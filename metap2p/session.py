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

    self._periods = list();

  def period(self, time, cb, *args, **kw):
    period = task.LoopingCall(cb, *args, **kw)
    period.start(time)
    self._periods.append(period)
  
  def begin(self):
    self.conversationStarted();

  def end(self):
    for period in self._periods:
      period.stop();
    
    self.conversationEnded();
  
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

  def spawn(self, conv):
    return self.session.spawn(conv)
  
  def _session_recv_check(self):
    if len(self._recv_frames) == 0:
      return
    
    frame, cb = self._recv_frames[-1]

    if self._buffer.has(frame._size()):
      recv_frame = frame()._unpack(self._buffer.read(frame._size()))
      
      if not self.session.validateFrame(recv_frame):
        self.debug("Losing connection since frame not valid")
        return self.session.loseConnection();
      
      cb(recv_frame)
      self._recv_frames.pop();
  
  def _session_recv(self, data):
    self._buffer.write(data)
    self._session_recv_check();
    return None
  
  def conversationStarted(self):
    pass

  def conversationEnded(self):
    pass

class Session:
  multiplex = True
  headerframe = None
  
  conversations = dict()

  default = None
  
  def __init__(self, peer):
    self.peer = peer
    self.ccounter = 0
    ## list containing all receivers
    self.receivers = list();
    ## fast lookup dictionary
    self.receivers_ff = dict();
    ## queue containing all received data
    self.buffer = Buffer();

    self.tx = 0
    self.rx = 0
    
    assert self.headerframe is not None, "headerframe is None"

    if self.default:
      self.spawn(self.default)
    
    self._connectionMade()
  
  def spawn(self, conv):
    c = self.conversations.get(conv, None)

    if not c:
      self.debug("could not find conversation");
    
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
        self.rx += len(data)
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
    
    receiver_id = self.getReceiverID(header)
    
    if not self.send_to(receiver_id, self.buffer.read(self.getFrameSize(header))):
      self.debug("Receiver does not exist")
  
  def recv(self, data):
    self.buffer.write(data)
    self.check_recv();
  
  def send(self, data):
    self.tx += len(data)
    self.sendMessage(data)
  
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
  
  def _connectionMade(self):
    self.connectionMade()
  
  def connectionMade(self):
    pass
  
  def _connectionLost(self, reason):
    self.connectionLost(reason)
  
  def connectionLost(self, reason):
    pass

  def sendMessage(self, data):
    self.debug("sendMessage:", repr(data))
  
  def debug(self, *msg):
    print ' '.join(msg)

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
