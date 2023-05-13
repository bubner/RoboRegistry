"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

from flask import Flask, render_template
app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")
