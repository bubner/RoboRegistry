"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

from os import getenv, urandom
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, make_response, flash
from flask_wtf.csrf import CSRFProtect
from datetime import timedelta
from firebase_instance import auth
from auth import auth_bp
from api import api_bp
from events import events_bp

import db
import wrappers
import utils

load_dotenv()
app = Flask(__name__)
csrf = CSRFProtect(app)
app.secret_key = getenv("SECRET_KEY") or urandom(32)

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    # CSRF PROTECTION IS DISABLED! https://github.com/hololb/RoboRegistry/issues/4
    WTF_CSRF_ENABLED=False
)

app.register_blueprint(utils.filter_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(events_bp)

csrf.init_app(app)


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
            response = make_response(redirect("/dashboard"))
            response.set_cookie(
                "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
            # Store user token in session
            session["token"] = user["idToken"]
            acc = auth.get_account_info(session.get("token"))
            session["uid"] = acc.get("users")[0].get("localId")

            # Redirect those who haven't verified their email to the verification page
            if not acc.get("users")[0].get("emailVerified"):
                return redirect(url_for("auth.verify"))

            # Ensure we have the user's data in the database
            # This is also handled by the @wrappers.user_data_must_be_present wrapper, but since this is where
            # we assign user data, we will ensure the state has been considered before continuing.
            if not db.get_user_data():
                return redirect(url_for("auth.create_profile"))

            # Try to redirect to the page the user was trying to access before logging in
            if goto := session.get("next"):
                session.pop("next")
                return redirect(goto)
            return redirect("/dashboard")
        except Exception:
            # If the token is invalid, redirect to the login page
            session.clear()
            flash("Your session has expired. Please log in again.")
            response = make_response(redirect(url_for("auth.login")))
            response.set_cookie("refresh_token", "", expires=0)
            return response
    else:
        # Clean slate, request a new login
        return redirect(url_for("auth.login"))


@app.route("/dashboard")
@wrappers.login_required
@wrappers.user_data_must_be_present
def dashboard():
    """
        Primary landing page for logged-in users, including a list of their own events.
        For users that haven't completed the profile creation process, they will be redirected by the index.
    """
    return render_template("dash/dash.html.jinja", user=db.get_user_data())


@app.route("/settings", methods=["GET", "POST"])
@wrappers.login_required
@wrappers.user_data_must_be_present
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
        current_settings = {
            "darkmode": request.cookies.get("darkmode")
        }
        return render_template("misc/settings.html.jinja", user=db.get_user_data(), settings=current_settings)


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
