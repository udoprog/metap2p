class Buffer:
  """
  A simple buffering class.
  """
  
  def __init__(self):
    self.buffer = list()
    self.size = 0
  
  def write(self, bytes):
    self.size += len(bytes)
    self.buffer.append(bytes)

  def has(self, n=1):
    return self.size >= n

  def top_has(self, n):
    return len(self.buffer[-1]) == n

  def read(self, n=None, buffered=False):
    if not n:
      n = self.size
    
    if self.has(n):
      if self.top_has(n):
        if buffered:
          return self.buffer[-1]
        else:
          self.size -= n
          return self.buffer.pop()
      else:
        # buffer has too much information : /
        # this is a lazy method of getting as much buffer as you need.
        r = ''.join(self.buffer)
        rest = r[n:]
        
        if not buffered:
          # reset the queue to something nice...
          self.buffer = list([rest]);
          self.size = len(rest)
        
        return r[0:n]
    
    return ""
