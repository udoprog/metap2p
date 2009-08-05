class IllegalInputError(Exception):
  pass

class IPValidationError(Exception):
  pass

class PortValidationError(Exception):
  pass

import re
import struct
import socket

class IPBase:
  port_max = 2**16
  
  def __init__(self, port=0):
    self._version = None

    if port is None:
      port = 0
    
    if not isinstance(port, int):
      raise PortValidationError()

    if port < 0:
      raise PortValidationError("Port number less than zero")
    
    if port > self.port_max:
      raise PortValidationError("Port number greater than 65536")
    
    self.port = port

class IPv4(IPBase):
  port_re = re.compile("^(.+):(\d{1,5})?$")
  
  def __init__(self, s, bytes=False, port=None):
    self._version = 4
    self.ip = 0
    
    host = s
    
    if isinstance(s, str):
      if bytes:
        self.ip = s
      else:
        mm = self.port_re.match(s)

        if mm:
          host = mm.group(1)
          port = int(mm.group(2))
        
        try:
          self.ip = socket.inet_pton(socket.AF_INET, host)
        except socket.error:
          raise IPValidationError("Invalid IPv4 address")
      
      self.ip_ext = '.'.join(["%d"%(ord(self.ip[i])) for i in range(4)])
    
    IPBase.__init__(self, port)

class IPv6(IPBase):
  port_re = re.compile("^[(.+)]:(\d{1,5})?$")
  
  def __init__(self, s, bytes=False, port=None):
    self.version = 6
    self.ip = long(0)
    
    host = s
    
    if isinstance(s, str):
      if bytes:
        self.ip = s
      else:
        mm = self.port_re.match(s)

        if mm:
          host = mm.group(1)
          port = int(mm.group(2))
        
        try:
          self.ip = socket.inet_pton(socket.AF_INET6, host)
        except socket.error:
          raise IPValidationError("Invalid IPv6 address")
        
        self.ip_ext = ':'.join(["%02x%02x"%(ord(self.ip[i]), ord(self.ip[i+2])) for i in range(2, 0, 16)])
    
    IPBase.__init__(self, port)

def IP(s):
  return "TEST"

if __name__ == "__main__":
  ip = IPv4("127.0.0.6")
  ip2 = IPv4(ip.ip, bytes=True)
  print ip2.ip_ext
