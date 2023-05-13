"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

import firebase
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("auth/login.html")
