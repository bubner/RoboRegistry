"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

import os
import warnings
from datetime import timedelta, datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, make_response, flash
from flask_login import LoginManager, current_user, login_required
from flask_wtf.csrf import CSRFProtect
from requests.exceptions import HTTPError

import api
import db
import events
import utils
from auth import auth_bp, User
from wrappers import validate_user

load_dotenv()
app = Flask(__name__)

key = os.getenv("SECRET_KEY")
if not key:
    key = os.urandom(32)
    warnings.warn(
        "SECRET_KEY not set in .env file. It has been set to a random value but may cause issues with multiple instances.")

if not os.getenv("FIREBASE_API_KEY"):
    raise RuntimeError("FIREBASE_API_KEY not set in .env file.")

if not os.getenv("OAUTH_TOKEN"):
    raise RuntimeError("OAUTH_TOKEN not set in .env file.")

if not os.getenv("MAPBOX_API_KEY"):
    raise RuntimeError("MAPBOX_API_KEY not set in .env file.")

if os.getenv("FLASK_ENV") == "development":
    app.debug = True
    warnings.warn("Currently running in DEVELOPMENT mode. Unset FLASK_ENV from 'development' to disable.")

app.secret_key = key

csrf = CSRFProtect(app)
login_manager = LoginManager()

login_manager.init_app(app)
csrf.init_app(app)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=60)
)

app.register_blueprint(utils.filter_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api.api_bp)
app.register_blueprint(events.events_bp)


@login_manager.user_loader
def load_user(ref_token):
    """
        Loads the user from the database into the session.
    """
    if ref_token:
        try:
            user = User(ref_token)
        except HTTPError:
            # Refresh token is no longer valid
            return None
        user.refresh()
        return user
    else:
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
        Redirects the user to the login page if they try to access a page that requires login.
    """
    session["next"] = "/" + request.full_path.lstrip("/").rstrip("?")
    flash("Login required or session expired. Please log in to continue.")
    return redirect(url_for("auth.login"))


@app.route("/")
@validate_user
def index():
    """
        Index page where the user will be directed to a login page.
        If the user can be logged in automatically, they will be redirected to the dashboard.
    """
    if current_user:
        # Try to redirect to the page the user was trying to access before logging in
        if goto := session.get("next"):
            session.pop("next")
            return redirect(goto)
        return redirect("/dashboard")
    else:
        return redirect(url_for("auth.login"))


@app.route("/dashboard")
@login_required
@validate_user
def dashboard():
    """
        Primary landing page for logged-in users, including a list of their own events.
        For users that haven't completed the profile creation process, they will be redirected by the index.
    """
    return render_template("dash/dash.html", user=getattr(current_user, "data", None))


@app.route("/settings", methods=["GET", "POST"])
@login_required
@validate_user
def settings():
    """
        Settings page for the user, including the ability to change their theme, settings, etc.
    """
    if request.method == "POST":
        res = make_response(redirect(url_for("dashboard")))
        darkmode = request.form.get("darkmode")
        account = {
            "email": getattr(current_user, "data", {}).get("email"),
            "first_name": request.form.get("first"),
            "last_name": request.form.get("last"),
            "role": request.form.get("role"),
            "affil": request.form.get("affil"),
        }

        if not all(account.values()):
            flash("Please fill out all fields.")
            return redirect(url_for("settings"))

        # Promotion can be False, which will flag all()
        account["promotion"] = request.form.get("promotion") == "on"

        if len(account["first_name"]) > 16 or len(account["last_name"]) > 16:
            flash("Name(s) must be less than 16 characters each.")
            return redirect(url_for("settings"))

        # Update the user account info
        db.mutate_user_data(account)
        getattr(current_user, "refresh")()

        # Use cookies to store user preferences
        res.set_cookie("darkmode", darkmode or "off", secure=True,
                       expires=datetime.now() + timedelta(days=365))
        return res
    else:
        current_settings = {
            "darkmode": request.cookies.get("darkmode"),
            "first": getattr(current_user, "data", {}).get("first_name", ""),
            "last": getattr(current_user, "data", {}).get("last_name", ""),
            "promotion": getattr(current_user, "data", {}).get("promotion", ""),
            "role": getattr(current_user, "data", {}).get("role", ""),
            "affil": getattr(current_user, "data", {}).get("affil", ""),
        }
        return render_template("misc/settings.html", user=getattr(current_user, "data", None),
                               settings=current_settings)


@app.route("/about")
def about():
    return render_template("misc/about.html")


@app.route("/exportall")
@login_required
def exportall():
    """
        Export all user data available for the current user.
    """
    raise NotImplementedError


def error_handler(code, reason):
    def decorator(f):
        @app.errorhandler(code)
        def wrapper(e):
            return render_template("misc/error.html", code=code, reason=reason, debug=e.description), code

        return wrapper

    return decorator


@error_handler(400, "CSRF Violation")
def handle_csrf_error(e):
    pass


@error_handler(404, "Not Found")
def handle_404(e):
    pass


@error_handler(500, "Internal Server Error")
def handle_500(e):
    pass


@error_handler(403, "Forbidden")
def handle_403(e):
    pass


@error_handler(405, "Method Not Allowed")
def handle_405(e):
    pass
