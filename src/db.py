"""
    Database management methods for RoboRegistry
    @author: Lucas Bubner, 2023
"""

import math
from time import time

from datetime import datetime
from pytz import timezone
from flask import session
from flask_login import current_user
from requests.exceptions import HTTPError

from firebase_instance import db


def get_user_data(uid) -> dict:
    """
        Gets a user's info from the database.
    """
    try:
        data = db.child("users").child(uid).get(session.get("id_token")).val()
    except KeyError:
        return {}
    if not data:
        return {}
    return dict(data)


def mutate_user_data(info: dict) -> None:
    """
        Appends user data in the database.
    """
    db.child("users").child(getattr(current_user, "id")).update(info, session.get("id_token"))


def get_uid_for(event_id) -> str:
    """
        Find the event creator for an event.
    """
    return str(db.child("events").child(event_id).child("creator").get(session.get("id_token")).val())


def add_event(uid, event):
    """
        Adds an event to the database.
    """
    toadd = {
        uid: {**event}
    }
    db.child("events").update(toadd, session.get("id_token"))


def add_entry(event_id, public_data, private_data):
    """
        Updates an event in the database to reflect a new registration.
    """
    public_data |= {
        "entity": f"{private_data['contactName']} | {private_data['repName'].upper()}",
        "checkin_data": {
            "checked_in": False,
            "time": 0
        }
    }
    db.child("events").child(event_id).child("registered").child(getattr(current_user, "id")).set(public_data, session.get("id_token"))
    db.child("registered_data").child(event_id).child(getattr(current_user, "id")).set(private_data, session.get("id_token"))


def remove_entry(event_id):
    """
        Removes an event registration from the database.
    """
    db.child("events").child(event_id).child("registered").child(getattr(current_user, "id")).remove(session.get("id_token"))
    db.child("registered_data").child(event_id).child(getattr(current_user, "id")).remove(session.get("id_token"))


def check_in(event_id):
    """
        Checks a user into an event.
    """
    db.child("events").child(event_id).child("registered").child(getattr(current_user, "id")).child("checkin_data").set({
        "checked_in": True,
        "time": math.floor(time())
    }, session.get("id_token"))


def get_event(event_id):
    """
        Gets an event from a creator from the database.
    """
    try:
        event = db.child("events").child(event_id).get(session.get("id_token")).val()
        event = dict(event)
        event["uid"] = event_id
    except (HTTPError, TypeError):
        # Event does not exist
        return {}
    return event


def unregister(event_id) -> bool:
    """
        Unregister from an event.
    """
    # Disallow unregistration if event has already started/ended
    event = get_event(event_id)
    tz = timezone(event["timezone"])
    tz.localize(datetime.strptime(event["date"] + event["start_time"], "%Y-%m-%d%H:%M"))
    if datetime.now(tz) > tz.localize(datetime.strptime(event["date"] + event["end_time"], "%Y-%m-%d%H:%M")):
        return False
    
    db.child("events").child(event_id).child("registered").child(getattr(current_user, "id")).remove(session.get("id_token"))
    db.child("registered_data").child(event_id).child(getattr(current_user, "id")).remove(session.get("id_token"))
    return True


def verify_unique(event_id, repname) -> bool:
    """
        Verify a team name is not already registered for an event.
    """
    all_registrations = db.child("events").child(event_id).child("registered").get(session.get("id_token")).val()
    try:
        all_registrations = dict(all_registrations)
    except TypeError:
        # No registrations, has to be unique
        return True
    for registration in all_registrations.values():
        if registration["entity"].split(" | ")[1].upper() == repname.upper():
            return False
    return True


def get_event_data(event_id):
    """
        Get registered data for an event.
        May only be accessed by the event owner.
    """
    try:
        event_data = db.child("registered_data").child(event_id).get(session.get("id_token")).val()
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


def get_my_events() -> tuple[dict, dict]:
    """
        Gets a user's events from the database.
        @return: (registered_events, owned_events)
    """
    try:
        events = db.child("events").get(session.get("id_token")).val()
        registered_events = {}
        owned_events = {}
        for event_id, event_data in dict(events).items():
            if event_data["creator"] == getattr(current_user, "id"):
                owned_events[event_id] = event_data
                continue
            if event_data.get("registered") and getattr(current_user, "id") in event_data["registered"]:
                registered_events[event_id] = event_data
    except (HTTPError, TypeError):
        # Events do not exist
        return {}, {}
    return registered_events, owned_events


def delete_event(event_id):
    """
        Deletes an event from the database.
    """
    if db.child("events").child(event_id).child("creator").get(session.get("id_token")).val() != getattr(current_user, "id"):
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
