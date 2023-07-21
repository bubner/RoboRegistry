"""
    User authentication and profile creation for RoboRegistry
    @author: Lucas Bubner, 2023
"""

from flask import Blueprint, render_template, request, redirect, session, make_response, url_for
from flask_login import current_user, UserMixin, login_required, logout_user, login_user

import db
from firebase_instance import auth

auth_bp = Blueprint("auth", __name__, template_folder="templates")


class User(UserMixin):
    """
        User class for Flask-Login
    """

    def __init__(self, tokens):
        # tokens may either be a dictionary from Firebase or a string from Flask-Login
        try:
            self.id = tokens.get("idToken")
        except AttributeError:
            self.id = tokens

        self.acc = auth.get_account_info(self.id)
        self.data = None

    def is_email_verified(self):
        """
            Returns whether the user's email is verified.
        """
        return self.acc.get("users")[0].get("emailVerified")

    def refresh(self):
        """
            Refreshes the local instance of user data to reflect data in Firebase.
        """
        self.data = db.get_user_data(self.acc.get("users")[0].get("localId"), self.id)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
        Logs in the user with the provided email and password through Firebase.
    """
    # If we're already logged in then redirect to the dashboard
    if getattr(current_user, "is_authenticated", lambda: False):
        return redirect("/")
    if request.method == "POST":
        # Get the email and password from the form
        email = request.form["email"]
        password = request.form["password"]
        try:
            # Sign in with the provided email and password
            user = auth.sign_in_with_email_and_password(email, password)
            login_user(User(user), remember=session.get("should_remember", False))
            return redirect("/")
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
        session["should_remember"] = request.form.get("remember-me", False)

        if len(password) < 8:
            return render_template("auth/register.html.jinja", error="Password must be at least 8 characters long.")

        # Make sure password contains at least one number and one capital letter
        if not any(char.isdigit() for char in password) or not any(char.isupper() for char in password):
            return render_template("auth/register.html.jinja",
                                   error="Password must contain at least one number and one capital letter.")

        try:
            # Create the user with the provided email and password
            auth.create_user_with_email_and_password(email, password)
            res = make_response(redirect("/"))
            # Sign in on registration
            user = auth.sign_in_with_email_and_password(email, password)
            res.set_cookie("refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
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
    logout_user()
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
            return render_template("auth/forgotpassword.html.jinja",
                                   success="Password reset email sent. Please follow instructions from there.")
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
    auth.send_email_verification(getattr(current_user, "id", None))
    return render_template("auth/verify.html.jinja")


@auth_bp.route("/create_profile", methods=["GET", "POST"])
@login_required
def create_profile():
    """
        Creates a profile for the user, including name, affiliation, and contact details.
    """
    auth_email = getattr(current_user, "acc", {}).get("users", [{}])[0].get("email")
    # If the user already has a profile, redirect them back to the dashboard
    if not getattr(current_user, "data", None):
        return redirect("/dashboard")

    if request.method == "POST":
        # Get the users information from the form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        role = request.form.get("role")
        if not first_name or not last_name or not role:
            return render_template("auth/addinfo.html.jinja", error="Please enter required details.", email=auth_email)

        if len(first_name) > 16 or len(last_name) > 16:
            return render_template("auth/addinfo.html.jinja", error="Name(s) must be less than 16 characters each.",
                                   email=auth_email)

        if not (email := request.form.get("email")):
            email = auth_email

        promotion = request.form.get("consent")
        promotion = promotion == "on"

        # Create the user's profile
        db.mutate_user_data({"first_name": first_name.strip(), "last_name": last_name.strip(),
                             "role": role, "email": email, "promotion": promotion})

        return redirect("/")
    else:
        return render_template("auth/addinfo.html.jinja", email=auth_email)
