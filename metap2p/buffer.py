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

  def has(self, n):
    return self.size >= n

  def read(self, n):
    if self.has(n):
      r = ''.join(self.buffer)
      rest = r[n:]
      self.buffer = list([rest]);
      self.size = len(rest)
      return r[0:n]
    
    return ""
