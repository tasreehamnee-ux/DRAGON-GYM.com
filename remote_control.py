import os
import json
import firebase_admin
from firebase_admin import credentials, db

# Since we are moving to Flask, we don't strictly need PyQt6 signals here, 
# but we can use callbacks instead.
class RemoteControlListener:
    def __init__(self):
        self.is_locked = False
        self.is_closed = False
        self.on_lock_state_changed = None
        self.on_close_requested = None

    def start_listening(self):
        config_dir = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(config_dir, 'firebase_key.json')
        db_url_path = os.path.join(config_dir, 'firebase_url.txt')

        if not os.path.exists(key_path) or not os.path.exists(db_url_path):
            print("Firebase config files (firebase_key.json, firebase_url.txt) missing. Remote control disabled.")
            return

        try:
            with open(db_url_path, 'r', encoding='utf-8') as f:
                db_url = f.read().strip()
                
            client_id_path = os.path.join(config_dir, 'client_id.txt')
            client_id = 'client_1'
            if os.path.exists(client_id_path):
                with open(client_id_path, 'r', encoding='utf-8') as f:
                    client_id = f.read().strip()

            if not firebase_admin._apps:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': db_url
                })
            
            ref = db.reference(f'/clients/{client_id}')
            
            def listener(event):
                # We need to re-fetch the whole thing to be safe if only a child updated
                full_data = ref.get() or {}
                
                is_locked_remote = bool(full_data.get('is_locked', False))
                expiry_date_str = full_data.get('license_expiry_date', '')
                
                is_closed_remote = bool(
                    full_data.get('is_closed', False) or 
                    full_data.get('force_close', False) or 
                    full_data.get('should_close', False) or 
                    full_data.get('close_app', False)
                )
                
                try:
                    from business_logic import update_license_cache
                    update_license_cache(is_locked_remote, expiry_date_str)
                except Exception as e:
                    print(f"Error caching license: {e}")
                
                expired = False
                if expiry_date_str:
                    from datetime import datetime, date
                    try:
                        expiry = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                        if date.today() > expiry:
                            expired = True
                    except Exception:
                        pass
                
                self.is_locked = is_locked_remote or expired
                self.is_closed = is_closed_remote
                
                if self.on_lock_state_changed:
                    self.on_lock_state_changed(self.is_locked)
                
                if self.is_closed and self.on_close_requested:
                    print("Received remote close command from Firebase. Requesting app close...")
                    self.on_close_requested()

            ref.listen(listener)
            print(f"Firebase Remote Control Listener Started for client: {client_id}")
            
        except Exception as e:
            print(f"Error starting Firebase listener: {e}")

remote_control = RemoteControlListener()
