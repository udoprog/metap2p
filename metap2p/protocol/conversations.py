from metap2p.session import Conversation
from metap2p.protocol import frames

class MetaP2P:
  class Stage:
    """
    Just a list of the different stages in order to sanity check messages...
    Gotta find out a more sane way to do these.
    Also; uniqueness is all that counts. Not that they can be packed into the same variable : P.
    """
    Handshake = 0x0001
    Handshake_Ack = 0x0002
    
    Ping = 0x1000
    Pong = 0x2000
    
    """
    Request a discover session.
    """
    Discover_Req = 0x0100
    
    """
    Acknowledge the request of a discover session.
    """
    Discover_Ack = 0x0200

    MessageBegin = 0x8000
    MessageBegin_Ack = 0x8001
    MessageBegin_Deny = 0x8010
    
    MessageHead = 0x8002
    MessageHead_Ack = 0x8003
    
    MessagePart = 0x8004
    MessagePart_Ack = 0x8005

def expect_header(*expected_stages):
  """
  Used to decorate Session methods in order to expect a certain header type
  """
  def retfunc(func):
    def wrapper(self, frame):
      if frame.stage not in expected_stages:
        self.debug("BAD HEADER, unexpected stage")
        if self.session.peer.persistent:
          self.debug("Connection is persistent, will be removed")
          self.session.peer.server.peers.remove(self.session.peer)
        
        return False
      
      return func(self, frame)
    #wrapper
    return wrapper
  #override function
  return retfunc

#
# Message sending protocols needs some looking into.
#
class RecvMessageConversation(Conversation):
  def conversationStarted(self):
    """
    Acknowledge message should have been sent already.
    """
    self.debug("RecvMessageConversation")
    self.recv(frames.MessageHead, self.recv_head)
  
  @expect_header(MetaP2P.Stage.MessageHead)
  def recv_head(self, frame):
    self.message = self.session.peer.recv_message(frame.length)
    self.debug("receiving message that is", self.message.length, "bytes long")
    self.recv(frames.MessagePart, self.recv_part)
    return self.send(frames.Header(stage=MetaP2P.Stage.MessageHead_Ack))
  
  @expect_header(MetaP2P.Stage.MessagePart)
  def recv_part(self, frame):
    self.message.feed(frame.data)
    self.send(frames.Header(stage=MetaP2P.Stage.MessagePart_Ack))
    
    if self.message.complete:
      self.session.peer.queue.append(self.message)
      return self.switch('base');

class SendMessageConversation(Conversation):
  def conversationStarted(self):
    self.debug("SendMessageConversation")
    self.message = self.session.peer.messages.pop()
    self.send(frames.Header(stage=MetaP2P.Stage.MessageBegin))
    self.recv(frames.Header, self.recv_message_begin_response)
  
  @expect_header(MetaP2P.Stage.MessageBegin_Deny, MetaP2P.Stage.MessageBegin_Ack)
  def recv_message_begin_response(self, frame):
    """
    Begin conversation, see if client accepts invitation to receive message.
    """
    if frame.stage == MetaP2P.Stage.MessageBegin_Deny:
      self.debug("Send message request was denied, message is lost")
      return self.switch('base')
    
    if frame.stage == MetaP2P.Stage.MessageBegin_Ack:
      self.send(frames.MessageHead(stage=MetaP2P.Stage.MessageHead, length=self.message.length))
      return self.recv(frames.Header, self.recv_message_head_ack)
    
    return False
  
  @expect_header(MetaP2P.Stage.MessageHead_Ack)
  def recv_message_head_ack(self, frame):
    """
    Client has accepted the invitation to receive the message
    debug: close the connection with a nice message.
    """
    self.send(frames.MessagePart(stage=MetaP2P.Stage.MessagePart, data=self.message.data.encode('utf-8')))
    return self.recv(frames.Header, self.recv_message_part_response)
  
  @expect_header(MetaP2P.Stage.MessagePart_Ack)
  def recv_message_part_response(self, frame):
    return self.switch('base')

