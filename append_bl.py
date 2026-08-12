code = """

def log_attendance(member_id):
    session = get_session()
    try:
        log = AttendanceLog(member_id=member_id)
        session.add(log)
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

def get_today_attendance():
    session = get_session()
    try:
        today = date.today()
        records = session.query(AttendanceLog, Member).join(Member).filter(
            func.date(AttendanceLog.entry_time) == today
        ).order_by(AttendanceLog.entry_time.desc()).all()
        return [{"member_name": m.name, "time": log.entry_time.strftime("%H:%M")} for log, m in records]
    finally:
        session.close()

def add_expense(title, amount, category, notes=""):
    session = get_session()
    try:
        exp = Expense(title=title, amount=float(amount), category=category, notes=notes)
        session.add(exp)
        session.commit()
        return True, "تم إضافة المصروف بنجاح"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def get_expenses(month=None, year=None):
    session = get_session()
    try:
        query = session.query(Expense)
        if month and year:
            query = query.filter(extract('month', Expense.expense_date) == month, extract('year', Expense.expense_date) == year)
        return query.order_by(Expense.expense_date.desc()).all()
    finally:
        session.close()
        
def delete_expense(expense_id):
    session = get_session()
    try:
        exp = session.query(Expense).get(expense_id)
        if exp:
            session.delete(exp)
            session.commit()
            return True, "تم حذف المصروف"
        return False, "المصروف غير موجود"
    finally:
        session.close()

def add_staff(name, phone, role, salary, salary_type):
    session = get_session()
    try:
        staff = Staff(name=name, phone=phone, role=role, salary=float(salary), salary_type=salary_type)
        session.add(staff)
        session.commit()
        return True, "تم الحفظ بنجاح"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def get_all_staff():
    session = get_session()
    try:
        return session.query(Staff).all()
    finally:
        session.close()

def delete_staff(staff_id):
    session = get_session()
    try:
        staff = session.query(Staff).get(staff_id)
        if staff:
            session.delete(staff)
            session.commit()
            return True, "تم الحذف"
        return False, "غير موجود"
    finally:
        session.close()
"""

with open('business_logic.py', 'a', encoding='utf-8') as f:
    f.write(code)
print("Code appended successfully!")
