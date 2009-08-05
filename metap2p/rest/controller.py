from metap2p.rest.errors import NotFound
from metap2p.rest import minitemplating as T

import inspect
import copy

__controllers__ = dict()

class Controller(object):
  layout = None
  
  class __metaclass__(type):
    def __init__(cls, name, bases, dict):
      if name != 'Controller':
        __controllers__[name.lower()] = cls
      
      type.__init__(cls, name, bases, dict)

  def _handle_request(self, resource, result, params):
    self.server = resource.server
    action = result.pop('action')

    if hasattr(self, action):
      action_def = getattr(self, action)
    else:
      raise NotFound("Action not found")
    
    # make sure action definition matches request match
    resource.debug(params)
    action_insp = inspect.getargspec(action_def)
    
    # 2.6 has named typle with attribute 'args'
    # 2.5 is just a regular tuple.
    action_insp_args = action_insp[0]
    
    for k in result:
      if not k in action_insp_args:
        raise NotAcceptable(' '.join(["Parameters invalid for action", k, "not in", action_insp_args]))
    
    skipped_first = False
    for k in action_insp_args:
      if not skipped_first:
        skipped_first = True
        continue
      
      if not k in result:
        raise NotAcceptable(' '.join(["Parameters invalid for action", k, "not in PARAMS", result]))
    
    self.params = params
    ret = action_def(**result)
    # action should only return string, catch all interesting possibilities here
    
    if self.layout:
      if isinstance(ret, unicode):
        return self.layout(ret.encode('utf-8'))
      
      if isinstance(ret, str):
        resource.debug("Return value is not string, coping")
        return self.layout(str(ret))
      
      return str(self.layout(ret))
    
    if isinstance(ret, list) or isinstance(ret, tuple):
      ret = ''.join(ret)
    
    if ret is None:
      ret = ""

    if isinstance(ret, unicode):
      return ret.encode('utf-8')
    
    if isinstance(ret, str):
      return ret
    
    return str(ret)
    
def get_controller(resource, result):
  if result is None:
    resource.debug("No match in router")
    return None
  
  controller = result.pop('controller')
  
  if controller in __controllers__:
    return __controllers__[controller]()
  else:
    return None
