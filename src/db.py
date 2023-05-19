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
