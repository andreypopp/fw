""" App"""

from flask import Flask
import facebook
import settings

__all__ = ("app", "main")

app = Flask(__name__)
fb = facebook.API(settings.FB_APP_ID, settings.FB_SECRET)

@app.route("/")
def index():
    return "Hello World!"

def main():
    app.run()

if __name__ == "__main__":
    main()

