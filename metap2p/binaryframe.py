import struct

class Field(object):
  # must be set for this to work properly.
  __name__ = None
  # is used in order to sort the fields properly
  __instance_counter = 0
  
  def __init__(self, *args, **kw):

    if len(args) == 1:
      self.struct = args[0]
      self._inherit_struct = False
    else:
      self._inherit_struct = True

    self._instance = self.__class__.__instance_counter
    self.__class__.__instance_counter += 1
    
    self.default = kw.get('default')
  
  def __set__(self, obj, val):
    if obj is None:
      return None
    
    obj.__store__[self.__name__] = val
  
  def __get__(self, obj, objtype):
    if obj is None:
      #class access
      return self.default
    
    # instsance access
    return obj.__store__[self.__name__]
  
  def __cmp__(self, other):
    return cmp(self._instance, other._instance)
  
  def __str__(self):
    return "<Field name='%s'>"%(self.__name__)

class Frame(object):
  __used__ = False

  class __metaclass__(type):
    """
    This is called when building the class object singleton for all subclasses.
    """
    def __init__(cls, name, bases, dict):
      type.__init__(cls, name, bases, dict)
      cls.setup_frame()
  
  def __init__(self, **kw):
    self.__store__ = dict()
    
    for k in self.__class__.__fields__:
      field = self.__class__.__fields__[k]
      self.__store__[k] = field.default
    
    for k in kw:
      setattr(self, k, kw[k])
    
    self._create_()
  
  def _digest_(self):
    for field in self.__class__.__ordered_fields__:
      if field.__get__(self, None) is None:
        raise Exception("%s: Field '%s' is None"%(repr(self), field.__name__))
    
    return struct.pack(self.__class__.__frame__, *map(lambda field: field.__get__(self, None), self.__class__.__ordered_fields__))
  
  def _feed_(self, data):
    if len(data) < self._size_():
      raise Exception("input not long enough")
    
    if len(data) != self._size_():
      data = buffer(data, 0, self._size_())
    
    for field, arg in zip(self.__class__.__ordered_fields__, struct.unpack(self.__class__.__frame__, data)):
      field.__set__(self, arg)
    
    return self
  
  def _size_(self):
    return self.__class__.__size__
  
  def _create_(self):
    pass
    #self.size = self._size_();
  
  @classmethod
  def setup_frame(cls):
    """
    Mark this class type as a 'used_frame', otherwise it will refuse to be digested or fed properly.

    If not marked as used; All values will be None, digest will return None.
    """
    cls.__fields__ = dict()
    
    for f in cls.__dict__:
      attr = cls.__dict__[f]
      if isinstance(attr, Field):
        attr.__name__ = f
        cls.__fields__[f] = attr
    
    for super in cls.__bases__:
      for f in super.__dict__:
        attr = super.__dict__[f]
        
        if isinstance(attr, Field):
          if f not in cls.__fields__:
            cls.__fields__[f] = attr
            continue
          
          field = cls.__fields__[f]
          
          if field._inherit_struct:
            field.struct = attr.struct
            field._inherit_struct = False
            field._instance = attr._instance

    cls.__ordered_fields__ = cls.__fields__.values()
    cls.__ordered_fields__.sort()

    cls.__frame__ = ''.join(map(lambda f: f.struct, cls.__ordered_fields__))
    cls.__size__ = struct.calcsize(cls.__frame__)

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
