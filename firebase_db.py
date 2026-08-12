"""
Firebase Realtime Database layer for DRAGON GYM.
Used when running on Vercel where SQLite is not persistent.
All data is stored under /gym_data/ in Firebase Realtime Database.
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, db as firebase_rtdb, storage
from datetime import date, datetime

_db_app = None

def _init_firebase_db():
    """Initialize Firebase app for database operations (named app to avoid conflicts)."""
    global _db_app
    if _db_app is not None:
        return _db_app

    config_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(config_dir, 'firebase_key.json')

    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
    else:
        # Check for Environment Variable (used in Vercel)
        firebase_env = os.environ.get('FIREBASE_CREDENTIALS')
        if not firebase_env:
            raise Exception("firebase_key.json not found and FIREBASE_CREDENTIALS environment variable is not set")
        try:
            cred_dict = json.loads(firebase_env)
            cred = credentials.Certificate(cred_dict)
        except Exception as e:
            raise Exception(f"Failed to parse FIREBASE_CREDENTIALS environment variable: {e}")

    try:
        _db_app = firebase_admin.get_app('gym_db')
    except ValueError:
        _db_app = firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://black-e91d4-default-rtdb.firebaseio.com/',
            'storageBucket': 'black-e91d4.appspot.com'
        }, name='gym_db')

    return _db_app


def _ref(path):
    """Get a Firebase Realtime Database reference."""
    app = _init_firebase_db()
    return firebase_rtdb.reference(path, app=app)


def _next_id(collection_path):
    """Generate next sequential ID for a collection."""
    data = _ref(collection_path).get() or {}
    if isinstance(data, list):
        keys = [i for i, d in enumerate(data) if d is not None]
    else:
        keys = [int(k) for k in data.keys() if str(k).isdigit()]
    if not keys:
        return 1
    return max(keys) + 1

def _get_list_from_data(data):
    if not data:
        return []
    if isinstance(data, list):
        return [d for d in data if d is not None]
    return list(data.values())


def _serialize_date(val):
    """Convert date/datetime to ISO string for Firebase storage."""
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return str(val)


def _parse_date(val):
    """Parse an ISO date string back to a date object."""
    if not val or val == 'None':
        return None
    try:
        return datetime.strptime(val[:10], '%Y-%m-%d').date()
    except Exception:
        return None


# ============================================================
# MEMBERS
# ============================================================

def fb_add_member(data):
    """Add a new member. Returns the new member ID."""
    member_id = _next_id('/gym_data/members')
    data['id'] = member_id
    data['created_at'] = datetime.now().isoformat()
    # Serialize dates
    for key in ['start_date', 'end_date', 'frozen_date', 'last_return_date']:
        if key in data:
            data[key] = _serialize_date(data[key])
    _ref(f'/gym_data/members/{member_id}').set(data)
    return member_id


def fb_update_member(member_id, updates):
    """Update specific fields of a member."""
    for key in ['start_date', 'end_date', 'frozen_date', 'last_return_date']:
        if key in updates:
            updates[key] = _serialize_date(updates[key])
    _ref(f'/gym_data/members/{member_id}').update(updates)


def fb_get_member(member_id):
    """Get a single member by ID. Returns dict or None."""
    return _ref(f'/gym_data/members/{member_id}').get()


def fb_get_all_members():
    """Get all members as a list of dicts."""
    data = _ref('/gym_data/members').get()
    return _get_list_from_data(data)


def fb_find_member_by_name(name):
    """Find a member by name (case-insensitive)."""
    if not name:
        return None
    name_lower = name.strip().lower()
    for m in fb_get_all_members():
        if m.get('name', '').strip().lower() == name_lower:
            return m
    return None


def fb_find_member_by_card(card_id):
    """Find a member by card/RFID ID."""
    for m in fb_get_all_members():
        if m.get('card_id') == card_id:
            return m
    return None


def fb_delete_member(member_id):
    """Delete a member and their associated payments."""
    _ref(f'/gym_data/members/{member_id}').delete()
    # Delete associated payments
    payments = _ref('/gym_data/payments').get() or {}
    for pid, p in payments.items():
        if p.get('member_id') == member_id:
            _ref(f'/gym_data/payments/{pid}').delete()


def fb_count_members(status=None):
    """Count members, optionally filtered by status."""
    members = fb_get_all_members()
    if status:
        return len([m for m in members if m.get('status') == status])
    return len(members)


# ============================================================
# PAYMENTS
# ============================================================

def fb_add_payment(data):
    """Add a new payment. Returns the payment ID."""
    payment_id = _next_id('/gym_data/payments')
    data['id'] = payment_id
    if 'payment_date' in data:
        data['payment_date'] = _serialize_date(data['payment_date'])
    _ref(f'/gym_data/payments/{payment_id}').set(data)
    return payment_id


def fb_get_all_payments():
    """Get all payments."""
    data = _ref('/gym_data/payments').get()
    return _get_list_from_data(data)


def fb_get_payments_by_member(member_id):
    """Get payments for a specific member."""
    return [p for p in fb_get_all_payments() if p.get('member_id') == member_id]


def fb_delete_payment(payment_id):
    """Delete a payment by ID."""
    _ref(f'/gym_data/payments/{payment_id}').delete()


def fb_delete_payments_by_member(member_id):
    """Delete all payments for a member."""
    payments = _ref('/gym_data/payments').get() or {}
    for pid, p in payments.items():
        if p.get('member_id') == member_id:
            _ref(f'/gym_data/payments/{pid}').delete()


def fb_get_last_payment_id():
    """Get the highest payment ID."""
    payments = _ref('/gym_data/payments').get() or {}
    if not payments:
        return 0
    return max(int(k) for k in payments.keys())


# ============================================================
# PLANS
# ============================================================

def fb_get_all_plans():
    """Get all subscription plans."""
    data = _ref('/gym_data/plans').get()
    return _get_list_from_data(data)


def fb_add_plan(name, price, duration_days):
    """Add a new plan. Returns (True, msg) or (False, msg)."""
    existing = fb_find_plan_by_name(name)
    if existing:
        return False, "اسم الاشتراك موجود مسبقاً"
    plan_id = _next_id('/gym_data/plans')
    _ref(f'/gym_data/plans/{plan_id}').set({
        'id': plan_id,
        'name': name,
        'price': float(price),
        'duration_days': int(duration_days)
    })
    return True, "تم الإضافة بنجاح"


def fb_find_plan_by_name(name):
    """Find a plan by name."""
    for p in fb_get_all_plans():
        if p.get('name') == name:
            return p
    return None


def fb_update_plan(plan_id, name, price, duration_days):
    """Update a plan."""
    _ref(f'/gym_data/plans/{plan_id}').update({
        'name': name,
        'price': float(price),
        'duration_days': int(duration_days)
    })


def fb_delete_plan(plan_id):
    """Delete a plan."""
    plan = _ref(f'/gym_data/plans/{plan_id}').get()
    if plan:
        _ref(f'/gym_data/plans/{plan_id}').delete()
        return True, "تم الحذف"
    return False, "الاشتراك غير موجود"


def fb_init_default_plans():
    """Initialize default plans if none exist."""
    if len(fb_get_all_plans()) == 0:
        defaults = [
            ('VIP شهري', 75000, 30),
            ('خاص شهري', 50000, 30),
            ('شهري', 35000, 30),
            ('أسبوعي', 12000, 7),
            ('يومي', 3000, 1),
            ('3 أشهر', 90000, 90),
        ]
        for name, price, days in defaults:
            fb_add_plan(name, price, days)


# ============================================================
# SETTINGS
# ============================================================

def fb_get_settings():
    """Get system settings."""
    data = _ref('/gym_data/settings').get()
    if not data:
        data = {
            'gym_name': 'نظام القاعة الرياضية',
            'gym_phone': '',
            'gym_address': '',
            'door_com_port': '',
            'license_expiry_date': '',
            'is_locally_locked': False
        }
        _ref('/gym_data/settings').set(data)
    return data


def fb_update_settings(updates):
    """Update system settings."""
    _ref('/gym_data/settings').update(updates)


# ============================================================
# ATTENDANCE
# ============================================================

def fb_log_attendance(member_id):
    """Log attendance for a member."""
    att_id = _next_id('/gym_data/attendance')
    _ref(f'/gym_data/attendance/{att_id}').set({
        'id': att_id,
        'member_id': member_id,
        'entry_time': datetime.now().isoformat()
    })


def fb_get_today_attendance():
    """Get today's attendance records with member names."""
    today_str = date.today().isoformat()
    all_att = _ref('/gym_data/attendance').get()
    att_list = _get_list_from_data(all_att)
    members = {m['id']: m for m in fb_get_all_members() if 'id' in m}

    today_records = []
    for att in att_list:
        entry_time = att.get('entry_time', '')
        if entry_time.startswith(today_str):
            member = members.get(att.get('member_id'))
            member_name = member.get('name', 'غير معروف') if member else 'غير معروف'
            try:
                time_str = datetime.fromisoformat(entry_time).strftime('%H:%M')
            except Exception:
                time_str = ''
            today_records.append({
                'member_name': member_name,
                'time': time_str
            })
    return sorted(today_records, key=lambda x: x['time'], reverse=True)


