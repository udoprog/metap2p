import metap2p.rest.controller as controller
from metap2p.rest.errors import NotFound, NotAcceptable

from twisted.web import resource, static, server as twisted_server

import routes

import copy
import urllib

class HttpDynamicResource(resource.Resource):
  isLeaf = True

  def __init__(self, service):
    self.service = service
    self.server = self.service.server
    
    self.encoding = self.service.encoding
    
    self.router = routes.Mapper()
    self.server.metap2p_app.setup_router(self.router)
  
  def debug(self, *msg):
    self.service.debug(*msg)
  
  def render(self, request):
    request.setHeader("content-type", "text/html; charset=%s"%(self.encoding))
    
    self.router.environ = {
      'REQUEST_METHOD': request.method
    }
    
    self.router.environ.update(request.getAllHeaders())

    #self.debug(dir(request))
    path = urllib.unquote(request.path)#.decode('utf-8')
    result = self.router.match(path)
    
    if not result:
      request.code = 404
      request.code_message = "Not Found"
      return ''
    
    params = dict()
    params.update(request.args)
    
    for k in params:
      rebuild = list()
      
      param = params[k]
  
      if not isinstance(param, list):
        param = [param]
      
      for i in param:
        if request.method in ["GET"]:
          i = urllib.unquote(i)
        
        try:
          val = i.decode(self.encoding)
        except:
          val = u""
        
        rebuild.append(val)
      
      if len(rebuild) == 1:
        params[k] = rebuild[0]
      else:
        params[k] = rebuild
    
    params.update(result)
    
    config = routes.request_config();
    config.mapper = self.router
    config.mapper_dict = result
    config.host = self.service.host
    config.protocol = self.service.protocol
    config.redirect = request.redirect
    
    self.debug("Handling:", request.method, result)
    
    #return repr(request.args)
    
    #must copy params since one of the copies are used internally in routes.
    action_params = copy.copy(result)
    
    controller_inst = controller.get_controller(self, action_params)
    
    try:
      if not controller_inst:
        raise NotFound("No such controller")

      args = copy.copy(request.args)
      
      #unquote args no GET since otherwise mommy is sad
      
      return controller_inst._handle_request(self, params)
    except NotFound, e:
      self.debug(e)
      request.code = 404
      request.code_message = "Not Found"
    except NotAcceptable, e:
      self.debug(e)
      request.code = 406
      request.code_message = "Not Acceptable"
    #except Exception, e:
    #  self.debug(e)
    #  request.code = 500
    #  request.code_message = "Internal Server Error"
    
    return ''

class HTTPServerResource(resource.Resource):
  #isLeaf = True
  
  def __init__(self, service):
    self.server = service.server
    self.service = service
    
    resource.Resource.__init__(self)
    
    if self.service.public:
      self.putChild(self.service.public,\
        static.File(self.server.get_root(
          self.service.path,
          self.service.public)))
  
  def getChild(self, path, request):
    if path in self.children:
      return self.children[path]
    
    return HttpDynamicResource(self.service)

class Service:
  encoding = "utf-8"

  def __init__(self, server, host, port, path=".", public=None, protocol="http"):
    self.server = server
    
    self.path = path
    self.host = host
    self.port = port
    self.public = public
    self.path = path
    self.protocol = protocol
    
    self.root_resource = HTTPServerResource(self);
    
    self.deferrer = twisted_server.Site(self.root_resource)
    
    self.uri = "%s://%s:%d"%(self.protocol, self.host, self.port)
  
  def listen(self, reactor):
    reactor.listenTCP(self.port, self.deferrer, interface = self.host)
    self.debug("Listening at", self.uri)
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s R %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))
