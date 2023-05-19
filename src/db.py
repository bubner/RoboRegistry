"""
    Firebase Realtime Database wrapper for RoboRegistry.
    @author: Lucas Bubner, 2023
"""
from firebase import Database


class Userdata:
    def __init__(self, db: Database, uid):
        self.db = db
        self.uid = uid

    def set_uid(self, uid) -> None:
        """
            Sets the user ID.
        """
        self.uid = uid

    # ===== User Data =====
    def add_user_info(self, info) -> None:
        """
            Adds a user's info to the database.
        """
        self.db.child("users").child(self.uid).set(info)

    def get_user_info(self) -> dict or list:
        """
            Gets a user's info from the database.
        """
        return self.db.child("users").child(self.uid).get().val()

    def add_user_data(self, info) -> None:
        """
            Adds data for a user to the database.
        """
        if isinstance(info, dict):
            for key in info:
                self.db.child("users").child(
                    self.uid).child(key).set(info[key])
            return

        self.db.child("users").child(self.uid).set(info)

    # ===== Events =====
    def add_event(self, uid, event) -> str:
        """
            Adds an event to the database.
        """
        self.db.child("events").child(self.uid).child(uid).set(event)

    def get_user_events(self, creator) -> dict or list:
        """
            Gets a user's events from the database.
        """
        return self.db.child("events").child(creator).get().val()   

    def get_my_events(self) -> dict or list:
        """
            Get personally owned events from the database.
        """
        return self.get_user_events(self.uid)

    def get_event(self, creator, event_id) -> dict or list:
        """
            Gets an event from a creator from the database.
        """
        return self.db.child("events").child(creator).child(event_id).get().val()
    
    def delete_event(self, creator, event_id) -> None:
        """
            Deletes an event from the database.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).child(event_id).remove()

    def update_event(self, creator, event_id, event) -> None:
        """
            Updates an event in the database.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).child(event_id).update(event)
    
    def delete_all_user_events(self, creator) -> None:
        """
            Deletes all events from a user.
        """
        if creator != self.uid:
            return
        self.db.child("events").child(creator).remove()
    

