""" App"""

from gevent import monkey
monkey.patch_all()
from gevent_psycopg2 import monkey_patch
monkey_patch()

import collections

from flask import Flask, render_template, request, abort
from gevent import pool
from gevent.pywsgi import WSGIServer
from gevent.queue import Queue
from geventwebsocket.handler import WebSocketHandler
from sqlalchemy import create_engine
import werkzeug.serving

import facebook
import settings

__all__ = ("app", "main")

app = Flask(__name__)
fb = facebook.API(settings.FB_APP_ID, settings.FB_SECRET)
db = create_engine(settings.DATABASE_URI)

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
        ufinfo = unpaginate(fb.me.using(u.access_token).friends.get)
        raise NotImplementedError()
    return results

def pmap(func, lst):
    l = len(lst)
    w = pool.Pool(size=l)
    return w.map(func, lst)

def unpaginate(fetch, pages=3):
    def worker((offset, limit)):
        r = fetch(offset=offset, limit=limit)
        return r.get("data", [])
    return [x
        for y in pmap(worker, [(i * 100, 100) for i in range(pages)])
        for x in y]

@werkzeug.serving.run_with_reloader
def main():
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(("", 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

if __name__ == "__main__":
    main()

