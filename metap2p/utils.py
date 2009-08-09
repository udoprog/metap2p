class IllegalInputError(Exception):
  pass

class IPValidationError(Exception):
  pass

class PortValidationError(Exception):
  pass

import re
import struct
import socket

def to_str(s):
  if isinstance(s, unicode):
    return s.encode('utf-8')
  elif isinstance(s, str):
    return s
  else:
    return ""

class IPBase:
  port_max = 2**16
  
  def __init__(self, host=None, port=0):
    self.host = host
    
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
  port_re = re.compile("^(.+):(\d{1,5})$")
  
  def __init__(self, s, bytes=False, port=None):
    s = to_str(s)
    self.version = 4
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
    
    IPBase.__init__(self, None, port)

  def __str__(self):
    return "%s:%d"%(self.ip_ext, self.port)

  def __repr__(self):
    return "<IPv4 %s:%d>"%(self.ip_ext, self.port)

class IPv6(IPBase):
  port_re = re.compile("^\[(.+)\]:(\d{1,5})$")
  
  def __init__(self, s, bytes=False, port=None):
    s = to_str(s)
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
        except socket.error, e:
          raise IPValidationError("Invalid IPv6 address")
        
      parts = ["%02x%02x"%(ord(self.ip[i]), ord(self.ip[i+1])) for i in range(0, 16, 2)]
      self.ip_ext = ':'.join(parts)
    
    IPBase.__init__(self, None, port)
  
  def __str__(self):
    return "[%s]:%d"%(self.ip_ext, self.port)

  def __repr__(self):
    return "<IPv6 [%s]:%d>"%(self.ip_ext, self.port)

class Host(IPBase):
  port_re = re.compile("^(.+):(\d{1,5})$")
  host_re = re.compile("^([\w\d]+[\w\d\-]*[\w\d]+\.?)+$")
  
  def __init__(self, s, port=None):
    s = to_str(s)
    self.version = 0
    self.ip = None
    
    mm = self.port_re.match(s)

    if mm:
      self.host = mm.group(1)
      s = int(mm.group(2))

    if not self.host_re.match(s):
      raise IPValidationError("Invalid Hostname")
    
    IPBase.__init__(self, s, port)

  def __str__(self):
    return "%s:%d"%(self.host, self.port)

def IP(s, port=0):
  try:
    return IPv4(s, port=port)
  except IPValidationError, e:
    pass

  try:
    return IPv6(s, port=port)
  except IPValidationError, e:
    pass
  
  return Host(s, port=port)

if __name__ == "__main__":
  print IP("192.178.1.1:80")
  print IP("::", port=12)
  print IP("google.se", port=80)
  print IP("www.google.se", port=80)
  print IP(u"localhost")
  #ip = IPv4("127.0.0.6")
  #ip2 = IPv4(ip.ip, bytes=True)
  #print ip2.ip_ext
