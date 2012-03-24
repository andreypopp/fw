""" App"""

from gevent import monkey
monkey.patch_all()
from gevent_psycopg2 import monkey_patch
monkey_patch()

import collections

from flask import Flask, render_template, request, abort
from gevent import pool, spawn
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
engine = create_engine(settings.DATABASE_URI)

User = collections.namedtuple("User", ["id", "access_token"])

class DB(object):

    def __init__(self):
        self.c = engine.connect()

    def friends(self, uid):
        return list(self.c.execute("select fid from fw.f where uid = %", uid))

    def store_friends(self, uid, fids):
        self.c.execute(
            "insert into fw.f (uid, fid) values (%s, %s)",
            [(uid, fid) for fid in fids])

    def __getattr__(self, name):
        return getattr(self.c, name)

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

def wave_for(u, result=None):
    if results is None:
        results = Queue()
    def listens():
        db = DB()

        # friends
        friends = db.friends(u.id)
        if not friends:
            friends = [User(x["id"], u.access_token) for x
                in unpage(fb.me.using(u.access_token).friends.get)]
            db.store_friends(u.id, [f.id for f in friends])
            db.commit()

        # friend listens
        def user_listens(u):
            db = DB()
            while True:
                listens = fb[u.id]["music.listens"].using(u.token).get()
        for f in friends:
            spawn(user_listens, f)

    spawn(listens) # XXX: Leak here!
    return results

def last_end_time(listens):
    return max(fb_datetime(v["end_time"]) for v in listens)

def fb_datetime(v):
    return datetime.strptime("%Y-%m-%dT%H:%M:%S+0000")

def pmap(func, lst):
    l = len(lst)
    w = pool.Pool(size=l)
    return w.map(func, lst)

def unpage(fetch, pages=3):
    def worker((offset, limit)):
        r = fetch(offset=offset, limit=limit)
        return r.get("data", [])
    return [x
        for y in pmap(worker, [(i * 100, 100) for i in range(pages)])
        for x in y]

def jsonpath(p):
    def w(k):
        if callable(k):
            return k(p)
        for k in k.split("."):
            try:
                p = p[k]
            except KeyError:
                return None
        return p
    return w

@werkzeug.serving.run_with_reloader
def main():
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(("", 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

if __name__ == "__main__":
    main()

