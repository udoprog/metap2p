class IllegalInputError(Exception):
  pass

class IPValidationError(Exception):
  pass

class PortValidationError(Exception):
  pass

import re
import struct

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
  fast_re = re.compile("^((\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}))(:(\d{1,5}))?$")
  ip_max = 2**32
  
  def __init__(self, s, bytes=False, port=None):
    self._version = 4
    self.ip = 0
    
    if isinstance(s, str):
      if bytes:
        if len(s) != 8:
          raise IllegalInputError("Expected string with length 4")
        
        self.ip = s
        
        parts = struct.unpack("i1s1s1s1s", self.ip)
        self.ip_ext = "%d.%d.%d.%d"%tuple(map(lambda c: ord(c), parts[1:]))
        self.port = parts[0]
      else:
        mm = self.fast_re.match(s)
        
        if mm:
          parts = list();
          
          for i in range(4):
            parts.append("%c"%(int(mm.group(i+2))))
          
          if mm.group(6):
            port = int(mm.group(7))
          
          IPBase.__init__(self, port=port)
          
          self.ip_ext = mm.group(1)
          self.ip = struct.pack("i1s1s1s1s", self.port, *parts)
        else:
          raise IPValidationError()
    else:
      raise IllegalInputError("Not a valid IPv4 address");
    

class IPv6(IPBase):
  _group = "[a-fA-F0-9]{1,4}"
  _area = "(%(grp)s):(%(grp)s):(%(grp)s):(%(grp)s):(%(grp)s):(%(grp)s):(%(grp)s):(%(grp)s)"%{'grp': _group}
  _ipv6_re1_port_ptn = "^\[(%(area)s)\]:(\d{1,5})$"%{'area': _area}
  
  #complete length regex with port
  ipv6_re1_port = re.compile(_ipv6_re1_port_ptn)
  #complete length regex without port
  ipv6_re1 = re.compile("$%(area)s^")

  max = 2**32
  
  def __init__(self, s, bytes=False, port=None):
    self.version = 6
    self.ip = long(0)

    if isinstance(s, str):
      if bytes:
        print len(s)
        if len(s) != (4 * 8 + 4):
          raise IPValidationError()
        
        parts = tuple(struct.unpack("iiiiiiiii", s))
        
        self.ip = s
        self.ip_ext = "%04x:%04x:%04x:%04x:%04x:%04x:%04x:%04x"%parts[1:]
        self.port = parts[0]
      else:
        if s == "::":
          IPBase.__init__(self, port=port)
          self.ip_ext = "0000:0000:0000:0000:0000:0000:0000:0000"
          self.ip = struct.pack("iiiiiiiii", self.port, 0, 0, 0, 0, 0, 0, 0, 0)
          return

        m1 = self.ipv6_re1_port.match(s)
        if m1:
          parts = list()
          
          for i in range(8):
            parts.append(int(m1.group(i + 2), 16))
          
          if m1.group(10):
            port = int(m1.group(10))
          
          IPBase.__init__(self, port=port)
          
          self.ip_ext = m1.group(1)
          self.ip = struct.pack("iiiiiiiii", port, *parts)
          return
        
        raise IllegalInputError("Not a valid IPv6 address");


def IP(s):
  return "TEST"

if __name__ == "__main__":
  IP(255 + 255 * 2**8 + 254 * 2**16 + 255 * 2**24)
  
#  ip = IPv4("0.0.0.0")
#  assert ip.ip == 0, "str -> long conversion"
#  assert ip.port is None, "ip.port should be None"
#  ip = IPv4("255.255.255.255")
#  assert ip.ip == 255 + 255 * 2**8 + 255 * 2**16 + 255 * 2**24, "str -> long conversion"
#  assert ip.port is None, "ip.port should be None"
#  ip = IPv4("0.0.0.0:65536")
#  assert ip.ip == 0, "str -> long conversion"
#  assert ip.port == 65536, "ip.port should be 65536"
#  
#  ip = IPv4("0.0.0.0", port=65536)
#  assert ip.ip == 0, "str -> long conversion"
#  assert ip.port == 65536, "ip.port should be 65536"
#
#  try:
#    ip = IPv4("0.0.0.0", port=65537)
#    assert False, "port number should trigger exception"
#  except PortValidationError:
#    pass
#
#  try:
#    ip = IPv4("0.0.0.0", port=-1)
#    assert False, "port number should trigger exception"
#  except PortValidationError:
#    pass
  
#  ip = IPv4(255 + 255 * 2**8 + 255 * 2**16 + 255 * 2**24)
#  assert ip.ip_ext == "255.255.255.255", "long -> str conversion"

  matcher = re.compile(IPv6._area)
  #if not matcher.match('[FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF:FFFF]:80'):
  #  print "BAD MATCHER"
  ip = IPv4("127.0.0.1:3241", port=32141)
  ip2 = IPv4(ip.ip, bytes=True)
  print ip2.ip_ext
  print ip2.port
  ip = IPv6('[0:A:0:0:0:0:0:F]:3412')
  ip2 = IPv6(ip.ip, bytes=True)
  print ip2.ip_ext
  print ip2.port
  ip = IPv6('[::ff]')
  ip2 = IPv6(ip.ip, bytes=True)
  print ip2.ip_ext
  print ip2.port
