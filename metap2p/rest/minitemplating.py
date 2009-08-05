# -*- encoding: utf-8 -*-

import cStringIO

def safe_attribute(s, encoding):
  if isinstance(s, str):
    return s.replace("\"", "\\\"")
  elif isinstance(s, unicode):
    return s.encode(encoding).replace("\"", "\\\"")

class Base:
  standalone = False
  tag = None
  cdata = False

  def __init__(self, **kw):
    self.children = list();
    self.attributes = kw
    self.cd = ""
    
    if 'encoding' in kw:
      self.encoding = kw.pop('encoding')
    else:
      self.encoding = 'utf-8'
  
  def __getitem__(self, it):
    if isinstance(it, list) or isinstance(it, tuple):
      for i in it:
        self.__getitem__(i)
      return self
    
    if isinstance(it, str):
      self.children.append(cdata(it))
    elif isinstance(it, unicode):
      self.children.append(cdata(it))
    elif isinstance(it, int) or isinstance(it, float):
      self.children.append(cdata(str(it)))
    elif isinstance(it, Base):
      self.children.append(it)
    else:
      self.children.append(cdata("<BadBlock>"))
    
    return self
  
  def __str__(self, sw=None, encoding=None):
    called = False
    
    if sw is None:
      sw = cStringIO.StringIO();
      called = True

    if encoding is None:
      encoding = self.encoding
    
    if self.cdata:
      sw.write(self.cd.encode(encoding))
    else:
      if not self.tag:
        sw.write("")
      else:
        if self.standalone:
          sw.write("<%s />"%(self.tag))
          if len(self.attributes) == 0:
            sw.write("<%s />"%(self.tag))
          else:
            sw.write("<%s"%(self.tag))
            for k in self.attributes:
              sw.write(" %s=\"%s\""%(k.strip("_"), safe_attribute(self.attributes[k], encoding)))
            sw.write("/>")
        else:
          if len(self.attributes) == 0:
            sw.write("<%s>"%(self.tag))
          else:
            sw.write("<%s"%(self.tag))
            for k in self.attributes:
              sw.write(" %s=\"%s\""%(k.strip("_"), safe_attribute(self.attributes[k], encoding)))
            sw.write(">")
            
          for child in self.children:
            child.__str__(sw, encoding)
          sw.write("</%s>"%(self.tag))
    
    if not called:
      return 
    
    return sw.getvalue();

class cdata(Base):
  cdata = True
  def __init__(self, cd):
    self.cd = cd

class html(Base):
  tag = "html"

class head(Base):
  tag = "head"

class body(Base):
  tag = "body"

class div(Base):
  tag = "div"

class script(Base):
  tag = "script"

class a(Base):
  tag = "a"

class title(Base):
  tag = "title"

class ul(Base):
  tag = "ul"

class li(Base):
  tag = "li"

class ol(Base):
  tag = "ol"

class link(Base):
  standalone = True
  tag = "link"

class h1(Base):
  tag = "h1"

class h2(Base):
  tag = "h2"

class h3(Base):
  tag = "h3"

class h4(Base):
  tag = "h4"

class h5(Base):
  tag = "h5"

class h6(Base):
  tag = "h6"

class p(Base):
  tag = "p"

class span(Base):
  tag = "span"

def link_to(href, **kw):
  if 'href' in kw:
    kw.pop('href')
  
  kw['href'] = href
  return a(**kw)

def link_to_css(path, **kw):
  kw['rel'] = "stylesheet"
  kw['type'] = "text/css"
  kw['href'] = path
  
  return link(**kw)

def link_to_javascript(path, **kw):
  kw['src'] = path
  kw['type'] = "text/javascript"

  return script(**kw)

def ifelse(st, t, f):
  if st:
    return t
  else:
    return f

if __name__ == "__main__":
  hh = html()[
    head()[
      script(src="/public/javascripts/master.js")
    ],
    body()[
      div(id='heading')["Test"],
      div(_class="strong test")["Test"],
      a(href=u"google\"\".se [';åäö"),
      link_to("http://www.google.se", _class="mylink")
    ]
  ]
  
  print str(hh)
