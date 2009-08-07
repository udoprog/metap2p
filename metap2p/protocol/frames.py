from metap2p.binaryframe import Frame, Field, String, Integer, Boolean

import hashlib

class Header(Frame):
  digest = String(16);
  receiver = Integer();
  stage = Integer()
  size = Integer()

  def _beforepack(self):
    self.size = self._size()
    self.digest = self._digest('digest')

  def valid(self):
    return self.digest == self._digest('digest')

#  def beforesend(self):
#    if self.stage != self.expected_stage:
#      return [False, "unexpected stage"]
#    
#    return True

class Handshake(Header):
  uuid = Field('32s')

#  def beforesend(self):
#    if not Header.beforesend(self):
#      return False
#    
#    if self.digest is None:
#      return [False, "cannot send without digest"]
#    
#    return True

class Handshake_Ack(Header):
  uuid = Field('32s')

class Discover:
  hostname = Field('256s')
  hasnext = Field('i')

class MessageHead(Header):
  length = Field("i")

class MessagePart(Header):
  data = Field("4096s")
