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
        with self.connect() as c:
            return c.execute("select * from fw.match_song(%s)", sid).first()

    def has_song(self, sid):
        with self.connect() as c:
            return (c
                .execute("select true from fw.s where sid = %s", sid)
                .scalar())

    def store_song(self, song):
        with self.connect() as c:
            with c.begin() as t:
                c.execute("""
                    insert into fw.s (sid, title, artist_name, site_name)
                    select q.* from (select %s::text sid, %s::text title,
                    %s::text artist_name, %s::text as site_name) q
                    left join fw.s using(sid) where s.sid is null""",
                    song.sid, song.title, song.artist_name, song.site_name)

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
                        select q.* from (
                            select %s::text lid, %s::text uid, %s::text sid,
                            %s::timestamp ts, %s::timestamp cts) q
                            left join fw.l using(lid) where l.lid is null""",
                        listen.lid, listen.uid, listen.sid, listen.ts,
                        datetime.utcnow())

    def listens(self, uid, ts):
        with self.connect() as c:
            return [Listen(**r) for r
                in c.execute("""
                    select lid, uid, sid, ts from fw.l
                    where uid = %s order by ts desc""", uid)]

    def has_listens(self, uid):
        with self.connect() as c:
            return c.execute("select true from fw.l where uid = %s limit 1",
                    uid).scalar()

@app.route("/wave")
def wave():
    if not "wsgi.websocket" in request.environ:
        return abort(400)
    if not "userId" in request.args or not "accessToken" in request.args:
        return abort(400)
    u = User(request.args["userId"], request.args["accessToken"], None)
    ws = request.environ["wsgi.websocket"]
    seen = []
    useen = []
    n = 0
    for _, item in wave_for(u):
        if item["trackId"] in seen:
            continue
        if item["userId"] in useen:
            continue
        n = n + 1
        if n > 6:
            time.sleep(5)
        ws.send(json.dumps(item))
        seen.append(item["trackId"])
        useen.append(item["userId"])
        seen = seen[-15:]
        useen = useen[-5:]

class UserTracker(object):

    spawn = spawn

    def __init__(self):
        self.users = {}
        self.db = DB()
        self.spawn(self.process)

    def subscribe(self, uid, access_token):
        results = PriorityQueue()
        seen, last, im, ts, subscribers = self.users.get(uid, (set(), None, True,
            datetime.utcnow(), []))
        subscribers.append((access_token, weakref.ref(results)))
        self.users[uid] = (seen, last, True, ts, subscribers)
        return results

    def notify(self, subscribers, listens):
        for access_token, ref in subscribers[:]:
            subscriber = ref()
            if not subscriber:
                subscribers.remove((access_token, ref))
                continue
            if listens:
                for listen in listens:
                    subscriber.put(listen)
        return bool(subscribers)

    def process(self):
        while True:
            time.sleep(2)
            log.debug("tick: %d users to process", len(self.users))
            now = datetime.utcnow()
            access_token = None
            for uid, (seen, last, im, ts, subscribers) in self.users.items():
                if not self.notify(subscribers, []):
                    self.users.pop(uid)
                    continue
                access_token = subscribers[0][0]
                if im or now - ts > timedelta(seconds=3):
                    log.debug("fetching")
                    listens = [
                        Listen(
                            lid=item.get("id"),
                            uid=uid,
                            sid=item.get("data", {}).get("song", {}).get("id"),
                            ts=fb_datetime(item.get("end_time")))
                        for item in (fb[uid]["music.listens"]
                                .using(access_token)
                                .get(limit=30)
                                .get("data", []))]
                    if not listens:
                        self.users[uid] = (seen, last, False, ts, subscribers)
                        continue
                    newlast = listens[-1].ts
                    if last and newlast <= last:
                        self.users[uid] = (seen, last, False, now, subscribers)
                        continue
                    print len(listens)
                    print last
                    listens = [l for l in listens if l.lid not in seen]
                    listens = reversed(sorted(listens, key=lambda l: l.ts))
                    for listen in listens:
                        seen.add(listen)
                    if not self.notify(subscribers, listens):
                        self.users.pop(uid)
                        continue
                    self.db.store_listen(*listens)
                    self.users[uid] = (seen, newlast, False, now, subscribers)

class WaveGenerator(object):

    def __init__(self, u):
        self.uid = u.uid
        self.access_token = u.access_token
        self.db = DB()
        self.results = PriorityQueue()

    def fetch_friends(self):
        friends = self.db.friends(self.uid)
        if not friends:
            friends = [User(x["id"], None, x["name"]) for x
                in unpage_par(fb.me.using(self.access_token).friends.get)]
            self.db.store_friends(self.uid, friends)
        return friends

    def rt_listens_for(self, u):
        rt_results = users.subscribe(u.uid, self.access_token)
        for listen in rt_results:
            if not self.db.has_song(listen.sid):
                self.db.store_song(self.fetch_song(listen.sid))
            t = self.db.match_song(listen.sid)
            if t:
                self.results.put((1, {
                        "trackId": t.ztid,
                        "userId": u.uid,
                        "userName": u.uname,
                        "src": t.surl,
                        "songName": t.title,
                        "artistName": t.artist_name,
                        "artistPhoto": t.aimgurl,
                        "coverSrc": t.rimgurl,
                        "timestamp": listen.ts.strftime("%Y-%m-%dT%H:%M:%S+0000")
                        }))

    def listens_for(self, u, num=50):
        last_ts, last_cts = self.db.last_listen(u.uid)
       #if not last_cts or (
       #        last_cts and datetime.utcnow() - last_ts > timedelta(seconds=300)):
       #    for listen in unpage_seq(
       #            fb[u.uid]["music.listens"].using(self.access_token).get, num):
       #        ts = fb_datetime(listen.get("end_time"))
       #        if last_ts and last_ts >= ts:
       #            break
       #        listen = Listen(
       #            lid=listen.get("id"),
       #            uid=u.uid,
       #            sid=listen.get("data", {}).get("song", {}).get("id"),
       #            ts=ts)
       #        self.db.store_listen(listen)
       #        yield listen
       #    self.db.update_cts(u.uid)
        time.sleep(2)
        for n, listen in enumerate(self.db.listens(u.uid, last_ts)):
            if n % 3 == 0:
                time.sleep(1)
            yield listen

    def fetch_song(self, sid):
        data = fb[sid].using(self.access_token).get()
        return Song(
            sid=sid,
            title=data.get("title"),
            artist_name=data.get("data", {}).get("musician", [{}])[0].get("name"),
            site_name=data.get("site_name"))

    def fetch_listens(self, u):
        for listen in self.listens_for(u):
            if not self.db.has_song(listen.sid):
                self.db.store_song(self.fetch_song(listen.sid))
            t = self.db.match_song(listen.sid)
            if t:
                self.results.put((10, {
                    "trackId": t.ztid,
                    "userId": u.uid,
                    "userName": u.uname,
                    "src": t.surl,
                    "songName": t.title,
                    "artistName": t.artist_name,
                    "artistPhoto": t.aimgurl,
                    "coverSrc": t.rimgurl,
                    "timestamp": listen.ts.strftime("%Y-%m-%dT%H:%M:%S+0000")
                    }))

    def fetch(self):
        friends = self.fetch_friends()
        for f in friends:
            spawn(self.rt_listens_for, f)
            spawn(self.fetch_listens, f)

    def __call__(self):
        spawn(self.fetch)
        return self.results

def wave_for(u):
    return WaveGenerator(u)()

def song(sid, access_token):
    data = fb[sid].using(access_token).get()
    return Song(
        sid=sid,
        title=data.get("title"),
        artist_name=data.get("data", {}).get("musician", [{}])[0].get("name"),
        site_name=data.get("site_name"))

def fb_datetime(v):
    return datetime.strptime(v, "%Y-%m-%dT%H:%M:%S+0000") + timedelta(seconds=10800) if v else None

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

users = None

#@run_with_reloader
def main():
    global users
    users = UserTracker()
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(("0.0.0.0", 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

def shell():
    from facebook import shell
    shell((settings.FB_APP_ID, settings.FB_SECRET))

if __name__ == "__main__":
    main()
