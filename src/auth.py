"""
    User authentication and profile creation for RoboRegistry
    @author: Lucas Bubner, 2023
"""

from flask import Blueprint, render_template, request, redirect, session, make_response, url_for
from firebase_instance import auth
from wrappers import login_required
from os import getenv

import db

auth_bp = Blueprint("auth", __name__, template_folder="templates")
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


@auth_bp.route("/login", methods=["GET", "POST"])
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
            response.set_cookie(
                "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
            return response
        except Exception:
            return render_template("auth/login.html.jinja", error="Invalid email or password.")
    else:
        return render_template("auth/login.html.jinja")


@auth_bp.route("/register", methods=["GET", "POST"])
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


@auth_bp.route("/googleauth")
def googleauth():
    """
        Redirects the user to the Google OAuth page.
    """
    return redirect(auth.authenticate_login_with_google())


@auth_bp.route("/logout")
def logout():
    """
        Logs out the user by removing the user token from the cookies.
    """
    res = make_response(redirect(url_for("auth.login")))
    res.set_cookie("refresh_token", "", expires=0)
    session.clear()
    return res


@auth_bp.route("/forgotpassword", methods=["GET", "POST"])
def forgotpassword():
    """
        Allows the user to reset their password.
    """
    if request.method == "POST":
        if not (email := request.form["email"]):
            return render_template("auth/forgotpassword.html.jinja", error="Please enter an email address.")
        try:
            # Send a password reset email to the user
            auth.send_password_reset_email(email)
            return render_template("auth/forgotpassword.html.jinja", success="Password reset email sent. Please follow instructions from there.")
        except Exception:
            return render_template("auth/forgotpassword.html.jinja", error="Something went wrong, please try again.")
    else:
        return render_template("auth/forgotpassword.html.jinja")


@auth_bp.route("/verify")
@login_required
def verify():
    """
        Page for users to verify their email address.
    """
    auth.send_email_verification(session.get("token"))
    return render_template("auth/verify.html.jinja")


@auth_bp.route("/create_profile", methods=["GET", "POST"])
@login_required
def create_profile():
    """
        Creates a profile for the user, including name, affiliation, and contact details.
    """
    auth_email = auth.get_account_info(session.get("token"))[
        "users"][0]["email"]
    # If the user already has a profile, redirect them back to the dashboard
    if db.get_user_data():
        return redirect("/dashboard")

    if request.method == "POST":
        # Get the users information from the form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        role = request.form.get("role")
        if not first_name or not last_name or not role:
            return render_template("auth/addinfo.html.jinja", error="Please enter required details.", email=auth_email)

        if len(first_name) > 16 or len(last_name) > 16:
            return render_template("auth/addinfo.html.jinja", error="Name(s) must be less than 16 characters each.", email=auth_email)

        if not (email := request.form.get("email")):
            email = auth_email

        if not (promotion := request.form.get("consent")):
            promotion = "off"

        # Create the user's profile
        db.mutate_user_data({"first_name": first_name, "last_name": last_name,
                             "role": role, "email": email, "promotion": promotion})

        return redirect("/")
    else:
        return render_template("auth/addinfo.html.jinja", email=auth_email)
