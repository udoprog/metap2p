import ipaddr
import re

#match ipv4 with port number
ipv4_re = re.compile("^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d+)$")
#strip the tags for easy writing of port in ipv6
ipv6_re = re.compile("^\[(.*)\](:(\d+))?$")

def IP(s):
  try:
    if isinstance(s, str):
      ipv4_match = ipv4_re.match(s)

      if ipv4_match:
        ip = ipaddr.IPv4(ipv4_match.group(1))
        
        if ipv4_match.group(2):
          ip.port = int(ipv4_match.group(2))
        else:
          ip.port = None

        return ip

      ipv6_match = ipv6_re.match(s)
      if ipv6_match:
        ip = ipaddr.IPv6(ipv6_match.group(1))
        
        if ipv6_match.group(3):
          ip.port = int(ipv6_match.group(3))
        else:
          ip.port = None
        
        return ip

    ip = ipaddr.IP(s)
    ip.port = None
    return ip
  except:
    return None