# ============================================================
# EXPENSES
# ============================================================

def fb_add_expense(title, amount, category, notes=''):
    """Add an expense."""
    exp_id = _next_id('/gym_data/expenses')
    _ref(f'/gym_data/expenses/{exp_id}').set({
        'id': exp_id,
        'title': title,
        'amount': float(amount),
        'expense_date': date.today().isoformat(),
        'category': category,
        'notes': notes
    })
    return True, "تم إضافة المصروف بنجاح"


def fb_get_expenses(month=None, year=None):
    """Get expenses with optional filtering."""
    data = _ref('/gym_data/expenses').get()
    expenses = _get_list_from_data(data)
    if month and year:
        prefix = f'{year}-{int(month):02d}'
        expenses = [e for e in expenses if e.get('expense_date', '').startswith(prefix)]
    return sorted(expenses, key=lambda x: x.get('expense_date', ''), reverse=True)


def fb_delete_expense(expense_id):
    """Delete an expense."""
    exp = _ref(f'/gym_data/expenses/{expense_id}').get()
    if exp:
        _ref(f'/gym_data/expenses/{expense_id}').delete()
        return True, "تم حذف المصروف"
    return False, "المصروف غير موجود"


# ============================================================
# STAFF
# ============================================================

def fb_add_staff(name, phone, role, salary, salary_type):
    """Add a staff member."""
    if isinstance(salary, str):
        salary = salary.replace(',', '').replace(' ', '')
    try:
        salary_val = float(salary)
    except (ValueError, TypeError):
        salary_val = 0.0

    staff_id = _next_id('/gym_data/staff')
    _ref(f'/gym_data/staff/{staff_id}').set({
        'id': staff_id,
        'name': name,
        'phone': phone or '',
        'role': role,
        'salary': salary_val,
        'salary_type': salary_type
    })
    return True, "تم الحفظ بنجاح"


