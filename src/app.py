"""
    Temporary restrictive access following implementation implications.
    This module replaces app.py to keep the website running, but without functionality
"""
from flask import Flask, render_template
app = Flask(__name__)

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def index(path):
    return render_template("down.html.jinja")
