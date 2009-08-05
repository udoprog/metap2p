import metap2p.rest.controller as controller
from metap2p.rest.errors import NotFound, NotAcceptable

from twisted.web import resource
from twisted.web import static

import routes

import copy
import urllib

class DynamicResource(resource.Resource):
  encoding = 'UTF-8'
  
  isLeaf = True

  def __init__(self, service):
    self.service = service
    self.server = self.service.server
    
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
    config.protocol = "http"
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

class ServiceResource(resource.Resource):
  #isLeaf = True
  
  def __init__(self, server, host, port):
    self.server = server
    self.host = host
    self.port = port
    self.uri = "%s:%d"%(self.host, self.port)
    resource.Resource.__init__(self)
    
    self.putChild(self.server.servicepublic, static.File(self.server.get_root(self.server.servicepath, self.server.servicepublic)))
  
  def getChild(self, path, request):
    if path in self.children:
      return self.children[path]
    
    return DynamicResource(self)
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s R %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))
