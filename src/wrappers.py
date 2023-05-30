"""
    RoboRegistry route wrappers
    @author: Lucas Bubner, 2023
"""
from flask import session, request, flash, redirect, abort
from db import is_event_owner
from functools import wraps


def login_required(f):
    """
        Ensures all routes that require a user to be logged in are protected.
    """
    @wraps(f)
    def check(*args, **kwargs):
        if not session.get("token"):
            session["next"] = "/" + request.full_path.lstrip("/").rstrip("?")
            flash("You'll need to be signed in to continue. This won't take long!")
            return redirect("/")
        return f(*args, **kwargs)
    return check


def must_be_event_owner(f):
    """
        Ensure permissions for administrative actions are only performed by the owner.
    """
    @wraps(f)
    def check(event_id, *args, **kwargs):
        if not is_event_owner(event_id):
            return abort(403)
        return f(event_id, *args, **kwargs)
    return check
