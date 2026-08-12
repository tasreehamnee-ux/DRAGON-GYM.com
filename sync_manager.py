import os
import sys
import firebase_admin
from firebase_admin import credentials, db
from threading import Thread

class SyncManager:
    def __init__(self):
        # Data saving in the cloud is disabled. All data is saved strictly locally in gym.db in the same directory.
        self.is_connected = False
        self.database_url = "https://black-e91d4-default-rtdb.firebaseio.com/"

    def _get_key_path(self):
        if hasattr(sys, '_MEIPASS'):
            p = os.path.join(sys._MEIPASS, 'firebase_key.json')
            if os.path.exists(p):
                return p
        p = os.path.join(os.path.dirname(__file__), 'firebase_key.json')
        if os.path.exists(p):
            return p
        return 'firebase_key.json'

    def _ensure_firebase_init(self):
        # Cloud data syncing disabled
        return False

    def _push_to_firebase(self, path: str, data: dict):
        # Cloud data saving disabled
        pass

    def sync_member(self, member_data: dict):
        """
        Cloud sync disabled: Data is saved strictly locally.
        """
        return False

    def delete_member(self, member_id: int):
        """
        Cloud delete disabled: Data is deleted strictly locally.
        """
        return False

# Initialize a global sync manager
sync_manager = SyncManager()


