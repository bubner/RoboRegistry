"""
    API functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""

from datetime import datetime, timedelta

import requests
from flask import request, redirect, Blueprint, abort, flash
from flask_login import login_required, login_user
from pytz import timezone
from requests.exceptions import MissingSchema, HTTPError

import db
from auth import User
from fb import auth
from wrappers import must_be_event_owner

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/api/oauth2callback")
def callback():
    """
        Handles the callback from Google OAuth.
    """
    try:
        user = auth.sign_in_with_oauth_credential(request.url)
        if not user:
            raise MissingSchema
    except MissingSchema:
        return redirect("/login")
    # Always remember the user when they log in with Google
    login_user(User(user.get("refreshToken")), True)
    return redirect("/")


@api_bp.route("/api/dashboard")
@login_required
def api_dashboard():
    """
        Calculates and returns the user's dashboard information in JSON format.
    """
    # Get user registered events
    registered_events, created_events = db.get_my_events()
    should_display = []
    for uid in created_events:
        # Check if the date of an event is in the next 4 weeks
        date = datetime.strptime(created_events[uid]['date'], "%Y-%m-%d")
        if datetime.now() < date < datetime.now() + timedelta(days=28):
            should_display.append(
                {
                    "text": f"🔍 View your upcoming '{created_events[uid]['name'].upper()}' event",
                    "path": f"/events/manage/{uid}"
                }
            )
    for uid in registered_events:
        # Display all registered events if they have not yet occurred
        date = datetime.strptime(registered_events[uid]['date'], "%Y-%m-%d")
        if date > datetime.now():
            should_display.append(
                {
                    "text": f"📖 View your registered '{registered_events[uid]['name'].upper()}' event",
                    "path": f"/events/view/{uid}"
                }
            )
    if len(should_display) == 0:
        # No events, show the standard dashboard messages
        should_display = [
            {
                "text": "🔍 Have an event link?",
                "path": "/events"
            },
            {
                "text": "⚙️ Manage your settings and preferences",
                "path": "/settings"
            },
            {
                "text": "📝 Create your very own event",
                "path": "/events/create"
            },
            {
                "text": "❓ Need help with registering?",
                "path": "https://scribehow.com/shared/RoboRegistry_account_creation_and_registration__PHs0o3GWQz6Rg5ERmlAodQ"
            }
        ]
    return should_display


@api_bp.route("/api/is_auto_open/<string:event_id>")
@login_required
def api_is_auto_open(event_id):
    """
        Determines if an event is automatically open for registration and checkin.
    """
    event = db.get_event(event_id)
    if not event:
        abort(404)

    tz = timezone(event["timezone"])

    start_time = tz.localize(datetime.strptime(
        f"{event['date']} {event['start_time']}", "%Y-%m-%d %H:%M"))
    can_register = start_time > datetime.now(tz)

    can_checkin = start_time < datetime.now(tz) < tz.localize(datetime.strptime(
        f"{event['date']} {event['end_time']}", "%Y-%m-%d %H:%M"))

    return {
        "can_register": can_register,
        "can_checkin": can_checkin
    }


@api_bp.route("/api/registrations/<string:event_id>")
@login_required
@must_be_event_owner
def api_event_data(event_id):
    """
        Returns all registered users and their data for an event.
    """
    event = db.get_event(event_id)
    if not event:
        return {
            "error": "NOT_FOUND"
        }, 404

    try:
        data = db.get_event_data(event_id)
    except HTTPError:
        return {
            "error": "FORBIDDEN"
        }, 403

    # Merge public and private data into an object of all data
    bigdata = {}
    if event.get("registered"):
        for uid in event["registered"]:
            user = {}
            if data:
                user.update(data[uid])
            user.update(event["registered"][uid])
            bigdata[uid] = user
    
    # Add any anonymous check-in data
    if data.get("anon_data"):
        bigdata["anon_checkin"] = data["anon_data"]

    return bigdata


@api_bp.route("/api/changevis/<string:event_id>", methods=["POST"])
@login_required
@must_be_event_owner
def api_change_visibility(event_id):
    """
        Changes the visibility of an event.
    """
    event = db.get_event(event_id)
    if not event:
        return {
            "error": "NOT_FOUND"
        }, 404

    # Toggle the visibility
    db.update_event(event_id, {}, {"visible": not event["settings"]["visible"]})
    flash("Visibility status changed.", "success")

    return redirect(f"/events/manage/{event_id}")


@api_bp.route("/api/changeregis/<string:event_id>", methods=["POST"])
@login_required
@must_be_event_owner
def api_change_registration(event_id):
    """
        Changes the registration status of an event.
    """
    event = db.get_event(event_id)
    if not event:
        return {
            "error": "NOT_FOUND"
        }, 404

    # Toggle the registration
    db.update_event(event_id, {}, {"regis": not event["settings"]["regis"]})
    flash("Registration status changed.", "success")

    return redirect(f"/events/manage/{event_id}")


@api_bp.route("/api/changecheckin/<string:event_id>", methods=["POST"])
@login_required
@must_be_event_owner
def api_change_checkin(event_id):
    """
        Changes the checkin status of an event.
    """
    event = db.get_event(event_id)
    if not event:
        return {
            "error": "NOT_FOUND"
        }, 404

    # Toggle the checkin
    db.update_event(event_id, {}, {"checkin": not event["settings"]["checkin"]})
    flash("Check-in status changed.", "success")

    return redirect(f"/events/manage/{event_id}")


@api_bp.route("/api/addregistration/<string:event_id>", methods=["POST"])
@login_required
@must_be_event_owner
def api_manual_regis(event_id):
    """
        Manually register someone for an event.
        request.form contains the normal registration data.
    """
    if not db.get_event(event_id):
        return {
            "error": "NOT_FOUND"
        }, 404
    req = {
        **request.form,
        "manual": "true"
    }
    res = requests.post(f"{request.host_url}events/register/{event_id}", data=req, cookies=request.cookies,
                        headers=request.headers, allow_redirects=False)
    if res.status_code != 200:
        flash("Registration failed. Please ensure the fields you have entered are valid.", "danger")
    else:
        flash("Registration successful.", "success")
    return redirect(f"/events/manage/{event_id}")


@api_bp.route("/api/opencinow/<string:event_id>")
@login_required
@must_be_event_owner
def api_open_checkin(event_id):
    """
        Open an event check in by overriding the event start time to now.
    """
    event = db.get_event(event_id)
    if not event:
        return {
            "error": "NOT_FOUND"
        }, 404
    
    tz = timezone(event["timezone"])
    start_time = tz.localize(datetime.strptime(
        f"{event['date']} {event['start_time']}", "%Y-%m-%d %H:%M"))
    
    # Check if the event is not visible
    if not event["settings"]["visible"]:
        flash("Your event is not visible, therefore check-in cannot be opened.", "danger")
        return redirect(f"/events/manage/{event_id}")
    
    # Check if check-ins are closed and remind the user
    if not event["settings"]["checkin"]:
        flash("Check-ins are manually closed. Please open them before opening check-in.", "danger")
        return redirect(f"/events/manage/{event_id}")
    
    # If the event has already started then check-in is already open
    if start_time < datetime.now(tz) < tz.localize(datetime.strptime(f"{event['date']} {event['end_time']}", "%Y-%m-%d %H:%M")):
        flash("Check-in is already open.", "warning")
        return redirect(f"/events/manage/{event_id}")
        
    # If the event is over then check-in cannot be opened
    if datetime.now(tz) >= tz.localize(datetime.strptime(f"{event['date']} {event['end_time']}", "%Y-%m-%d %H:%M")):
        flash("Check-in cannot be opened after the event has ended.", "danger")
        return redirect(f"/events/manage/{event_id}")

    # If it is not the event date, we cannot open check-in
    if datetime.now(tz).date() != start_time.date():
        flash("Check-in cannot be opened before the event date.", "danger")
        return redirect(f"/events/manage/{event_id}")

    # Override the start time based on the event timezone now
    db.update_event(event_id, {"start_time": datetime.now(tz).strftime("%H:%M")}, {})

    flash(f"Check-in has been opened ({datetime.now(tz).strftime('%H:%M')}).", "success")
    return redirect(f"/events/manage/{event_id}")
