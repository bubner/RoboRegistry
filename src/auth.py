"""
    User authentication and profile creation for RoboRegistry
    @author: Lucas Bubner, 2023
"""
import random

from flask import Blueprint, render_template, request, redirect, session, make_response, url_for
from flask_login import current_user, UserMixin, login_required, logout_user, login_user
from requests.exceptions import HTTPError

import db
from firebase_instance import auth

auth_bp = Blueprint("auth", __name__, template_folder="templates")


class User(UserMixin):
    """
        User class for Flask-Login
    """

    def __init__(self, refresh_token):
        self.id = refresh_token
        # Automatically refresh the user's token
        self.token = auth.refresh(refresh_token).get("idToken")
        self.acc = auth.get_account_info(self.token)
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
        self.data = db.get_user_data(self.acc.get("users")[0].get("localId"), self.token)


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
            if not user:
                return redirect("/login")
            login_user(User(user.get("refreshToken")), remember=session.get("should_remember", False))
            return redirect("/")
        except Exception:
            return render_template("auth/login.html", error="Invalid email or password.")
    else:
        return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
        Registers the user with the provided email and password through Firebase.
    """
    # Redirect to dashboard if already logged in
    if getattr(current_user, "is_authenticated", lambda: False):
        return redirect("/")
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        session["should_remember"] = request.form.get("remember-me", False)

        if len(password) < 8:
            return render_template("auth/register.html", error="Password must be at least 8 characters long.")

        # Make sure password contains at least one number and one capital letter
        if not any(char.isdigit() for char in password) or not any(char.isupper() for char in password):
            return render_template("auth/register.html",
                                   error="Password must contain at least one number and one capital letter.")

        try:
            # Create the user with the provided email and password
            auth.create_user_with_email_and_password(email, password)
            res = make_response(redirect("/"))
            # Sign in on registration
            user = auth.sign_in_with_email_and_password(email, password)
            if not user:
                return redirect("/login")
            login_user(User(user.get("refreshToken")), remember=session.get("should_remember", False))
            return res
        except Exception:
            return render_template("auth/register.html", error="Something went wrong, please try again.")
    else:
        return render_template("auth/register.html")


@auth_bp.route("/googleauth")
def googleauth():
    """
        Redirects the user to the Google OAuth page.
    """
    if getattr(current_user, "is_authenticated", lambda: False):
        return redirect("/")
    return redirect(auth.authenticate_login_with_google())


@auth_bp.route("/logout")
def logout():
    """
        Logs out the user by removing the user token from the cookies.
    """
    res = make_response(redirect(url_for("auth.login")))
    session.clear()
    logout_user()
    return res


@auth_bp.route("/forgotpassword", methods=["GET", "POST"])
def forgotpassword():
    """
        Allows the user to reset their password.
    """
    if getattr(current_user, "is_authenticated", lambda: False):
        return redirect("/")
    if request.method == "POST":
        if not (email := request.form["email"]):
            return render_template("auth/forgotpassword.html", error="Please enter an email address.")
        try:
            # Send a password reset email to the user
            auth.send_password_reset_email(email)
            return render_template("auth/forgotpassword.html",
                                   success="Password reset email sent. Please follow instructions from there.")
        except Exception:
            return render_template("auth/forgotpassword.html", error="Something went wrong, please try again.")
    else:
        return render_template("auth/forgotpassword.html")


@auth_bp.route("/verify")
@login_required
def verify():
    """
        Page for users to verify their email address.
    """
    if getattr(current_user, "is_email_verified", lambda: False)():
        return redirect("/")
    try:
        auth.send_email_verification(getattr(current_user, "token", None))
    except HTTPError:
        # Timeout error, we can ignore it
        pass
    return render_template("auth/verify.html")


@auth_bp.route("/create_profile", methods=["GET", "POST"])
@login_required
def create_profile():
    """
        Creates a profile for the user, including name, affiliation, and contact details.
    """
    auth_email = getattr(current_user, "acc", {}).get("users", [{}])[0].get("email")
    # If the user already has a profile, redirect them back to the dashboard
    if getattr(current_user, "data", False):
        return redirect("/dashboard")

    if request.method == "POST":
        # Get the users information from the form
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        role = request.form.get("role")
        affil = request.form.get("affiliation")

        if not first_name or not last_name or not role or not affil:
            return render_template("auth/addinfo.html", error="Please enter required details.", email=auth_email)

        if len(first_name) > 16 or len(last_name) > 16:
            return render_template("auth/addinfo.html", error="Name(s) must be less than 16 characters each.",
                                   email=auth_email)

        if not (email := request.form.get("email")):
            email = auth_email

        promotion = request.form.get("consent")
        promotion = promotion == "on"

        # Create the user's profile
        db.mutate_user_data({"first_name": first_name.strip(), "last_name": last_name.strip(),
                             "role": role, "email": email, "promotion": promotion, "affil": affil.strip()})

        return redirect("/")
    else:
        return render_template("auth/addinfo.html", email=auth_email)


@auth_bp.route("/changepassword")
@login_required
def changepassword():
    """
        Change the password of the currently logged-in user.
    """
    # current_user.acc.users[0].providerUserInfo[0].providerId
    if getattr(current_user, "acc", {}).get("users", [{}])[0].get("providerUserInfo", [{}])[0].get(
            "providerId") == "google.com":
        # We cannot change the password of a user that signed in with Google, so we'll send them on their merry way
        return redirect("https://myaccount.google.com/security")

    # For now, we'll let Firebase handle all the password management, and an easy way we can do that is by sending a reset email
    auth.send_password_reset_email(getattr(current_user, "acc", {}).get("users", [{}])[0].get("email"))

    return render_template("auth/changepassword.html", user=getattr(current_user, "data", None))


@auth_bp.route("/deleteaccount", methods=["GET", "POST"])
@login_required
def deleteaccount():
    """
        Permanently deletes the user's account.
    """
    num = str(random.randint(100000, 999999))
    numevents = len(db.get_my_events()[1])

    if request.method == "POST":
        old_num = request.form.get("num")
        new_num = request.form.get("newnum")

        if old_num != new_num:
            return render_template("auth/deleteaccount.html", user=getattr(current_user, "data", None),
                                   error="Numbers don't match.", num=num, numevents=numevents)

        db.delete_all_user_events()
        db.delete_user_data()
        auth.delete_user_account(getattr(current_user, "token", None))

        return redirect("/logout")
    else:
        return render_template("auth/deleteaccount.html", user=getattr(current_user, "data", None), num=num,
                               numevents=numevents)
