from metap2p.binaryframe import Frame, Field, String, Integer, Boolean

import hashlib

class Header(Frame):
  send_to = Integer(default=0);
  send_from = Integer(default=0);
  
  digest = String(16);
  stage = Integer()
  size = Integer()

  def _beforepack(self):
    self.size = self._size()
    self.digest = self._digest('send_to', 'send_from', 'stage', 'size')
  
  def valid(self):
    return self.digest ==  self._digest('send_to', 'send_from', 'stage', 'size')

class Spawn(Header):
  conv = String(12)

class Ping(Header):
  stage = Field(default=0x8888)

class Pong(Header):
  stage = Field(default=0x7777)

#  def beforesend(self):
#    if self.stage != self.expected_stage:
#      return [False, "unexpected stage"]
#    
#    return True

class Handshake(Header):
  uuid = Field('32s')

class HandshakeResponse(Header):
  uuid = Field('32s')
  ack = Boolean()

