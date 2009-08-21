from metap2p.rest.controller import Controller

import config.router

#load all available controllers here
# metaclassing with metap2p.rest.controller.Controller will register them.
from metap2p_service.controllers import base
from metap2p_service.controllers import peers

def setup_router(mapper):
  config.router.setup_router(mapper)
