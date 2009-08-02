from metap2p.binaryframe import Frame, Field

import md5

class Header(Frame):
  stage = Field('i')

#  def beforesend(self):
#    if self.stage != self.expected_stage:
#      return [False, "unexpected stage"]
#    
#    return True

class Handshake(Header):
  digest = Field('16s')
  uuid = Field('32s')

  def generate_digest(self):
    m = md5.new(self.uuid)
    self.digest = m.digest()
  
  def validate_digest(self):
    m = md5.new(self.uuid)
    return self.digest == m.digest()

#  def beforesend(self):
#    if not Header.beforesend(self):
#      return False
#    
#    if self.digest is None:
#      return [False, "cannot send without digest"]
#    
#    return True

class Handshake_Ack(Header):
  digest = Field('16s')
  uuid = Field('32s')

  def generate_digest(self):
    m = md5.new(self.uuid)
    self.digest = m.digest()
  
  def validate_digest(self):
    m = md5.new(self.uuid)
    return self.digest == m.digest()

class Discover:
  hostname = Field('256s')
  hasnext = Field('i')
