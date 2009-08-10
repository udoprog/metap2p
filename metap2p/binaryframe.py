import struct

class ImmutableDict(dict):
  def __setitem__(self, key, value):
    raise ValueError("Cannot set value in an immutable dict")

class Field(object):
  # must be set for this to work properly.
  __name__ = None
  
  # is used in order to sort the fields properly
  __instance_counter = 0
  
  __slots__ = ('_instance', 'default', 'struct')
  
  def __init__(self, *args, **kw):
    if len(args) == 1:
      self.struct = args[0]
    
    self._instance = Field.__instance_counter
    Field.__instance_counter += 1
    
    self.default = kw.get('default')
  
  def __set__(self, instance, val):
    if instance is None:
      raise ValueError("Cannot set values on metaclasses")
    
    #instance._tainted = True
    instance.__store__[self.__name__] = val
  
  def __get__(self, instance, owner):
    # class access
    if instance is None:
      return self.default
    
    # instance access
    # get is more effective than pre-assignment
    return instance.__store__.get(self.__name__, self.default)
  
  def __cmp__(self, other):
    return cmp(self._instance, other._instance)
  
  def __str__(self):
    return "<Field name='%s'>"%(self.__name__)
  
  def __getstval__(self, instance, owner):
    return Field.__get__(self, instance, owner)
  
  def __setstval__(self, instance, val):
    return Field.__set__(self, instance, val)

class Integer(Field):
  def __init__(self, default=0):
    try:
      Field.__init__(self, "i", default=int(default))
    except ValueError, e:
      raise ValueError("Default value is not a valid integer")
  
  def __set__(self, obj, val):
    try:
      return Field.__set__(self, obj, int(val))
    except ValueError, e:
      raise ValueError("Default value is not a valid integer")

class String(Field):
  def __init__(self, length, default=""):
    try:
      Field.__init__(self, "%ds"%(length), default=str(default))
    except struct.error:
      raise ValueError("Bad struct pack")
  
  def __set__(self, obj, val):
    try:
      return Field.__set__(self, obj, str(val))
    except ValueError, e:
      raise ValueError("Default value is not a valid string")

class Boolean(Field):
  TRUE = chr(1)
  FALSE = chr(0)
  
  def __init__(self, **kw):
    Field.__init__(self, "s", default=(self.TRUE if kw.pop('default', False) else self.FALSE))
  
  def __set__(self, obj, val):
    if val:
      return Field.__set__(self, obj, self.TRUE)
    else:
      return Field.__set__(self, obj, self.FALSE)
  
  def __get__(self, obj, val):
    val = Field.__get__(self, obj, val)
    
    if val == self.TRUE:
      return True
    else:
      return False

class Frame(object):
  __used__ = False

  __slots__ = ('__store__', '_tainted', '__old_digest')

  class __metaclass__(type):
    """
    This is called when building the class object singleton for all subclasses.
    """
    def __init__(cls, name, bases, dict):
      type.__init__(cls, name, bases, dict)
      cls.setup_frame()
  
  def __init__(self, **kw):
    self.__store__ = dict()
    for k in kw: setattr(self, k, kw[k])
 
  def _pack(self, *args):
    self._beforepack()
    
    ## Performance boost.
    return self.__class__.__frame.pack(*[self.__store__.get(field.__name__, field.default) for field in self.__class__.__ordered_fields])
  
  def _unpack(self, data):
    if len(data) < self._size():
      raise Exception("input not long enough")
    
    if len(data) != self._size():
      data = buffer(data, 0, self._size())
    
    # do we have a quicker method?
    for f, arg in zip(self.__class__.__ordered_fields, self.__class__.__frame.unpack(data)):
      self.__store__[f.__name__] = arg
      #field.__setstval__(self, arg)
    #  
    #[field.__setstval__(self, arg) for field, arg in zip(self.__class__.__ordered_fields, self.__class__.__frame.unpack(data))]
    
    return self
  
  def _digest(self, *exceptions):
    global hashlib
    if hashlib is None:
      import hashlib
    
    m = hashlib.new('sha1')
    
    for field in self.__ordered_fields:
      if field.__name__ not in exceptions:
        m.update(struct.pack(field.struct, field.__getstval__(self, None)))
    
    return m.digest()
  
  def _size(self):
    return self.__class__._size()
  
  @classmethod
  def _size(klass):
    return klass.__size
  
  def _create(self):
    pass

  def _beforepack(self):
    pass
    #self.size = self._size();
  
  @classmethod
  def setup_frame(cls):
    """
    Mark this class type as a 'used_frame', otherwise it will refuse to be digested or fed properly.

    If not marked as used; All values will be None, digest will return None.
    """
    fields = dict()
    
    for f, attr in cls.__dict__.items():
      if not isinstance(attr, Field):
        continue
      
      attr.__name__ = f
      fields[f] = attr
    
    for super in cls.__bases__:
      for f, attr in super.__dict__.items():
        if not isinstance(attr, Field):
          continue
        
        if f not in fields:
          fields[f] = attr
          continue
        
        field = fields[f]
        
        if not field.struct:
          field.struct = attr.struct
          field._instance = attr._instance
    
    cls.__ordered_fields = tuple(sorted(fields.values()))
    #cls.__ordered_fields.sort()
    
    cls._fields = ImmutableDict(**fields)
    
    cls.__frame = struct.Struct(''.join(map(lambda f: f.struct, cls.__ordered_fields)))
    cls.__size = cls.__frame.size

