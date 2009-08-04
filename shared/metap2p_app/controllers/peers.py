from metap2p_app import Controller
from routes.util import url_for, redirect_to
from metap2p.rest import minitemplating as T

def template(c):
  return T.html()[
    T.head()[
      T.title()["MetaP2P Control Panel"],
      T.link_to_css("/public/css/master.css"),
      T.link_to_javascript("/public/js/master.js")
    ],
    T.body()[
      T.div(id="header")[
        "MetaP2P Control Panel"
      ],
      T.div(id="navigation")[
        "Navigation"
      ],
      T.div()[
        c
      ]
    ]
  ]

class Peers(Controller):
  def index(self):
    return template(T.ul(id="frame")[
      map(
        lambda peer: T.li()[
          T.link_to(url_for(action="show", peer_uri=peer.uri))[peer.uri]
        ],
        self.server.peers),
      T.div()["test"]
    ])
  
  def show(self, peer_uri):
    import urllib
    
    content = [
      T.h1()[peer_uri]
    ]
    
    return template(content)
