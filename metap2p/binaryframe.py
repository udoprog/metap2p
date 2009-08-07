import struct

class ImmutableDict(dict):
  def __setitem__(self, key, value):
    raise ValueError("Cannot set value in an immutable dict")

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
    
    self._instance = Field.__instance_counter
    Field.__instance_counter += 1
    
    self.default = kw.get('default')
  
  def __set__(self, instance, val):
    if instance is None:
      raise ValueError("Cannot set values on metaclasses")
    
    instance._updated = True
    instance.__store__[self.__name__] = val
  
  def __get__(self, instance, owner):
    if instance is None:
      #class access
      return self.default
    
    # instsance access
    return instance.__store__[self.__name__]
  
  def __cmp__(self, other):
    return cmp(self._instance, other._instance)
  
  def __str__(self):
    return "<Field name='%s'>"%(self.__name__)
  
  def __getstval__(self, instance, owner):
    return Field.__get__(self, instance, owner)

class Integer(Field):
  def __init__(self, **kw):
    self.default = kw.pop('default', 0)
    
    try:
      self.default = int(self.default)
    except ValueError, e:
      raise ValueError("Default value is not a valid integer")
    
    Field.__init__(self, "i", default=self.default)
  
  def __set__(self, obj, val):
    try:
      val = int(val)
    except ValueError, e:
      raise ValueError("Default value is not a valid integer")
    
    return Field.__set__(self, obj, val)

class String(Field):
  def __init__(self, length, **kw):
    self.default = kw.pop('default', "")
    
    try:
      self.default = str(self.default)
    except ValueError, e:
      raise ValueError("Default value is not a valid string")
    
    Field.__init__(self, "%ds"%(length), default=self.default)
  
  def __set__(self, obj, val):
    try:
      val = str(val)
    except ValueError, e:
      raise ValueError("Default value is not a valid string")
    
    return Field.__set__(self, obj, val)

class Boolean(Field):
  TRUE = chr(1)
  FALSE = chr(0)
  
  def __init__(self, **kw):
    self.default = kw.pop('default', 0)
    
    if self.default:
      self.default = self.TRUE
    else:
      self.default = self.FALSE
    
    Field.__init__(self, "s", default=self.default)
  
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
  
  class __metaclass__(type):
    """
    This is called when building the class object singleton for all subclasses.
    """
    def __init__(cls, name, bases, dict):
      type.__init__(cls, name, bases, dict)
      cls.setup_frame()
  
  def __init__(self, **kw):
    self.__store__ = dict()
    
    # Sets all the fields to their default values
    for k in self._fields:
      field = self._fields[k]
      self.__store__[k] = field.default
    
    for k in kw:
      setattr(self, k, kw[k])
    
    self._updated = True
    self.__old_digest = ""
    
    self._create()
  
  def _pack(self):
    if not self._updated:
      return self.__old_digest
    
    self._updated = False
    
    for field in self.__class__.__ordered_fields:
      if field.__getstval__(self, None) is None:
        raise Exception("%s: Field '%s' is None"%(repr(self), field.__name__))
    
    # hook to do stuff before tha value is packed,
    # like digest all fields in a hash.
    self._beforepack()
    
    field_values = map(lambda field: field.__getstval__(self, None), self.__class__.__ordered_fields)
    self.__old_digest = struct.pack(self.__class__.__frame, *field_values)
    return self.__old_digest
  
  def _unpack(self, data):
    if len(data) < self._size():
      raise Exception("input not long enough")
    
    if len(data) != self._size():
      data = buffer(data, 0, self._size())
    
    for field, arg in zip(self.__class__.__ordered_fields, struct.unpack(self.__class__.__frame, data)):
      field.__set__(self, arg)
    
    return self
  
  def _digest(self, *exceptions):
    import hashlib

    m = hashlib.new('md5')
    
    for field in self.__ordered_fields:
      if field.__name__ in exceptions:
        continue

      m.update(struct.pack(field.struct, field.__getstval__(self, None)))
    
    return m.digest()
  
  def _size(self):
    return self.__class__.__size
  
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
    
    for f in cls.__dict__:
      attr = cls.__dict__[f]
      if isinstance(attr, Field):
        attr.__name__ = f
        fields[f] = attr
    
    for super in cls.__bases__:
      for f in super.__dict__:
        attr = super.__dict__[f]
        
        if isinstance(attr, Field):
          if f not in fields:
            fields[f] = attr
            continue
          
          field = fields[f]
          
          if field._inherit_struct:
            field.struct = attr.struct
            field._inherit_struct = False
            field._instance = attr._instance
    
    cls.__ordered_fields = fields.values()
    cls.__ordered_fields.sort()
    
    cls._fields = ImmutableDict(**fields)
    
    cls.__frame = ''.join(map(lambda f: f.struct, cls.__ordered_fields))
    cls.__size = struct.calcsize(cls.__frame)

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
    pass
  
  print "Testing string..."
  test_strings();
  print "                 OK"
  
  print "Testing booleans..."
  test_booleans();
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
  assert override_frame._updated == True, "Frame should initalize as updated"

  base_frame = TestFrame()._unpack(override_frame._pack())
  assert base_frame.foo == 42, "Parent failed to read values from child"
  assert override_frame._updated == False, "Frame should be set as not updated when digested"
  
  override_frame.baz = True
  assert override_frame._updated == True, "Frame should be set as updated when any value has been changed"
  assert override_frame.baz == True, "boolean balue baz should have been set to True"
  
  #retry same tests
  base_frame = TestFrame()._unpack(override_frame._pack())
  assert base_frame.foo == 42, "Parent failed to read values from child"
  
  base_frame = TestFrame()._unpack(override_frame._pack())
  assert base_frame.foo == 42, "Parent failed to read values from child"
  
  class DigestTest(Frame):
    digest = String(16)
    size = Integer()
    message = String(512)
    
    def _beforepack(self):
      self.size = self._size()
      self.digest = self._digest('digest')

    def valid(self):
      return self.digest == self._digest('digest')
  
  message1 = DigestTest(message="This is cool shit")
  message2 = DigestTest(message="This is cool shit")
  message3 = DigestTest(message="This is different shit")
  
  assert message1._pack() == message2._pack()
  assert message1._pack() != message3._pack()
  assert message2._pack() != message3._pack()
  
  assert message1.digest == message2.digest
  assert message1.digest != message3.digest
  assert message2.digest != message3.digest

  recv_message = DigestTest()
  recv_message._unpack(message1._pack())
  assert recv_message.valid() == True, "Message recieved is not valid"
  
  recv_message.message = "Die motherfucker"
  assert recv_message.valid() == False, "Message recieved is valid"
