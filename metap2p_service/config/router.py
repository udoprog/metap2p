import routes

def setup_router(m):
  m.connect('/', controller="base", action="index", conditions=dict(method=['GET']))
  m.connect('peers', '/peers', controller="peers", action="index", conditions=dict(method=['GET']))
  m.connect('show_peer', '/peers/:peer_uri', controller="peers", action="show", conditions=dict(method=['GET']))
  return m