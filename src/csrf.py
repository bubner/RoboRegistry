"""
    Custom middleware to add CSRF tokens to forms without using Flask-WTF.
    This has been done as in specific situations the browser doesn't play nicely with the CSRF session token.
    @author Lucas Bubner, 2023
"""
import uuid
from functools import wraps
from flask import session, request, abort

def protect(f):
    """
        Adds a CSRF token to the session and passes it to the template.
    """
    @wraps(f)
    def csrf_check(*args, **kwargs):
        # Generate a CSRF token
        session["csrf_token"] = session.get("csrf_token") or str(uuid.uuid4())
        # Check for validity
        if request.method == "POST" and session["csrf_token"] != request.form.get("csrf_token"):
            abort(400)
        return f(*args, **kwargs)
    return csrf_check

def token():
    """
        Returns the CSRF token for use in forms, if there is one.
    """
    return session.get("csrf_token")