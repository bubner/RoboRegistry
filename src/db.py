"""
    Database management methods for RoboRegistry
    @author: Lucas Bubner, 2023
"""

import math
from datetime import datetime
from time import time

from flask_login import current_user
from pytz import timezone
from requests.exceptions import HTTPError

import utils
from firebase_instance import db


def get_user_data(uid, auth=None) -> dict:
    """
        Gets a user's info from the database.
    """
    auth = auth or getattr(current_user, "id", None)
    try:
        data = db.child("users").child(uid).get(auth).val()
    except KeyError:
        return {}
    if not data:
        return {}
    return dict(data)


def mutate_user_data(info: dict, auth=None) -> None:
    """
        Appends user data in the database.
    """
    auth = auth or getattr(current_user, "id", None)
    db.child("users").child(utils.get_uid()).update(info, auth)


def get_uid_for(event_id, auth=None) -> str:
    """
        Find the event creator for an event.
    """
    auth = auth or getattr(current_user, "id", None)
    return str(db.child("events").child(event_id).child("creator").get(auth).val())


def add_event(uid, event, auth=None):
    """
        Adds an event to the database.
    """
    auth = auth or getattr(current_user, "id", None)
    db.child("events").child(uid).set(event, auth)


def add_entry(event_id, public_data, private_data, auth=None):
    """
        Updates an event in the database to reflect a new registration.
    """
    auth = auth or getattr(current_user, "id", None)
    public_data |= {
        "entity": f"{private_data['contactName']} | {private_data['repName'].upper()}",
        "checkin_data": {
            "checked_in": False,
            "time": 0
        }
    }
    db.child("events").child(event_id).child("registered").child(utils.get_uid()).set(public_data, auth)
    db.child("registered_data").child(event_id).child(utils.get_uid()).set(private_data, auth)


def remove_entry(event_id, auth=None):
    """
        Removes an event registration from the database.
    """
    auth = auth or getattr(current_user, "id", None)
    db.child("events").child(event_id).child("registered").child(utils.get_uid()).remove(auth)
    db.child("registered_data").child(event_id).child(utils.get_uid()).remove(auth)


def check_in(event_id, auth=None):
    """
        Checks a user into an event.
    """
    auth = auth or getattr(current_user, "id", None)
    db.child("events").child(event_id).child("registered").child(utils.get_uid()).child("checkin_data").set({
        "checked_in": True,
        "time": math.floor(time())
    }, auth)


def get_event(event_id, auth=None):
    """
        Gets an event from a creator from the database.
    """
    auth = auth or getattr(current_user, "id", None)
    try:
        event = db.child("events").child(event_id).get(auth).val()
        event = dict(event)
        event["uid"] = event_id
    except (HTTPError, TypeError):
        # Event does not exist
        return {}
    return event


def unregister(event_id, auth=None) -> bool:
    """
        Unregister from an event.
    """
    auth = auth or getattr(current_user, "id", None)
    # Disallow unregistration if event has already started/ended
    event = get_event(event_id)
    tz = timezone(event["timezone"])
    tz.localize(datetime.strptime(event["date"] + event["start_time"], "%Y-%m-%d%H:%M"))
    if datetime.now(tz) > tz.localize(datetime.strptime(event["date"] + event["end_time"], "%Y-%m-%d%H:%M")):
        return False

    db.child("events").child(event_id).child("registered").child(utils.get_uid()).remove(auth)
    db.child("registered_data").child(event_id).child(utils.get_uid()).remove(auth)
    return True


def verify_unique(event_id, repname, auth=None) -> bool:
    """
        Verify a team name is not already registered for an event.
    """
    auth = auth or getattr(current_user, "id", None)
    all_registrations = db.child("events").child(event_id).child("registered").get(auth).val()
    try:
        all_registrations = dict(all_registrations)
    except TypeError:
        # No registrations, has to be unique
        return True
    for registration in all_registrations.values():
        if registration["entity"].split(" | ")[1].upper() == repname.upper():
            return False
    return True


def get_event_data(event_id, auth=None):
    """
        Get registered data for an event.
        May only be accessed by the event owner.
    """
    auth = auth or getattr(current_user, "id", None)
    try:
        event_data = db.child("registered_data").child(event_id).get(auth).val()
    except (HTTPError, TypeError):
        # Event does not exist or cannot be accessed
        return {}
    return event_data


def get_uid_for_entity(event_id, entity) -> str:
    """
        Find the entity creator for an entity.
    """
    # entity has the structure of '{CONTACTNAME} | {REPNAME}'
    event = get_event(event_id)
    if not event:
        return ""
    for uid, data in event["registered"].items():
        if data["entity"] == entity:
            return uid
    return ""


def get_my_events(auth=None) -> tuple[dict, dict]:
    """
        Gets a user's events from the database.
        @return: (registered_events, owned_events)
    """
    auth = auth or getattr(current_user, "id", None)
    try:
        events = db.child("events").get(auth).val()
        registered_events = {}
        owned_events = {}
        for event_id, event_data in dict(events).items():
            if event_data["creator"] == utils.get_uid():
                owned_events[event_id] = event_data
                continue
            if event_data.get("registered") and utils.get_uid() in event_data["registered"]:
                registered_events[event_id] = event_data
    except (HTTPError, TypeError):
        # Events do not exist
        return {}, {}
    return registered_events, owned_events


def delete_event(event_id, auth=None):
    """
        Deletes an event from the database.
    """
    auth = auth or getattr(current_user, "id", None)
    if db.child("events").child(event_id).child("creator").get(auth).val() != utils.get_uid():
        return
    db.child("registered_data").child(event_id).remove()
    db.child("events").child(event_id).remove()


def delete_all_user_events():
    """
        Deletes all owned events from a user.
    """
    events = get_my_events()[1]
    for event_id in events:
        delete_event(event_id)


logged_out_data = {
    "first_name": "Guest",
    "last_name": "User",
    "email": "guest@user.com",
    "promotion": False,
    "role": "guest"
}
