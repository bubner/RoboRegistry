"""
    API functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""

from datetime import datetime, timedelta

from flask import request, redirect, Blueprint, make_response, session
from flask_login import current_user, login_required

import db
from firebase_instance import auth

api_bp = Blueprint("api", __name__, template_folder="templates")


@api_bp.route("/api/oauth2callback")
def callback():
    """
        Handles the callback from Google OAuth.
    """
    user = auth.sign_in_with_oauth_credential(request.url)
    res = make_response(redirect("/"))
    res.set_cookie("refresh_token", user["refreshToken"], secure=True, httponly=True, samesite="Lax")
    # Always remember the user when they log in with Google
    session["should_remember"] = True
    return res


@api_bp.route("/api/dashboard")
@login_required
def api_dashboard():
    """
        Calculates and returns the user's dashboard information in JSON format.
    """
    # Get user registered events
    registered_events, created_events = db.get_my_events(getattr(current_user, "id"))
    should_display = []
    for uid in created_events:
        # Check if the date of an event is in the next two weeks
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
