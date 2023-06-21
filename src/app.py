"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

import os
import warnings
from datetime import timedelta, datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, make_response
from flask_login import LoginManager, login_user, current_user, login_required
from flask_wtf.csrf import CSRFProtect

import api
import events
import utils
import wrappers
from auth import auth_bp, User
from firebase_instance import auth

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

if os.getenv("FLASK_ENV") != "production":
    app.debug = True
    warnings.warn("Currently running in DEVELOPMENT mode. Set FLASK_ENV to 'production' to change this.")

app.secret_key = key

csrf = CSRFProtect(app)
login_manager = LoginManager()

login_manager.init_app(app)
csrf.init_app(app)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
)

app.register_blueprint(utils.filter_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api.api_bp)
app.register_blueprint(events.events_bp)


@login_manager.user_loader
def load_user(uid=None):
    """
        Loads the user from the database into the session.
    """
    # Attempt to retrieve the user tokens from the cookies
    refresh_token = request.cookies.get("refresh_token")
    # The refresh token would be set from the login page
    if refresh_token:
        try:
            # Refresh user token based on refresh token
            user = auth.refresh(refresh_token)

            # Store new refresh token in cookies
            response = make_response(redirect("/dashboard"))
            response.set_cookie("refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")

            # Use token to get user account info
            acc = auth.get_account_info(user["idToken"])
            user_obj = User(acc)
            user_obj.refresh()

            return user_obj
        except Exception:
            return None
    elif uid:
        # If we don't have a refresh token, indicating we are on a new session, use the UID to get the user
        # as Flask-Login would have stored the UID as part of a remember-me schema
        acc = auth.get_account_info(uid)
        user_obj = User(acc)
        user_obj.refresh()
        return user_obj
    else:
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
        Redirects the user to the login page if they try to access a page that requires login.
    """
    session["next"] = "/" + request.full_path.lstrip("/").rstrip("?")
    return redirect(url_for("auth.login"))


@app.route("/")
def index():
    """
        Index page where the user will be directed to a login page.
        If the user can be logged in automatically, they will be redirected to the dashboard.
    """
    user = load_user()
    if user:
        # Log user in with Flask-Login
        if should_remember := session.get("should_remember", False):
            session.pop("should_remember")
        login_user(user, remember=should_remember)

        # Redirect those who haven't verified their email to the verification page
        is_email_verified = getattr(
            current_user, "is_email_verified", lambda: False)
        if not is_email_verified():
            return redirect(url_for("auth.verify"))

        # Ensure we have the user's data in the database
        # This is also handled by the @user_data_must_be_present wrapper, but since this is where
        # we assign user data, we will ensure the state has been considered before continuing.
        if not getattr(current_user, "data", None):
            return redirect(url_for("auth.create_profile"))

        # Try to redirect to the page the user was trying to access before logging in
        if goto := session.get("next"):
            session.pop("next")
            return redirect(goto)
        return redirect("/dashboard")
    else:
        return redirect(url_for("auth.login"))


@app.route("/dashboard")
@login_required
@wrappers.user_data_must_be_present
def dashboard():
    """
        Primary landing page for logged-in users, including a list of their own events.
        For users that haven't completed the profile creation process, they will be redirected by the index.
    """
    return render_template("dash/dash.html.jinja", user=getattr(current_user, "data", None))


@app.route("/settings", methods=["GET", "POST"])
@login_required
@wrappers.user_data_must_be_present
def settings():
    """
        Settings page for the user, including the ability to change their theme, settings, etc.
    """
    if request.method == "POST":
        res = make_response(redirect(url_for("dashboard")))
        darkmode = request.form.get("darkmode")
        # Use cookies to store user preferences
        res.set_cookie("darkmode", darkmode or "off", secure=True,
                       expires=datetime.now() + timedelta(days=365))
        return res
    else:
        current_settings = {
            "darkmode": request.cookies.get("darkmode")
        }
        return render_template("misc/settings.html.jinja", user=getattr(current_user, "data", None),
                               settings=current_settings)


@app.route("/about")
def about():
    return render_template("misc/about.html.jinja")


def error_handler(code, reason):
    def decorator(f):
        @app.errorhandler(code)
        def wrapper(e):
            return render_template("misc/error.html.jinja", code=code, reason=reason, debug=e.description), code

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


@error_handler(409, "Conflict")
def handle_409(e):
    pass
