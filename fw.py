""" App"""

from gevent import monkey
monkey.patch_all()

import collections

from flask import Flask, render_template, request, abort
from gevent.pywsgi import WSGIServer
from gevent.queue import Queue
from geventwebsocket.handler import WebSocketHandler
import werkzeug.serving

import facebook
import settings

__all__ = ("app", "main")

app = Flask(__name__)
fb = facebook.API(settings.FB_APP_ID, settings.FB_SECRET)

User = collections.namedtuple("User", ["id", "access_token"])

@app.route("/")
def welcome():
    return render_template("welcome.html", settings=settings)

@app.route("/wave")
def wave():
    if not "wsgi.websocket" in request.environ:
        return abort(400)
    if not "id" in request.args or not "access_token" in request.args:
        return abort(400)
    u = User(request.args["id"], request.args["access_token"])
    ws = request.environ["wsgi.websocket"]
    for item in wave_for(u):
        ws.send(item)

def wave_for(u):
    results = Queue()
    def worker():
        uinfo = fb.me.using(u.access_token).get()
        ufinfo = fb.me.using(u.access_token).friends.get()
        raise NotImplementedError()
    return results

@werkzeug.serving.run_with_reloader
def main():
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(("", 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

if __name__ == "__main__":
    main()