def fb_get_all_staff():
    """Get all staff members."""
    data = _ref('/gym_data/staff').get()
    return _get_list_from_data(data)


def fb_find_staff_by_name(name):
    """Find staff by name (case-insensitive)."""
    if not name:
        return None
    name_lower = name.strip().lower()
    for s in fb_get_all_staff():
        if s.get('name', '').strip().lower() == name_lower:
            return s
    return None


def fb_delete_staff(staff_id):
    """Delete a staff member."""
    staff = _ref(f'/gym_data/staff/{staff_id}').get()
    if staff:
        _ref(f'/gym_data/staff/{staff_id}').delete()
        return True, "تم الحذف"
    return False, "غير موجود"


def fb_update_staff(staff_id, name, phone, role, salary, salary_type):
    """Update a staff member."""
    staff = _ref(f'/gym_data/staff/{staff_id}').get()
    if not staff:
        return False, "عضو الكادر غير موجود"
    if isinstance(salary, str):
        salary = salary.replace(',', '').replace(' ', '')
    try:
        salary_val = float(salary)
    except (ValueError, TypeError):
        salary_val = 0.0

    _ref(f'/gym_data/staff/{staff_id}').update({
        'name': name,
        'phone': phone or '',
        'role': role,
        'salary': salary_val,
        'salary_type': salary_type
    })
    return True, "تم تعديل بيانات الكادر بنجاح"


# ============================================================
# FIREBASE STORAGE - Face Model
# ============================================================

def fb_upload_face_model(local_path):
    """Upload face_model.yml to Firebase Storage."""
    try:
        app = _init_firebase_db()
        bucket = storage.bucket(app=app)
        blob = bucket.blob('face_model.yml')
        blob.upload_from_filename(local_path)
        return True
    except Exception as e:
        print(f"Error uploading face model: {e}")
        return False


def fb_download_face_model(local_path):
    """Download face_model.yml from Firebase Storage to local path."""
    try:
        app = _init_firebase_db()
        bucket = storage.bucket(app=app)
        blob = bucket.blob('face_model.yml')
        if blob.exists():
            blob.download_to_filename(local_path)
            return True
        return False
    except Exception as e:
        print(f"Error downloading face model: {e}")
        return False
