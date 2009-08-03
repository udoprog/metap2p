from metap2p.rest.controller import Controller

from routes.util import url_for, redirect_to

class Peers(Controller):
  def index(self):
    res = ""

    res += "<ul>"
    for peer in self.server.peers:
      if peer.connected:
        res += "<li><a href='%s'>%s</a> <em>connected</em></li>"%(url_for(action='show', peer_uri=peer.uri), peer.uri)
      else:
        res += "<li><b>%s</b> <em>not connected</em></li>"%(peer.uri)
    res += "</ul>"
    
    return res

  def sshow(self, peer_uri):
    import urllib
    
    for peer in self.server.peers:
      if peer.uri == peer_uri:
        res = "<h1>%s</h1>"%(peer_uri)

        if peer.connected:
          res += "<p>received: %d bytes</p>"%(peer.session.rx)
          res += "<p>transmitted: %d bytes</p>"%(peer.session.tx)
        else:
          res += "<p>Not Connected</p>"
        
        return res

    return "<b>Not Found</b>"
