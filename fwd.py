""" App"""

from gevent import monkey
monkey.patch_all()
from gevent_psycopg2 import monkey_patch
monkey_patch()

import weakref
import time
import itertools
import logging
import collections
import simplejson as json
from datetime import datetime, timedelta

from flask import Flask, render_template, request, abort
from gevent import pool, spawn
from gevent.pywsgi import WSGIServer
from gevent.queue import Queue, PriorityQueue
from geventwebsocket.handler import WebSocketHandler
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from werkzeug.serving import run_with_reloader

import facebook
import settings

__all__ = ("app", "main")

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("fw")
app = Flask(__name__)
app.config.from_object("settings")
fb = facebook.API(settings.FB_APP_ID, settings.FB_SECRET)

User = collections.namedtuple("User", ["uid", "access_token", "uname"])
Listen = collections.namedtuple("Listen", ["lid", "uid", "sid", "ts"])
Song = collections.namedtuple(
    "Song",
    ["sid", "title", "artist_name", "site_name"])

class DB(object):

    def __init__(self):
        self.engine = create_engine(
            settings.DATABASE_URI, pool_size=10, max_overflow=20,
            pool_timeout=60, echo_pool=True)

    def connect(self):
        return self.engine.connect()

    def friends(self, uid):
        with self.connect() as c:
            return [User(row[0], None, row[1]) for row
                    in c.execute("select fid, uname from fw.f where uid = %s", uid)]

    def store_friends(self, uid, friends):
        with self.connect() as c:
            with c.begin() as t:
                c.execute(
                    "insert into fw.f (uid, fid, uname) values (%s, %s, %s)",
                    [(uid, f.uid, f.uname) for f in friends])

    def match_song(self, sid):
        try:
            with self.connect() as c:
                return c.execute("select * from fw.match_song(%s)", sid).first()
        except IntegrityError:
            pass

    def has_song(self, sid):
        with self.connect() as c:
            return (c
                .execute("select true from fw.s where sid = %s", sid)
                .scalar())

    def store_song(self, song):
        try:
            with self.connect() as c:
                with c.begin() as t:
                    c.execute("""
                        insert into fw.s (sid, title, artist_name, site_name)
                        select q.* from (select
                            %s::text as sid,
                            %s::text as title,
                            %s::text as artist_name,
                            %s::text as site_name) q
                        left join fw.s using(sid)
                        where s.sid is null""",
                        song.sid, song.title, song.artist_name, song.site_name)
        except IntegrityError:
            pass

    def last_listen(self, uid):
        with self.connect() as c:
            return (c
                .execute("select max(ts), max(cts) from fw.l where uid = %s", uid)
                .first())

    def update_cts(self, uid):
        with self.connect() as c:
            with c.begin() as t:
                c.execute("update fw.l set cts = now() where uid = %s", uid)

    def store_listen(self, *listens):
        with self.connect() as c:
            with c.begin() as t:
                for listen in listens:
                    c.execute("""
                        insert into fw.l (lid, uid, sid, ts, cts)
                        select q.* from (select
                            %s::text as lid,
                            %s::text as uid,
                            %s::text as sid,
                            %s::timestamp as ts,
                            %s::timestamp as cts) q left join fw.l using (lid) where
                        l.lid is null""",
                        listen.lid, listen.uid, listen.sid, listen.ts,
                        datetime.now())

    def listens(self, uid, limit=1):
        with self.connect() as c:
            return [Listen(**r) for r
                in c.execute("""
                select lid, uid, sid, ts from fw.l order by ts desc limit %s""",
                limit)]

@app.route("/wave")
def wave():
    if not "wsgi.websocket" in request.environ:
        return abort(400)
    if not "userId" in request.args or not "accessToken" in request.args:
        return abort(400)
    print "HERE"
    u = User(request.args["userId"], request.args["accessToken"], None)
    ws = request.environ["wsgi.websocket"]
    db = DB()
    for listen in db.listens(u.uid, 100):
        if not db.has_song(listen.sid):
            continue
        t = db.match_song(listen.sid)
        if t:
            ws.send(json.dumps({
                "trackId": t.ztid,
                "userId": u.uid,
                "userName": "Andrey Popp",
                "src": t.surl,
                "songName": t.title,
                "artistName": t.artist_name,
                "artistPhoto": t.aimgurl,
                "coverSrc": t.rimgurl,
                "timestamp": listen.ts.strftime("%Y-%m-%dT%H:%M:%S+0000")
                }))

def main():
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(("0.0.0.0", 5001), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

if __name__ == "__main__":
    main()
