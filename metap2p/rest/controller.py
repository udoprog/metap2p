from metap2p.rest.errors import NotFound

import inspect
import copy

__controllers__ = dict()

class Controller(object):
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
    
    for k in result:
      if not k in action_insp.args:
        raise NotAcceptable(' '.join(["Parameters invalid for action", k, "not in", action_insp.args]))
    
    skipped_first = False
    for k in action_insp.args:
      if not skipped_first:
        skipped_first = True
        continue
      
      if not k in result:
        raise NotAcceptable(' '.join(["Parameters invalid for action", k, "not in PARAMS", result]))
    
    self.params = params
    ret = action_def(**result)
    # action should only return string, catch all interesting possibilities here
    
    if isinstance(ret, list) or isinstance(ret, tuple):
      ret = ''.join(ret)

    if isinstance(ret, unicode):
      return ret.encode('utf-8')
    
    if not isinstance(ret, str):
      resource.debug("Return value is not string, coping")
      return str(ret)
    
    return ret

def get_controller(resource, result):
  if result is None:
    resource.debug("No match in router")
    return None
  
  controller = result.pop('controller')
  
  if controller in __controllers__:
    return __controllers__[controller]()
  else:
    return None
