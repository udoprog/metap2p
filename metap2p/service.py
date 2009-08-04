import metap2p.rest.controller as controller
from metap2p.rest.errors import NotFound, NotAcceptable

from twisted.web import resource
from twisted.web import static

import routes

import copy

class ServiceResource(resource.Resource):
  #isLeaf = True
  
  def __init__(self, server, host, port):
    self.server = server
    self.router = routes.Mapper()
    self.server.metap2p_app.setup_router(self.router)
    self.host = host
    self.port = port
    self.uri = "%s:%d"%(self.host, self.port)
    resource.Resource.__init__(self)
    
    self.putChild('public', static.File(self.server.get_root("shared", "public")))
  
  def getChild(self, path, request):
    if path in self.children:
      return self.children[path]
    
    self.isLeaf = True
    return self
  
  def debug(self, *msg):
    import time
    now = time.strftime("%H:%M:%S")
    print "%s R %-20s - %s"%(now, self.uri, ' '.join(map(lambda s: str(s), msg)))
  
  def render(self, request):
    self.router.environ = {
      'REQUEST_METHOD': request.method
    }
    
    self.router.environ.update(request.getAllHeaders())

    #self.debug(dir(request))
    
    result = self.router.match(request.path)
    
    config = routes.request_config();
    config.mapper = self.router
    config.mapper_dict = result
    config.host = self.host
    config.protocol = "http"
    config.redirect = request.redirect
    
    self.debug("Handling:", request.method, result)

    #must copy params since one of the copies are used internally in routes.
    action_params = copy.copy(result)
    
    controller_inst = controller.get_controller(self, action_params)
    
    try:
      if not controller_inst:
        raise NotFound("No such controller")
      
      import urllib

      args = copy.copy(request.args)
      
      for k in args:
        args[k] = urllib.unquote(args[k])
      
      return controller_inst._handle_request(self, action_params, args)
    except NotFound, e:
      self.debug(e)
      request.code = 404
      request.code_message = "Not Found"
    except NotAcceptable, e:
      self.debug(e)
      request.code = 406
      request.code_message = "Not Acceptable"
    except Exception, e:
      self.debug(e)
      request.code = 500
      request.code_message = "Internal Server Error"
    
    return ''
