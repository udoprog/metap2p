from metap2p_service import Controller
from routes.util import url_for, redirect_to

class Base(Controller):
  def index(self):
    redirect_to(url_for(controller="peers", action="index"))
