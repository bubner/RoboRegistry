"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

from os import getenv, urandom
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, make_response, abort
from datetime import timedelta
from db import Userdata
from flask_wtf.csrf import CSRFProtect, CSRFError

import firebase


# ===== Configuration =====
load_dotenv()
app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = getenv("SECRET_KEY") or urandom(32)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
)

config = {
    # Firebase API key is stored in the environment variables for security reasons
    "apiKey": getenv("FIREBASE_API_KEY"),
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
        "client_secret": getenv("OAUTH_TOKEN"),
        "redirect_uris": ["https://roboregistry.vercel.app/api/oauth2callback"] if getenv("FLASK_ENV") == "production" else ["http://localhost:5000/api/oauth2callback"],
        "javascript_origins": ["https://roboregistry.vercel.app"] if getenv("FLASK_ENV") == "production" else ["http://localhost:5000"]
    }
}

fb = firebase.initialize_app(config)
auth = fb.auth(client_secret=oauth_config)
db = Userdata(fb.database(), None)

# ===== Wrappers =====
def login_required(f):
    """
        Ensures all routes that require a user to be logged in are protected.
    """
    @wraps(f)
    def check(*args, **kwargs):
        if not session.get("token"):
            return redirect("/")
        return f(*args, **kwargs)
    return check


# ===== Routes =====
@app.route("/")
def index():
    """
        Index page where the user will be directed to either a dashboard if they are
        logged in or a login page if they are not.
    """
    # Attempt to retrieve the user tokens from the cookies
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            # Refresh user token based on refresh token
            user = auth.refresh(refresh_token)
            # Store refresh token in cookies
            response = make_response(redirect("/"))
            response.set_cookie(
                "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
            # Store user token in session
            session["token"] = user["idToken"]
            db.set_uid(auth.get_account_info(
                session.get("token"))["users"][0]["localId"])
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
    if session.get("token") or request.cookies.get("refresh_token"):
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
            # Set cookie with refresh token
            response.set_cookie("refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
            return response
        except Exception:
            return render_template("auth/login.html.jinja", error="Invalid email or password.")
    else:
        return render_template("auth/login.html.jinja")


@app.route("/register", methods=["GET", "POST"])
def register():
    """
        Registers the user with the provided email and password through Firebase.
    """
    # Redirect to dashboard if already logged in
    if session.get("token") or request.cookies.get("refresh_token"):
        return redirect("/")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if len(password) < 8:
            return render_template("auth/register.html.jinja", error="Password must be at least 8 characters long.")
        
        # Make sure password contains at least one number and one capital letter
        if not any(char.isdigit() for char in password) or not any(char.isupper() for char in password):
            return render_template("auth/register.html.jinja", error="Password must contain at least one number and one capital letter.")
        
        try:
            # Create the user with the provided email and password
            auth.create_user_with_email_and_password(email, password)
            res = make_response(redirect("/"))
            # Sign in on registration
            user = auth.sign_in_with_email_and_password(email, password)
            res.set_cookie(
                "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
            return res
        except Exception:
            return render_template("auth/register.html.jinja", error="Something went wrong, please try again.")
    else:
        return render_template("auth/register.html.jinja")


@app.route("/googleauth")
def googleauth():
    """
        Redirects the user to the Google OAuth page.
    """
    return redirect(auth.authenticate_login_with_google())


@app.route("/logout")
def logout():
    """
        Logs out the user by removing the user token from the cookies.
    """
    res = make_response(redirect(url_for("login")))
    res.set_cookie("refresh_token", "", expires=0)
    return res


@app.route("/dashboard")
@login_required
def dashboard():
    """
        Primary landing page for logged in users, including a list of their own events.
        For users that haven't completed the profile creation process, they will be redirected.
    """
    # Get information from Firebase about the user
    data = db.get_user_info()
    if not data:
        # If the user doesn't have a profile, redirect them to the profile creation page
        return redirect(url_for("create_profile"))
    return render_template("dash/dash.html.jinja", user=db.get_user_info())


@app.route("/create_profile", methods=["GET", "POST"])
@login_required
def create_profile():
    """
        Creates a profile for the user, including name, affiliation, and contact details.
    """
    auth_email = auth.get_account_info(session.get("token"))[
        "users"][0]["email"]
    # If the user already has a profile, redirect them to the dashboard
    if db.get_user_info():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        # Get the users information from the form
        name = request.form.get("name")
        role = request.form.get("role")
        if not role or not name:
            return render_template("auth/addinfo.html.jinja", error="Please enter required details.", email=auth_email)

        if len(name) > 16:
            return render_template("auth/addinfo.html.jinja", error="Name must be less than 16 characters.", email=auth_email)

        if not (email := request.form.get("email")):
            email = auth_email

        if not (promotion := request.form.get("consent")):
            promotion = "off"

        # Create the user's profile
        db.add_user_data({"name": name, "role": role,
                         "email": email, "promotion": promotion})
        return redirect(url_for("dashboard"))
    else:
        return render_template("auth/addinfo.html.jinja", email=auth_email)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """
        Settings page for the user, including the ability to change their theme, settings, etc.
    """
    if request.method == "POST":
        res = make_response(redirect(url_for("dashboard")))
        darkmode = request.form.get("darkmode")
        # Use cookies to store user preferences
        res.set_cookie("darkmode", darkmode or "off", secure=True)
        return res
    else:
        settings = {
            "darkmode": request.cookies.get("darkmode")
        }
        return render_template("misc/settings.html.jinja", user=db.get_user_info(), settings=settings)


# ===== API =====
@app.route("/api/oauth2callback")
def callback():
    """
        Handles the callback from Google OAuth.
    """
    user = auth.sign_in_with_oauth_credential(request.url)
    res = make_response(redirect("/"))
    res.set_cookie(
        "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
    return res


@app.route("/api/dashboard")
@login_required
def api_dashboard():
    """
        Calculates and returns the user's dashboard information in JSON format.
    """
    return [{"text": "api speaking", "path": "/"}]


# ===== Error Handlers =====
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return render_template("misc/error.html.jinja", code=400, reason="CSRF Violation", debug=e.description)

@app.errorhandler(404)
def handle_404(e):
    return render_template("misc/error.html.jinja", code=404, reason="Not Found", debug=e.description)

@app.errorhandler(500)
def handle_500(e):
    return render_template("misc/error.html.jinja", code=500, reason="Internal Server Error", debug=e.description)

@app.errorhandler(403)
def handle_403(e):
    return render_template("misc/error.html.jinja", code=403, reason="Forbidden", debug=e.description)

@app.errorhandler(405)
def handle_405(e):
    return render_template("misc/error.html.jinja", code=405, reason="Method Not Allowed", debug=e.description)
