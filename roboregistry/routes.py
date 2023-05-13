"""
    Flask HTTP routes
    @author: Lucas Bubner
"""

from flask import render_template
from roboregistry import app

@app.route("/")
def index():
    return render_template("index.html")
