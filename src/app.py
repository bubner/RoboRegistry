"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

from os import getenv
from dotenv import load_dotenv
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, make_response

import firebase

load_dotenv()

if not getenv("FIREBASE_API_KEY"):
    raise RuntimeError("FIREBASE_API_KEY is not currently set.")
if not getenv("SECRET_KEY"):
    raise RuntimeError("SECRET_KEY is not currently set.")

app = Flask(__name__)
app.secret_key = getenv("SECRET_KEY")

config = {
    # Firebase API key is stored in the environment variables for security reasons
    "apiKey": getenv("FIREBASE_API_KEY"),
    "authDomain": "roboregistry.firebaseapp.com",
    "databaseURL": "https://roboregistry-default-rtdb.firebaseio.com/",
    "projectId": "roboregistry",
    "storageBucket": "roboregistry.appspot.com",
    "messagingSenderId": "908229856176",
    "appId": "1:908229856176:web:1168d0be1562eb8ca5a475"
}

fb = firebase.initialize_app(config)
auth = fb.auth()
db = fb.database()


def login_required(f):
    @wraps(f)
    def check(*args, **kwargs):
        # Ensure that all routes that require login are protected
        if not session.get("user"):
            return redirect("/")
        return f(*args, **kwargs)
    return check


@app.route("/")
def index():
    """
        Index page where the user will be directed to either a dashboard if they are
        logged in or a login page if they are not.
    """
    # Attempt to retrieve the user token from the cookies
    user_token = request.cookies.get("user_token")
    if user_token:
        try:
            # Verify the user token
            user = auth.get_account_info(user_token)
            # Store UID in session
            session["user"] = user["users"][0]["localId"]
            return redirect(url_for("dashboard"))
        except Exception:
            # If the token is invalid, redirect to the login page
            return redirect(url_for("login"))
    else:
        # Clean slate, request a new login
        session.clear()
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """
        Logs in the user with the provided email and password through Firebase.
        Stores token into cookies.
    """
    # If we're already logged in then redirect to the dashboard
    if session.get("user") or request.cookies.get("user_token"):
        return redirect("/")
    if request.method == "POST":
        # Get the email and password from the form
        email = request.form["email"]
        password = request.form["password"]
        try:
            # Sign in with the provided email and password
            user = auth.sign_in_with_email_and_password(email, password)
            # Store the user token in a cookie
            response = make_response(redirect("/"))
            # Set cookie with user token
            response.set_cookie("user_token", user["idToken"])
            return response
        except Exception:
            return render_template("auth/login.html", error="Invalid email or password.")
    else:
        return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
        Registers the user with the provided email and password through Firebase.
    """
    # Redirect to dashboard if already logged in
    if session.get("user") or request.cookies.get("user_token"):
        return redirect("/")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        try:
            # Create the user with the provided email and password
            auth.create_user_with_email_and_password(email, password)
            res = make_response(redirect("/"))
            # Sign in on registration
            res.set_cookie("user_token", auth.sign_in_with_email_and_password(email, password)["idToken"])
            return res
        except Exception:
            return render_template("auth/register.html", error="Something went wrong, please try again.")
    else:
        return render_template("auth/register.html")


@app.route("/logout")
def logout():
    """
        Logs out the user by removing the user token from the cookies.
    """
    res = make_response(redirect(url_for("login")))
    res.set_cookie("user_token", "", expires=0)
    return res


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dash/dash.html", user=session.get("user"))