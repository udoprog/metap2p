import routes

def setup_routes(m):
  m.connect('/peers', controller="peers", action="index", conditions=dict(method=['GET']))
  m.connect('/peers/:peer_uri', controller="peers", action="show", conditions=dict(method=['GET']))
  return m
