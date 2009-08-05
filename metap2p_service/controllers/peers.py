from metap2p_service import Controller
from routes.util import url_for, redirect_to
from metap2p.rest import minitemplating as T

class Peers(Controller):
  def layout(self, c):
    return T.html()[
      T.head()[
        T.title()["MetaP2P Control Panel (%s)"%(self.server.uuid.hex)],
        T.link_to_css("/public/css/master.css"),
        T.link_to_javascript("/public/js/master.js")
      ],
      T.body()[
        T.div(id="heading")[
          T.span(_class="title")["MetaP2P Control Panel"],
          map(lambda element: [T.span(_class="sep")["&gt;"],
            T.span(_class="place")[element]], self.path)
        ],
        T.div(id="navigation")[
          T.ul()[
            T.li()[T.link_to(url_for('peers'))["Peers"]],
          ]
        ],
        T.div(id="content")[
          c
        ]
      ]
    ]
  
  def index(self):
    self.path=["Peers"]

    peerlist = list()

    peerlist.append(T.div(_class="row heading")[
      T.span(_class="name")["host"],
      T.span(_class="transmit")["tX (out)"],
      T.span(_class="receive")["rX (in)"],
      T.div(_class="clear")
      ])

    for peer in self.server.peers:
      if peer.connected:
        if peer.session.uuid:
          uuid = peer.session.uuid
        else:
          uuid = "<none>"

        peerlist.append(T.div(_class="row")[
          T.span(_class="name")[T.link_to(url_for(action="show", peer_uri=peer.uri))[peer.uri]],
          T.span(_class="transmit")[str(peer.session.tx)],
          T.span(_class="receive")[str(peer.session.rx)],
          T.span(_class="uuid")[uuid],
          T.div(_class="clear")
        ])
      else:
        peerlist.append(T.div(_class="row")[
          T.span(_class="name")[T.link_to(url_for(action="show", peer_uri=peer.uri))[peer.uri]],
          "not connected",
          T.div(_class="clear")
        ])
    
    return T.div(id="peers")[peerlist]
  
  def show(self, peer_uri):
    import urllib
    
    self.path=["Peers", peer_uri]
    return [
      T.h1()[peer_uri],
      T.p()["This is a paragraph"]
    ]
