from metap2p.binaryframe import Struct, Field, String, Integer, Boolean

import hashlib

class Header(Struct):
  MAX_SIZE = 2**16

  magic = String(4, default="mP2P")
  
  ## to keep the header digest by itself
  headerdigest = String(20)
  
  id_from = String(16)
  id_to =   String(16)
  
  size = Integer()
  
  signature = String(16)
  digest = String(20)
  
  padding = String(56)
  
  type = Integer(default=0x0)

  def generatePayloadDigest(self, data):
    m = hashlib.new('sha1')
    m.update(data)
    self.digest = m.digest()

  def validatePayloadDigest(self, data):
    m = hashlib.new('sha1')
    m.update(data)
    return self.digest == m.digest()

  def hdigest(self):
    self.headerdigest = self._digest('headerdigest')

  def hvalidate(self):
    return self.headerdigest == self._digest('headerdigest')

class Handshake(Struct):
  type = Integer(default=0x0001)
  uuid = String(32)

class Oper(Struct):
  type = Integer(default=0x0020)
  ack = Boolean()

class MessageHead(Struct):
  id = String(32)
  type = Integer(default=0x1000)
  length = Integer(default=0)
  parts = Integer()
  mime = String(64)
  name = String(128)

class MessagePart(Struct):
  id = String(32)
  type = Integer(default=0x2000)
  part = Integer()
  length = Integer()
  message = String(2**15)
