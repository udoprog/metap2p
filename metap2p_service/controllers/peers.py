from metap2p_service import Controller
from routes.util import url_for, redirect_to
from metap2p.rest import minitemplating as T

class Peers(Controller):
  def layout(self, c):
    return T.html()[
      T.head()[
        T.title()["MetaP2P Control Panel (%s)"%(self.server.uuid.hex)],
        T.link_to_css("/public/css/master.css"),
        T.link_to_javascript("/public/js/master.js"),
        T.meta({'http-equiv': "content-type", 'content': "text/html; charset=utf-8"})
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
            T.li()[T.link_to(url_for('peers_broadcast'))["Broadcast"]],
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
          T.span(_class="conv")[repr(peer.session)],
          T.div(_class="clear")
        ])
      else:
        peerlist.append(T.div(_class="row")[
          T.span(_class="name")[T.link_to(url_for(action="show", peer_uri=peer.uri))[peer.uri]],
          "not connected",
          T.div(_class="clear")
        ])
    
    return [T.div(_class="mininav")[T.span(_class='item')[T.link_to(url_for('new_peer'))["new"]]],
            T.div(id="peers")[peerlist]]
  
  def show(self, peer_uri):
    import urllib
    
    self.path=["Peers", peer_uri]

    peer = self.__find_peer(peer_uri)
    if not peer:
      return T.h1("Not Found")
    
    messages = list()

    for message in peer.queue:
      messages.append(
        T.div()[
          T.p()[message.data]
        ]
      )
    
    return [
      T.h1()[peer_uri],
      T.p()["This is a paragraph"],
      T.p()["messages received:"],
      T.div()[messages]
    ]

  def new(self):
    self.path = ["Peers", "new"]
    
    return [
      T.form(action=url_for('peers'), method="POST")[
        T.input(name="peer_uri", type="text"),
        T.input(name="new_peer", type="submit", value="New Peer")
      ]
    ]
  
  def create(self, peer_uri):
    self.server.addPeer(peer_uri)
    redirect_to(url_for(action="index"))

  def broadcast(self):
    self.path = ["Peers", "Broadcast"]
    
    return [
      T.h1()["Broadcast to All Peers"],
      T.form(action=url_for('peers_broadcast'), method="POST")[
        T.text_area(name="broadcast_message", cols="60", rows="20"),
        T.br(),
        T.input(name="submit_broadcast_message", type="submit", value="Send Broadcast")
      ]
    ]
  
  def send_broadcast(self, broadcast_message):
    for peer in self.server.peers:
      if peer.connected:
        peer.send_message(broadcast_message)
    
    return redirect_to(url_for('peers'))
  
  def __find_peer(self, peer_uri):
    for peer in self.server.peers:
      if peer.uri == peer_uri:
        return peer
    return None
