"""
    RoboRegistry Firebase instance and configuration
    @author: Lucas Bubner, 2023
"""

import os

import firebase

config = {
    # Firebase API key is stored in the environment variables for security reasons
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": "roboregistry.firebaseapp.com",
    "databaseURL": "https://roboregistry-default-rtdb.firebaseio.com",
    "projectId": "roboregistry",
    "storageBucket": "roboregistry.appspot.com",
    "messagingSenderId": "908229856176",
    "appId": "1:908229856176:web:555ddb9cf48289d0a5a475"
}

oauth_config = {
    "web": {
        "client_id": "908229856176-9add6ckcvb0aljsur31to46i1batg28h.apps.googleusercontent.com",
        "project_id": "roboregistry",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": os.getenv("OAUTH_TOKEN"),
        "redirect_uris": ["http://localhost:5000/api/oauth2callback"] if os.getenv("FLASK_ENV") == "development" else ["https://roboregistry.vercel.app/api/oauth2callback"],
        "javascript_origins": ["http://localhost:5000"] if os.getenv("FLASK_ENV") == "development" else ["https://roboregistry.vercel.app"]
    }
}

fb = firebase.initialize_app(config)
auth = fb.auth(client_secret=oauth_config)
db = fb.database()
