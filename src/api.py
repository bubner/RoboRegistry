"""
    API functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""
from flask import request, redirect, Blueprint, make_response
from wrappers import login_required
from datetime import datetime, timedelta
from firebase_instance import auth

import db

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/api/oauth2callback")
def callback():
    """
        Handles the callback from Google OAuth.
    """
    user = auth.sign_in_with_oauth_credential(request.url)
    res = make_response(redirect("/"))
    res.set_cookie(
        "refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
    return res


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
        # Check if the date of an event is in the next two weeks
        date = datetime.strptime(created_events[uid]['date'], "%Y-%m-%d")
        if date > datetime.now() and date < datetime.now() + timedelta(days=14):
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
                    "text": f"📖 View registered '{registered_events[uid]['name'].upper()}' event",
                    "path": f"/events/view/{uid}"
                }
            )
    return should_display
