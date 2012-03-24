""" App"""

from flask import Flask, render_template
import facebook
import settings

__all__ = ("app", "main")

app = Flask(__name__)
fb = facebook.API(settings.FB_APP_ID, settings.FB_SECRET)

@app.route("/")
def welcome():
    return render_template("welcome.html", settings=settings)

def main():
    app.run(debug=True)

if __name__ == "__main__":
    main()

