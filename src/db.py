"""
    Database management methods for RoboRegistry
    @author: Lucas Bubner, 2023
"""
import math
from time import time

from requests.exceptions import HTTPError

from firebase_instance import db


def get_user_data(uid) -> dict:
    """
        Gets a user's info from the database.
    """
    try:
        data = db.child("users").child(uid).get().val()
    except KeyError:
        return {}
    if not data:
        return {}
    return dict(data)


def mutate_user_data(uid, info: dict) -> None:
    """
        Appends data for a user to the database.
    """
    db.child("users").child(uid).update(info)


def get_uid_for(event_id) -> str:
    """
        Find the event creator for an event.
    """
    return str(db.child("events").child(event_id).child("creator").get().val())


def add_event(uid, event):
    """
        Adds an event to the database.
    """
    db.child("events").child(uid).set(event)


def update_event(event_id, event):
    """
        Updates an event in the database.
    """
    db.child("events").child(event_id).update(event)


def get_event(event_id):
    """
        Gets an event from a creator from the database.
    """
    try:
        event = db.child("events").child(event_id).get().val()
        event = dict(event)
        event["uid"] = event_id
    except (HTTPError, TypeError):
        # Event does not exist
        return {}
    return event


def get_uid_for_entity(event_id, entity_id) -> str:
    """
        Find the entity creator for an entity.
    """
    # entity_id has the structure of '{TEAMNAME}, behalf of {CONTACTNAME}'
    event = get_event(event_id)
    if not event:
        return ""
    for uid, entity in event["registered_data"].items():
        if f"{entity['teamName'].upper()}, behalf of {entity['contactName']}" == entity_id:
            return uid
    return ""


def get_user_events(creator) -> tuple[dict, dict]:
    """
        Gets a user's events from the database.
        @return: (registered_events, owned_events)
    """
    try:
        events = db.child("events").get().val()
        registered_events = {}
        owned_events = {}
        for event_id, event_data in dict(events).items():
            if creator in event_data["registered"]:
                if event_data["creator"] == creator:
                    owned_events[event_id] = event_data
                    continue
                registered_events[event_id] = event_data
    except (HTTPError, TypeError):
        # Events do not exist
        return {}, {}
    return registered_events, owned_events


def get_my_events(uid) -> tuple[dict, dict]:
    """
        Get personally associated events from the database.
        @return: (registered_events, owned_events)
    """
    return get_user_events(uid)


def is_event_owner(uid, event_id):
    """
        Check if a user owns an event by checking if an event exists under their name.
    """
    event = db.child("events").child(event_id).child("creator").get().val()
    return event == uid


def delete_event(uid, event_id):
    """
        Deletes an event from the database.
    """
    if db.child("events").child(event_id).child("creator").get().val() != uid:
        return
    db.child("events").child(event_id).remove()


def delete_all_user_events(uid):
    """
        Deletes all events from a user.
    """
    db.child("events").child(uid).remove()


def refresh_excess(event_id):
    event = get_event(event_id)

    # Get all excess
    excess = []
    for uid, entity in event["registered"].items():
        if str(entity).startswith("excess"):
            excess.append((uid, entity))

    # Sort excess by unix time appended to the end by {n}-{unix}
    excess.sort(key=lambda x: int(x[1].split("-")[-1]))

    # Get the oldest excess, and update it to be no longer excess if the event is not full
    i = len(event["registered"]) - 1
    while excess and i < event["limit"]:
        entity = excess.pop(0)
        event["registered"][entity[0]] = math.floor(time())
        update_event(event_id, event)
        i += 1


logged_out_data = {
    "first_name": "Guest",
    "last_name": "User",
    "email": "guest@user.com",
    "promotion": "off",
    "role": "guest"
}
