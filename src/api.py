"""
    API functionality for RoboRegistry
    @author: Lucas Bubner, 2023
"""
from flask import request, redirect, Blueprint, make_response
from wrappers import login_required
from firebase_instance import auth

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
    return [{"text": "api speaking", "path": "/"}]
