""" App"""

from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template, request, abort
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer
import werkzeug.serving

import facebook
import settings

__all__ = ("app", "main")

app = Flask(__name__)
fb = facebook.API(settings.FB_APP_ID, settings.FB_SECRET)

@app.route("/")
def welcome():
    return render_template("welcome.html", settings=settings)

@app.route('/wave')
def wave():
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        while True:
            message = ws.wait()
            ws.send(message)
    return abort(400)

@werkzeug.serving.run_with_reloader
def main():
    app.debug = settings.DEBUG if hasattr(settings, "DEBUG") else False
    http_server = WSGIServer(('',5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()

if __name__ == "__main__":
    main()

