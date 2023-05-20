"""
    RoboRegistry
    @author: Lucas Bubner, 2023
"""

from os import getenv, urandom
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, make_response, abort
from datetime import timedelta, datetime
from db import Userdata
from re import sub
from flask_wtf.csrf import CSRFProtect, CSRFError

import firebase
import pytz


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


def must_be_event_owner(f):
    """
        Ensure permissions for administrative actions are only performed by the owner.
    """
    @wraps(f)
    def check(event_id, *args, **kwargs):
        if not db.is_event_owner(event_id):
            return abort(403)
        return f(event_id, *args, **kwargs)
    return check

# ===== Helper functions =====


@app.template_filter('strftime')
def filter_datetime(date):
    """
        Convert date to MonthName Day, Year format
    """
    date = datetime.fromisoformat(date)
    format = '%b %d, %Y'
    return date.strftime(format)


@app.template_filter('timeto')
def filter_timeto(date):
    """
        Convert time to relative units (e.g. 5 days, 2 hours)
    """
    date = datetime.fromisoformat(date)
    now = datetime.now()
    delta = date - now
    if delta.days < 0:
        return None
    elif delta.days > 0:
        return f"{delta.days} days"
    else:
        return f"{delta.seconds // 3600} hours"


def get_time_diff(start_time, end_time):
    """
        Calculate the time difference between two datetime objects.
    """
    time_diff = end_time - start_time
    days = time_diff.days
    hours, remainder = divmod(time_diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return days, hours, minutes

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
            acc = auth.get_account_info(session.get("token"))
            db.set_uid(acc["users"][0]["localId"])
            if acc.get("users")[0].get("emailVerified") == False:
                return redirect(url_for("verify"))
            return redirect(url_for("dashboard"))
        except Exception:
            # If the token is invalid, redirect to the login page
            session.clear()
            response = make_response(redirect(url_for("login")))
            response.set_cookie("refresh_token", "", expires=0)
            return response
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
            response.set_cookie(
                "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
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
    data = db.get_user_data()
    if not data:
        # If the user doesn't have a profile, redirect them to the profile creation page
        return redirect(url_for("create_profile"))
    return render_template("dash/dash.html.jinja", user=db.get_user_data())


@app.route("/verify")
@login_required
def verify():
    """
        Page for users to verify their email address.
    """
    auth.send_email_verification(session.get("token"))
    return render_template("auth/verify.html.jinja")


@app.route("/create_profile", methods=["GET", "POST"])
@login_required
def create_profile():
    """
        Creates a profile for the user, including name, affiliation, and contact details.
    """
    auth_email = auth.get_account_info(session.get("token"))[
        "users"][0]["email"]
    # If the user already has a profile, redirect them to the dashboard
    if db.get_user_data():
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
        db.mutate_user_data({"name": name, "role": role,
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
        return render_template("misc/settings.html.jinja", user=db.get_user_data(), settings=settings)


@app.route("/about")
def about():
    return render_template("misc/about.html.jinja")


@app.route("/forgotpassword", methods=["GET", "POST"])
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


@app.route("/events/view")
@login_required
def viewall():
    """
        View all personally affiliated events.
    """
    registered_events, created_events = db.get_my_events()
    return render_template("dash/view.html.jinja", created_events=created_events, registered_events=registered_events, user=db.get_user_data())


@app.route("/events/view/<string:uid>")
@login_required
def viewevent(uid: str):
    """
        View a specific user-owned event.
    """
    data = db.get_event(uid)

    registered = owned = False
    for key, value in data["registered"].items():
        if value == "owner" and key == db.uid:
            owned = True
            break
        elif key == db.uid:
            registered = True
            break

    # Calculate time to event
    start_time = datetime.strptime(
        f"{data['date']} {data['start_time']}", "%Y-%m-%d %H:%M")
    end_time = datetime.strptime(
        f"{data['date']} {data['end_time']}", "%Y-%m-%d %H:%M")

    days, hours, minutes = get_time_diff(datetime.now(), start_time)
    time_to_end = get_time_diff(datetime.now(), end_time)

    if days > 0:
        time = ""
        if days >= 7:
            time += f"{days // 7} week(s) "
        time += f"{days % 7} day(s) {hours} hour(s)"
    elif hours > 0:
        time = f"{hours} hour(s) {minutes} minute(s)"
    elif minutes > 0:
        time = f"{minutes} minute(s)"
    elif time_to_end[1] > 0:
        time = f"Ends in {time_to_end[1]} hours {time_to_end[2]} minute(s)"
    elif time_to_end[2] > 0:
        time = f"Ends in {time_to_end[2]} minute(s)"
    else:
        time = "Event has ended."

    can_register = time.startswith("Ends") or time.startswith("Event")
    tz = pytz.timezone(data["timezone"])
    offset = tz.utcoffset(datetime.now()).total_seconds() / 3600

    if not data:
        abort(409)

    return render_template("event/event.html.jinja", user=db.get_user_data(), event=data, registered=registered, owned=owned, mapbox_api_key=getenv("MAPBOX_API_KEY"), time=time, can_register=can_register, timezone=tz, offset=offset)


@app.route("/events/create", methods=["GET", "POST"])
@login_required
def create():
    """
        Create a new event on the system.
    """
    user = db.get_user_data()
    MAPBOX_API_KEY = getenv("MAPBOX_API_KEY")
    if request.method == "POST":
        if not (name := request.form.get("event_name")):
            return render_template("event/create.html.jinja", error="Please enter an event name.", user=user, mapbox_api_key=MAPBOX_API_KEY)
        if not (date := request.form.get("event_date")):
            return render_template("event/create.html.jinja", error="Please enter an event date.", user=user, mapbox_api_key=MAPBOX_API_KEY)
        # Generate an event UID
        event_uid = sub(r'[^a-zA-Z0-9]+', '-', name.lower()) + "-" + date.replace("-", "")
        if db.get_event(event_uid):
            return render_template("event/create.html.jinja", error="An event with that name and date already exists.", user=user, mapbox_api_key=MAPBOX_API_KEY)

        # Create the event and generate a UID
        event = {
            "name": name,
            # UIDs are in the form of <event name seperated by dashes><date seperated by dashes>
            "creator": db.uid,
            "date": date,
            "start_time": request.form.get("event_start_time"),
            "end_time": request.form.get("event_end_time"),
            "description": request.form.get("event_description"),
            "email": request.form.get("event_email") or user["email"],
            "location": request.form.get("event_location"),
            "limit": request.form.get("event_limit"),
            "timezone": request.form.get("event_timezone"),
            "registered": {db.uid: "owner"}
        }

        if not event["limit"] or int(event["limit"]) >= 1000:
            event["limit"] = -1

        # Make sure all fields were filled
        if not all(event.values()):
            return render_template("event/create.html.jinja", error="Please fill out all fields.", user=user, mapbox_api_key=MAPBOX_API_KEY, timezones=pytz.all_timezones)

        # Make sure start time is before end time
        if datetime.strptime(event["start_time"], "%H:%M") > datetime.strptime(event["end_time"], "%H:%M"):
            return render_template("event/create.html.jinja", error="Please enter a start time before the end time.", user=user, mapbox_api_key=MAPBOX_API_KEY, timezones=pytz.all_timezones)

        if event["date"] + event["start_time"] < datetime.now().strftime("%Y-%m-%d%H:%M"):
            return render_template("event/create.html.jinja", error="Please enter a date and time in the future.", user=user, mapbox_api_key=MAPBOX_API_KEY, timezones=pytz.all_timezones)

        db.add_event(event_uid, event)
        return redirect(f"/events/view/{event_uid}")
    else:
        return render_template("event/create.html.jinja", user=user, mapbox_api_key=MAPBOX_API_KEY, timezones=pytz.all_timezones)


@app.route("/events/delete/<string:event_id>", methods=["GET", "POST"])
@login_required
@must_be_event_owner
def delete(event_id: str):
    """
        Delete an event from the system.
    """
    if request.method == "POST":
        db.delete_event(event_id)
        return redirect("/events/view")
    else:
        return render_template("event/delete.html.jinja", event=db.get_event(event_id), user=db.get_user_data())


@app.route("/events/register/<string:event_id>", methods=["GET", "POST"])
@login_required
def event_register(event_id: str):
    """
        Register a user for an event.
    """
    event = db.get_event(event_id)
    if request.method == "POST":
        if event["limit"] != -1 and len(event["registered"]) >= event["limit"]:
            event["registered"][db.uid] = "excess"
            db.update_event(event_id, event)    
            return render_template("event/register.html.jinja", event=event, status="Failed: EVENT_FULL", message="This event has reached it's maximum capacity. Your registration has been placed on a waitlist, and we'll automatically add you if a spot frees up.", user=db.get_user_data())
        
        event["registered"][db.uid] = datetime.now()
        db.update_event(event_id, event)
        return render_template("event/register.html.jinja", event=event, status="Registration successful", message="Your registration was successfully recorded. Go to the dashboard to view all your registered events, and remember your Affiliation Name for check-in on the day.", user=db.get_user_data())
    else:
        if db.uid in event["registered"]:
            return render_template("event/register_done.html.jinja", event=event, status="Failed: REGIS_ALR", message="You are already registered for this event. If you wish to unregister from this event, please go to the event view tab and unregister from there.", user=db.get_user_data())
        return render_template("event/register.html.jinja", event=event, user=db.get_user_data())


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


@app.errorhandler(409)
def handle_409(e):
    return render_template("misc/error.html.jinja", code=409, reason="Conflict", debug=e.description)
