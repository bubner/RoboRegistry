"""
    API functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""

from datetime import datetime, timedelta

from flask import request, redirect, Blueprint, abort
from flask_login import login_required, login_user
from requests.exceptions import MissingSchema
from pytz import timezone

import db
from auth import User
from fb import auth

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
