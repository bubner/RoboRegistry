"""
    Firebase Realtime Database wrapper for RoboRegistry.
    @author: Lucas Bubner, 2023
"""
from firebase import Database
from collections import OrderedDict
from requests.exceptions import HTTPError

class Userdata:
    def __init__(self, db: Database, uid):
        self.db = db
        self.userinfo = None
        self.uid = uid

    def set_uid(self, uid) -> None:
        """
            Sets the user ID for usage in database operations.
        """
        self.uid = uid

    # ===== User Data =====
    def get_user_data(self) -> dict:
        """
            Gets a user's info from the database.
        """
        if self.userinfo is None:
            self.userinfo = self.db.child("users").child(self.uid).get().val()
        return dict(self.userinfo)

    def mutate_user_data(self, info: dict) -> None:
        """
            Appends data for a user to the database.
        """
        for key in info:
            self.db.child("users").child(self.uid).child(key).update(info[key])
        self.userinfo = None

    # ===== Events =====
    def get_uid_for(self, event_id) -> str:
        """
            Find the event creator for an event.
        """
        return str(self.db.child("events").child(event_id).child("creator").get().val())
    
    def add_event(self, uid, event):
        """
            Adds an event to the database.
        """
        self.db.child("events").child(uid).set(event)

    def update_event(self, event_id, event):
        """
            Updates an event in the database.
        """
        self.db.child("events").child(event_id).update(event)

    def get_event(self, event_id):
        """
            Gets an event from a creator from the database.
        """
        try:
            event = self.db.child("events").child(event_id).get().val()
            event = dict(event)
        except (HTTPError, TypeError):
            # Event does not exist
            return {}
        return event

    def get_user_events(self, creator) -> tuple[dict, dict]:
        """
            Gets a user's events from the database.
            @return: (registered_events, owned_events)
        """
        try:
            events = self.db.child("events").get().val()
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
            return ({}, {})
        return (registered_events, owned_events)

    def get_my_events(self) -> tuple[dict, dict]:
        """
            Get personally associated events from the database.
            @return: (registered_events, owned_events)
        """
        return self.get_user_events(self.uid)
    
    def is_event_owner(self, event_id):
        """
            Check if a user owns an event by checking if an event exists under their name.
        """
        event = self.db.child("events").child(event_id).child("owner").get().val()
        return event == self.uid
    
    def delete_event(self, event_id):
        """
            Deletes an event from the database.
        """
        if self.db.child("events").child(event_id).child("owner").get().val() != self.uid:
            return
        self.db.child("events").child(event_id).remove()
    
    def delete_all_user_events(self, creator):
        """
            Deletes all events from a user.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).remove()
    