if __name__ == '__main__':
  class TestFrame(Frame):
    foo = Integer()
  
  class TestFrameChild(TestFrame):
    bar = String(2)
    baz = Boolean()

  def test_strings():
    class StringFrame1(Frame):
      base1 = String(10)
    
    class StringFrame2(Frame):
      base1 = String(10)
      base2 = String(20)

    class StringFrame3(Frame):
      base1 = String(10, default="FEAZ")
    
    # make sure default balues are set
    assert StringFrame1.base1 == ""
    assert StringFrame2.base1 == ""
    assert StringFrame2.base2 == ""
    assert StringFrame3.base1 == "FEAZ"
    
    # make sure it is impossible to assign values to metaclass
    frame1 = StringFrame1();
    
    try:
      frame1.base1 = "TEST"
    except Exception, e:
      assert not e, e
  
  def test_booleans():
    class BooleanFrame1(Frame):
      bool1 = Boolean()

    bf = BooleanFrame1(bool1 = False)
    
    assert bf.bool1 == False, "Boolean value not set"
    bf2 = BooleanFrame1()._unpack(bf._pack())
    assert bf2.bool1 == bf.bool1, "Boolean unpack does not work"

  def test_performance():
    class FieldTest(Frame):
      i1 = Integer()
      i2 = Integer()
      i3 = Integer()
      i4 = Integer()
    
    import time

    start = time.time()
    
    for x in range(10000):
      f1 = FieldTest()#i1=1, i2=2, i3=3, i4=4)
      f1._pack(1,2,3,4)
      f2 = FieldTest()._unpack(f1._pack())

    stop = time.time()

    print "TIME:", stop - start

    ss2 = struct.Struct("iiii")

    start = time.time()
    
    for x in range(10000):
      data = ss2.pack(1,2,3,4)
      i1, i2, i3, i4 = ss2.unpack(data)
    
    stop = time.time()
    
    print "VS TIME (optimal and unfair):", stop - start
  
  print "testing performance"
  test_performance()
  print "                OK!"
  
  print "Testing string..."
  for x in range(20000):
    test_strings();
  print "                 OK"
  
  print "Testing booleans..."
  for x in range(20000):
    test_booleans()
  print "                 OK"
  
  assert TestFrame.foo == 0, "Integer field has invalid default value"
  
  assert TestFrameChild.foo == 0, "TestFrameChild has invalid default integer"
  assert TestFrameChild.bar == "", "TestFrameChild has invalid default string"
  assert TestFrameChild.baz == False, "TestFrameChild has invalid default boolean"
  
  test = TestFrame()
  assert test.foo == 0, "Integer field has invalid default value"
  
  test.foo = 12
  assert test.foo == 12, "Integer field cannot set value properly"
  assert test._pack() == struct.pack("i", 12), "Digest gives invalid value"

  test.foo = 13
  assert test._pack() ==  struct.pack("i", 13), "Digest gives invalid value"
  
  test2 = TestFrame()._unpack(test._pack())
  assert test2.foo == 13, "Fed value is invalid"
  assert test2._pack() == struct.pack("i", 13), "Digest gives invalid value"
  
  assert TestFrameChild()._pack() == struct.pack("i2ss", 0, "", Boolean.FALSE), "TestFrameChild does not digest properly"
  
  override_frame = TestFrameChild(foo=42)
  #assert override_frame._tainted == True, "Frame should initalize as updated"

  base_frame = TestFrame()._unpack(override_frame._pack())
  assert base_frame.foo == 42, "Parent failed to read values from child"
  #assert override_frame._tainted == False, "Frame should be set as not updated when digested"
  
  override_frame.baz = True
  #assert override_frame._tainted == True, "Frame should be set as updated when any value has been changed"
  assert override_frame.baz == True, "boolean balue baz should have been set to True"
  
  #retry same tests
  base_frame = TestFrame()._unpack(override_frame._pack())
  assert base_frame.foo == 42, "Parent failed to read values from child"
  
  base_frame = TestFrame()._unpack(override_frame._pack())
  assert base_frame.foo == 42, "Parent failed to read values from child"



