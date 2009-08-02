import struct

class Field(object):
  __instance_counter = 0
  __name__ = None

  def __init__(self, struct, default=None):
    self.struct = struct
    self.id = id(self)
    self.default = default
    
    self.__instance = self.__class__.__instance_counter
    self.__class__.__instance_counter += 1
  
  def __set__(self, obj, val):
    obj.__store__[self.id] = val
  
  def __get__(self, obj, objtype):
    if self.id in obj.__store__:
      return obj.__store__[self.id]
    return self.default
  
  def __cmp__(self, other):
    return cmp(self.__instance, other.__instance)

class Frame(object):
  __used__ = False

  class __metaclass__(type):
    """
    This is called when building the class object singleton for all subclasses.
    """
    def __init__(cls, name, bases, dict):
      type.__init__(name, bases, dict)
      cls.setup_frame()
  
  def __init__(self, **kw):
    self.__store__ = dict()
    for k in kw:
      setattr(self, k, kw[k])
  
  def _digest_(self):
    if not self.__class__.__used__:
      return None

    for field in self.__class__.__fields__:
      if field.__get__(self, None) is None:
        raise Exception("Field %s:%d is None"%(field.__name__, field.__instance))
    
    return struct.pack(self.__class__.__frame__, *map(lambda field: field.__get__(self, None), self.__class__.__fields__))
  
  def _feed_(self, data):
    if not self.__class__.__used__:
      return

    for field, arg in zip(self.__class__.__fields__, struct.unpack(self.__class__.__frame__, data)):
      field.__set__(self, arg)
  
  def _size_(self):
    return self.__class__.__size__
  
  @classmethod
  def setup_frame(cls):
    """
    Mark this class type as a 'used_frame', otherwise it will refuse to be digested or fed properly.

    If not marked as used; All values will be None, digest will return None.
    """
    cls.__fields__ = list()

    # grab all subclasses of this class
    classes = list()
    classes.append(cls)
    for subclass in cls.__bases__:
      classes.append(subclass)
    
    # grab all fields defined
    for klass in classes:
      for k in klass.__dict__:
        if isinstance(klass.__dict__[k], Field):
          klass.__dict__[k].__name__ = k
          cls.__fields__.append(klass.__dict__[k])
    
    cls.__fields__.sort()
    cls.__frame__ = ''.join(map(lambda field: field.struct, cls.__fields__))
    cls.__used__ = True
    cls.__size__ = struct.calcsize(cls.__frame__)

  def beforesend(self):
    return True

if __name__ == '__main__':
  ping1 = Ping(stage = 22)

  hand1 = Handshake(stage = 4)
  hand1.uuid = "test1"

  hand2 = Handshake(stage = 12)
  hand2.uuid = "test2"

  print hand1.uuid
  print hand2.uuid

  print "Handshake digest:", repr(hand1.digest())
  print "Ping digest:", repr(ping1.digest())

#  frame = None
#  before = None
#  
#  def __init__(self):
#    if self.before:
#      self.before = self.before();
#    
#    self.parts = list();
#    parts = self.__class__.__dict__
#    
#    for k in parts:
#      if isinstance(parts[k], Field):
#        pp = parts[k]
#        self.parts.append(pp)
#    
#    self.parts.sort()
#    self.frame = ''.join(map(lambda part: part.struct, self.parts))
#  
#  def digest(self):
#    result = list();
#    
#    if self.before:
#      result.append(self.before.digest())
#    
#    result.append(struct.pack(self.frame, *map(lambda part: part.val, self.parts)))
#    return ''.join(result)
#
#  def size(self):
#    beforesize = 0
#    
#    if self.before:
#      beforesize = self.before.size()
#
#    return beforesize + struct.calcsize(self.frame)
#
#  def feed(self, data):
#    feeddata = None
#
#    if self.before:
#      size = self.before.size()
#      
#      before = buffer(data, 0, size)
#      feeddata = buffer(data, size, -1)
#      
#      self.before.feed(before);
#    else:
#      feeddata = buffer(data)
#    
#    args = struct.unpack(self.frame, feeddata)
#    
#    for arg, part in zip(args, self.parts):
#      part.val = arg
#
#  def clear(self):
#    if self.before:
#      self.before.clear();
#    
#    for part in self.parts:
#      part.val = None

#class Handshake(Frame):
#  before = Header
  
#  uuid = Field('32s')
#  hash = Field('16s')

#  def extraDigest(self):

#header = Header()
#header.stage = 12

#header2 = Header()
#header2.stage = 13
#print header.stage
#print header2.stage

#print header.digest();

#print repr(header.digest())

#print header.digest()

#header2 = Handshake()
#header2.feed(header.digest())
#print header2.hash
#print header2.uuid
#print header2.before.stage

#header3 = Handshake();
#print header3.hash
#print header3.uuid
#print header3.before.stage

#hh.feed(struct.pack("i16s", 5, "a" * 16))
#hh.get('stage')
#hh.body_digest();
