import os
import sys
import firebase_admin
from firebase_admin import credentials
from database import get_session, Member, Payment, Staff, Expense, AttendanceRecord
from firebase_db import (
    _ref, fb_add_member, fb_add_payment, fb_add_staff, 
    fb_add_expense, fb_log_attendance
)
from datetime import datetime

# Initialize Firebase
cred = credentials.Certificate("black-e91d4-firebase-adminsdk-fbsvc-289d2e6de9.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://black-e91d4-default-rtdb.firebaseio.com'
})

def migrate_data():
    print("بدء عملية نقل البيانات إلى السحابة...")
    session = get_session()
    try:
        # 1. Migrate Staff
        print("جاري نقل بيانات الكادر...")
        staff_members = session.query(Staff).all()
        for s in staff_members:
            _ref(f'/gym_data/staff/{s.id}').set({
                'id': s.id,
                'name': s.name,
                'phone': s.phone or '',
                'role': s.role or '',
                'salary': float(s.salary or 0),
                'salary_type': s.salary_type or ''
            })
        print(f"تم نقل {len(staff_members)} موظف.")

        # 2. Migrate Members
        print("جاري نقل بيانات المشتركين...")
        members = session.query(Member).all()
        for m in members:
            _ref(f'/gym_data/members/{m.id}').set({
                'id': m.id,
                'name': m.name or '',
                'phone': m.phone or '',
                'address': m.address or '',
                'landmark': m.landmark or '',
                'plan_name': m.plan_name or '',
                'price': float(m.price or 0),
                'notes': m.notes or '',
                'start_date': str(m.start_date) if m.start_date else '',
                'end_date': str(m.end_date) if m.end_date else '',
                'status': m.status or 'active',
                'payment_method': m.payment_method or '',
                'card_id': m.card_id or '',
                'trainer_name': m.trainer_name or '',
                'is_frozen': getattr(m, 'is_frozen', False),
                'frozen_date': str(getattr(m, 'frozen_date', '')) if getattr(m, 'frozen_date', None) else '',
                'last_return_date': str(getattr(m, 'last_return_date', '')) if getattr(m, 'last_return_date', None) else '',
                'has_face_registered': getattr(m, 'has_face_registered', False)
            })
        print(f"تم نقل {len(members)} مشترك.")

        # 3. Migrate Payments
        print("جاري نقل بيانات المدفوعات...")
        payments = session.query(Payment).all()
        for p in payments:
            _ref(f'/gym_data/payments/{p.id}').set({
                'id': p.id,
                'member_id': p.member_id,
                'amount': float(p.amount or 0),
                'payment_method': p.payment_method or '',
                'plan_name': p.plan_name or '',
                'receipt_number': p.receipt_number or '',
                'payment_date': str(p.payment_date) if p.payment_date else ''
            })
        print(f"تم نقل {len(payments)} دفعة.")

        # 4. Migrate Expenses
        print("جاري نقل بيانات المصروفات...")
        expenses = session.query(Expense).all()
        for e in expenses:
            _ref(f'/gym_data/expenses/{e.id}').set({
                'id': e.id,
                'title': e.title or '',
                'amount': float(e.amount or 0),
                'category': e.category or '',
                'notes': e.notes or '',
                'expense_date': str(e.expense_date) if e.expense_date else ''
            })
        print(f"تم نقل {len(expenses)} مصروف.")

        print("تمت عملية النقل بنجاح! 🚀")
        print("يمكنك الآن فتح الآيباد وستجد جميع بياناتك هناك.")
        
    except Exception as e:
        print(f"حدث خطأ أثناء النقل: {str(e)}")
    finally:
        session.close()

if __name__ == '__main__':
    migrate_data()
