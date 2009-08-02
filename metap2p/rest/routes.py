from routes import Mapper

def setup_routes(self):
  m = Mapper()
  m.match('')
  return m
