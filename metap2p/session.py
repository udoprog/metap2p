from twisted.internet import task, reactor

if __name__ == "__main__":
  from buffer import Buffer
  from binaryframe import Frame, Integer, String
else:
  from metap2p.buffer import Buffer
  from metap2p.binaryframe import Frame, Integer, String

class Session:
  """
  The session makes sure that all sent messages are queued until they receive a response.
  """
  headerframe = None
  default = None

  def __init__(self, peer):
    self.server = peer.server
    self.peer = peer
    
    ## queue containing all received data
    self.buffer = Buffer();
    
    self.tx = 0
    self.rx = 0
    
    ## all running periodcalls
    self._periods = list();
    
    assert self.headerframe is not None, "headerframe is None"
    
    if self.default:
      self.switch(self.default)
    
    self.sessionInit();
  
  def period(self, time, cb, *args, **kw):
    period = task.LoopingCall(cb, *args, **kw)
    period.start(time)
    self._periods.append(period)

  def later(self, cb, *args, **kw):
    reactor.callLater(0, cb, *args, **kw)
  
  def check_recv(self):
    """
    Check receiver queue and pack the header frame when possible.
    """
    
    while self.buffer.has():
      # nothing to do since we have not received any header frames yet...
      if not self.buffer.has(self.headerframe._size()):
        self.debug("buffer does not have anough data for header frame")
        return
      
      data = self.buffer.read(self.headerframe._size())
      self.rx += len(data)

      header = self.headerframe()._unpack(data)

      if not self.validateHeader(header):
        self.debug("Validation of header frame failed")
        return self.lose()
      
      if not self.buffer.has(self.getPayloadSize(header)):
        self.debug("Buffer does not contain enough data")
        continue
      
      data = self.buffer.read(self.getPayloadSize(header))
      
      if not self.validatePayload(header, data):
        self.debug("Validation of frame failed")
        return self.lose();
      
      self.rx += len(data)
      self.receiveFrame(header, data)

    return
    
  def recv(self, data):
    self.buffer.write(data)
    self.check_recv();

  def send(self, frame):
    self.prepareFrame(frame)

    header = self.buildHeaderFrame(self.headerframe, frame)
    
    if header is NotImplemented:
      self.debug("Session's buildHeaderFrame method not implemented!")
      return self.lose()
    
    data = header + frame._pack()
    
    self.tx += len(data)
    self.sendMessage(data)
    return True

  def lose(self):
    for period in self._periods:
      period.stop()
      del period
    
    del self.buffer
    self.buffer = Buffer()
    
    return self.loseConnection()

  def prepareFrame(self, frame):
    """
    Allows you the ability to prepare a frame before it is sent.
    Override this method.
    """
    pass

  def receiveFrame(self, header, data):
    """
    This is where frames that have no specific receiver attached to it ends up.
    Override method to work with.
    """
    pass

  def getPayloadSize(self, headerframe):
    """
    Figure out the entire frame size from the header.
    Override this method when used as multiplexer.
    """
    return 0

  def validateHeader(self, headerframe):
    """
    Override this method to implement early frame validation.
    Return false in order to lose connection.
    """
    return True

  def validatePayload(self, headerframe, data):
    """
    Override this method to implement early frame validation.
    Return false in order to lose connection.
    """
    return True

  def buildHeaderFrame(self, headerframe, frame):
    """
    Override this method to implement early frame validation.
    Return false in order to lose connection.
    """
    return NotImplemented

  def loseConnection(self):
    """
    Override this method in order to specify how to lose the connection.
    """
    pass
  
  def connectionMade(self):
    """
    Is called when connections are made.
    """
    pass

  def connectionLost(self, reason):
    """
    Are throwed when connections are lost.
    """
    pass

  def sessionInit(self):
    """
    Session initiated.
    """
    pass

  def _connectionMade(self):
    self.connectionMade()
  
  def _connectionLost(self, reason):
    self.connectionLost(reason)

  def sendMessage(self, data):
    self.debug("sendMessage:", repr(data))

  def debug(self, *msg):
    self.peer.debug(' '.join(map(lambda it: str(it), msg)))

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
  session.switch(TestConversation);
  session.recv(HeaderFrame(receiver=0, type=100)._pack())
