"""
    Utility functions and filters for RoboRegistry
    @author: Lucas Bubner, 2023
"""
from datetime import datetime

from flask import Blueprint
from flask_login import current_user

filter_bp = Blueprint("filters", __name__, template_folder="templates")


@filter_bp.app_template_filter('strftime')
def filter_datetime(date):
    """
        Convert date to MonthName Day, Year format
    """
    date = datetime.fromisoformat(date)
    return date.strftime("%b %d, %Y")


@filter_bp.app_template_filter('timeto')
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


def limit_to_999(value):
    """
        Limit a value to 0-999 and safe cast to int.
    """
    if value is None:
        return None
    try:
        value = int(value)
        if value == 0:
            # Zero is nullish, so return "0" instead
            return "0"
        if value < 0:
            return None
    except ValueError:
        return None
    return min(value, 999)


def validate_form(form_data, role):
    """
        Ensure all fields for registration are valid.
    """
    # repName, contactName, contactEmail, role required
    if not all(form_data.get(field) for field in ("repName", "contactName", "contactEmail")) or not role:
        return False
    # numPeople, numStudents, numMentors, teams required if role is "comp"
    if role == "comp" and not all(
            form_data.get(field) for field in ("numPeople", "numStudents", "numMentors", "teams")):
        return False
    # numPeople must be in ["lt5", "5t10", "10t15", "15t20", "20t25", "gt25"]
    if role == "comp" and form_data.get("numPeople") not in ("lt5", "5t10", "10t15", "15t20", "20t25", "gt25"):
        return False
    # All values in teams must be non-empty
    if form_data.get("teams") and any(not team for team in form_data.get("teams")):
        return False
    return True


def reformat_number(number):
    """
        Remove a phone number from any formatting.
    """
    return number.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")


def validate_email(email):
    """
        Validate an email address by checking for "@" and "." in this order.
    """
    if "@" not in email:
        return False
    if "." not in email:
        return False
    if email.index(".") < email.index("@"):
        return False
    return True


def get_uid():
    """
        Fetch the localId for the current user.
    """
    # current_user.acc.users[0].localId
    return getattr(current_user, "acc", {}).get("users", [{}])[0].get("localId", None)