class DiscoverConversation(Conversation):
  def conversationStarted(self):
    import copy

    self.recv_done = False
    self.send_done = False
    
    self.debug("DiscoverConversation")

    self.peers = copy.copy(self.session.peer.server.peers)
    
    self.period(10, self.send_discover)
    self.recv(frames.Discover, self.recv_discover)

  def send_discover(self, frame):
    print "I WANT TO SEND", len(self.peers), "PEERS"
    peer = self.peers.pop()
    return self.switch('base')
  
  def recv_discover(self, frame):
    if not frame.hasnext:
      return self.recv_done()
    return True

  def recv_done(self):
    self.recv_done = True
    
    if self.recv_done and self.send_done:
      return self.switch('base')

  def send_done(self):
    self.send_done = True
    
    if self.recv_done and self.send_done:
      return self.switch('base')

class BaseConversation(Conversation):
  # allows this conversation to be overwritten.
  # just remember to design this conversation to be flexible.
  allow_next = True

  def conversationStarted(self):
    self.debug("BaseConversation")
    self.recv(frames.Header, self.recv_header)
    self.period(10, self.send_ping)
    #this is the send_discover subrouting, enable it to receive a bunch of nice errors
    #self.period(60, self.send_discover, now=False)
  
  def send_ping(self):
    #self.debug("Sent a ping to")
    self.send(frames.Header(stage=MetaP2P.Stage.Ping))
  
  def recv_header(self, frame):
    if frame.stage == MetaP2P.Stage.Ping:
      self.debug("Got a ping")
      #set it up for another receive later...
      self.recv(frames.Header, self.recv_header)
      return self.send(frames.Header(stage=MetaP2P.Stage.Pong))
    
    if frame.stage == MetaP2P.Stage.Pong:
      #self.debug("Got a ping response from")
      #set it up for another receive later...
      return self.recv(frames.Header, self.recv_header)
    
    if frame.stage == MetaP2P.Stage.MessageBegin:
      self.debug("Got request to receive message, acknowledged it")
      self.send(frames.Header(stage=MetaP2P.Stage.MessageBegin_Ack))
      return self.switch('recv_message')
    
    return False
  
  def send_discover(self):
    return self.switch('discover')

class AuthConversation(Conversation):
  def conversationStarted(self):
    self.debug("AuthConversation")
    
    self.got_handshake = False
    
    sendframe = frames.Handshake(stage=MetaP2P.Stage.Handshake, uuid=self.session.peer.server.uuid.hex) 
    sendframe.generate_digest()
    # just to make sure where we get our information.
    self.send(sendframe)
    
    #self.handshake(1, "dsd")
    # to recv the initial handshake
    return self.recv(frames.Handshake, self.handshake)
  
  @expect_header(MetaP2P.Stage.Handshake)
  def handshake(self, frame):
    #
    # Are we communicating with someone who has the same uuid as me?
    #
    if self.session.peer.server.uuid.hex == frame.uuid and False:
      self.debug("BAD Handshake, will not talk to self!")
      
      if self.session.peer.persistent:
        self.debug("Connection is persistent, will be removed")
        self.session.peer.server.peers.remove(self.session.peer)
      else:
        self.debug("Connection is volatile, no need to remove")
      
      return False
    
    #
    # Does the message digest work out?
    #
    if not frame.validate_digest():
      self.debug("BAD Handshake, integrity check fails!")
      return False
    #if uuid in self.session.server.connections:
    #  return False
    
    self.debug("OK Handshake")
    
    self.session.uuid = frame.uuid
    self.got_handshake = True

    sendframe = frames.Handshake_Ack(stage=MetaP2P.Stage.Handshake_Ack, uuid=self.session.uuid)
    sendframe.generate_digest()
    self.send(sendframe)

    #test = frames.Handshake_Ack()
    #test._feed_(sendframe._digest_())
    #raise repr(test.stage)
    
    # to recv the handshake ACK
    return self.recv(frames.Handshake_Ack, self.handshake_ack)
  
  @expect_header(MetaP2P.Stage.Handshake_Ack)
  def handshake_ack(self, frame):
    if not self.got_handshake:
      self.debug("BAD Handshake_Ack, no Handshake sent");
      return False
    
    if frame.uuid != self.session.peer.server.uuid.hex:
      self.debug("BAD Handshake_Ack, uuid mismatch");
      return False
    
    if not frame.validate_digest():
      self.debug("BAD Handshake_Ack, integrity check fails!")
      return False
    
    self.debug("OK Handshake ACK")
    #switch conversation
    return self.switch('base')
  
  def conversationEnded(self):
    pass
