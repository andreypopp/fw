""" App"""

from gevent import monkey
monkey.patch_all()
from gevent_psycopg2 import monkey_patch
monkey_patch()

import collections
import simplejson as json

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

User = collections.namedtuple("User", ["uid", "access_token"])
Listen = collections.namedtuple("Listen", ["lid", "uid", "sid", "ts"])
Song = collections.namedtuple(
    "Song",
    ["sid", "title", "artist_name", "site_name"])

class DB(object):

    def __init__(self):
        self.c = engine.connect()

    def friends(self, uid):
        return list(self.c.execute("select fid from fw.f where uid = %s", uid))

    def store_friends(self, uid, fids):
        self.c.execute(
            "insert into fw.f (uid, fid) values (%s, %s)",
            [(uid, fid) for fid in fids])

    def match_song(self, sid):
        return self.c.execute("select * fw.match_song(%s)", sid).first()

    def has_song(self, sid):
        return (
            self.c.execute("select true from fw.s where sid = %s", sid)
            .scalar())

    def store_song(self, song):
        self.c.execute("""
            insert into fw.s (sid, title, artist_name, site_name)
            values(%s, %s, %s, %s)""",
            song.sid, song.title, song.artist_name, song.site_name)

    def last_listen(self, uid):
        return (self.c
            .execute("select max(ts) from fw.l where uid = %s", uid)
            .first())

    def store_listen(self, listen):
        self.c.execute("""
            insert into fw (lid, uid, sid, ts)
            values (%s, %s, %s, %s)""",
            listen.lid, listen.uid, listen.sid, listen.ts)

    def listens(self, uid, ts):
        for r in self.c.execute("select * from fw.l where ts >= %s", ts):
            yield Listen(**r)

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
        ws.send(json.dumps(item))

def wave_for(u, result=None):
    if results is None:
        results = Queue()
    def listens():
        db = DB()

        # friends
        friends = db.friends(u.uid)
        if not friends:
            friends = [User(x["id"], u.access_token) for x
                in unpage(fb.me.using(u.access_token).friends.get)]
            db.store_friends(u.uid, [f.uid for f in friends])
            db.commit()

        # friend listens
        def user_listens(u):
            db = DB()

            def listens_for(u, num=200):
                last_ts = db.last_listen(u.uid)
                for listen in unpage_seq(
                        fb[u.uid]["music.listens"].using(u.token).get,
                        num):
                    ts = fb_datetime(listen.get("end_time"))
                    if last_ts >= ts:
                        break
                    listen = Listen(
                        lid=listen.get("id"),
                        uid=u.uid,
                        sid=listen.get("song", {}).get("id"),
                        ts=ts)
                    db.store_listen(listen)
                    yield listen
                for listen in db.listens(u.uid, last_ts):
                    yield listen

            for listen in listens_for(u):
                if not has_song(listen.sid):
                    db.store_song(song(listen.sid, u.access_token))
                t = db.song(listen.sid)
                if t:
                    results.put({
                        "src": t.surl,
                        "songName": t.title,
                        "artistName": t.artist_name,
                        "artistPhoto": t.aimgurl,
                        "coverSrc": t.rimgurl
                        })

        for f in friends:
            spawn(user_listens, f)

    spawn(listens) # XXX: Leak here!
    return results

def song(sid, access_token):
    data = fb[sid].using(access_token).get()
    return Song(
        sid=sid,
        title=data.get("title"),
        artist_name=data.get("musician")[0].get("name"),
        site_name=data.get("site_name"))

def fb_datetime(v):
    return datetime.strptime("%Y-%m-%dT%H:%M:%S+0000", v) if v else None

def pmap(func, lst):
    l = len(lst)
    w = pool.Pool(size=l)
    return w.map(func, lst)

def unpage_par(fetch, pages=3):
    def worker((offset, limit)):
        r = fetch(offset=offset, limit=limit)
        return r.get("data", [])
    return [x
        for y in pmap(worker, [(i * 100, 100) for i in range(pages)])
        for x in y]

def unpage_seq(fetch, num=200):
    offset, limit = 0, 25
    while True:
        if offset > num:
            break
        data = fetch(offset=offset, limit=limit).get("data", [])
        if not data:
            break
        for item in data:
            yield item
        offset = offset + limit

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


def main():
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(("", 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

def shell():
    from facebook import shell
    shell((settings.FB_APP_ID, settings.FB_SECRET))

if __name__ == "__main__":
    werkzeug.serving.run_with_reloader(main)()

