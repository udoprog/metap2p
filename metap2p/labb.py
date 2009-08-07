
class SessionFrame(Frame):
  receiver = Field("i")
  type = Field("i", default=0)
  size = Field("i")
  
  def _create_(self):
    self.size = self._size_();

def TestChild(SessionFrame):
  type = Field(default=0x0004)

#print repr(ChildChild()._feed_().test)
