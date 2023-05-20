"""
    Firebase Realtime Database wrapper for RoboRegistry.
    @author: Lucas Bubner, 2023
"""
from firebase import Database
from collections import OrderedDict

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
    def add_event(self, uid, event) -> None:
        """
            Adds an event to the database.
        """
        self.db.child("events").child(self.uid).child(uid).set(event)

    def update_event(self, creator, event_id, event) -> None:
        """
            Updates an event in the database.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).child(event_id).update(event)

    def get_event(self, creator, event_id) -> dict:
        """
            Gets an event from a creator from the database.
        """
        event = self.db.child("events").child(creator).child(event_id).get().val()
        if isinstance(event, dict):
            return event
        else:
            return {}

    def get_user_events(self, creator) -> dict:
        """
            Gets a user's events from the database.
        """
        events = self.db.child("events").child(creator).get().val()
        if isinstance(events, list):
            return {i: events[i] for i in range(len(events))}
        elif isinstance(events, OrderedDict):
            return dict(events)
        else:
            return {}

    def get_my_events(self) -> dict or list:
        """
            Get personally owned events from the database.
        """
        return self.get_user_events(self.uid)
    
    def is_event_owner(self, event_id) -> bool:
        """
            Check if a user owns an event by checking if an event exists under their name.
        """
        event = self.db.child("events").child(self.uid).child(event_id).get().val()
        return event is not None
    
    def delete_event(self, creator, event_id) -> None:
        """
            Deletes an event from the database.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).child(event_id).remove()
    
    def delete_all_user_events(self, creator) -> None:
        """
            Deletes all events from a user.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).remove()
    

