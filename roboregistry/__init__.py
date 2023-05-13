"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

from flask import Flask
app = Flask(__name__)

import roboregistry.routes
