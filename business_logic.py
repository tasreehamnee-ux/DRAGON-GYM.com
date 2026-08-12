from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, extract
from database import get_session, Member, Payment, Settings, SubscriptionPlan, AttendanceLog, Expense, Staff, USE_FIREBASE
from sync_manager import sync_manager

# Import Firebase DB layer (only used when USE_FIREBASE is True)
if USE_FIREBASE:
    from firebase_db import (
        fb_get_all_members, fb_get_member, fb_add_member, fb_update_member,
        fb_delete_member, fb_find_member_by_name, fb_find_member_by_card, fb_count_members,
        fb_add_payment, fb_get_all_payments, fb_get_payments_by_member,
        fb_delete_payments_by_member, fb_get_last_payment_id, fb_delete_payment,
        fb_get_all_plans, fb_add_plan, fb_find_plan_by_name, fb_update_plan,
        fb_delete_plan, fb_init_default_plans,
        fb_get_settings, fb_update_settings,
        fb_log_attendance, fb_get_today_attendance,
        fb_add_expense, fb_get_expenses, fb_delete_expense,
        fb_add_staff, fb_get_all_staff, fb_find_staff_by_name,
        fb_delete_staff, fb_update_staff,
        _parse_date
    )

def get_settings():
    if USE_FIREBASE:
        data = fb_get_settings()
        # Return a simple object with attribute access
        class SettingsObj:
            pass
        s = SettingsObj()
        s.gym_name = data.get('gym_name', 'نظام القاعة الرياضية')
        s.gym_phone = data.get('gym_phone', '')
        s.gym_address = data.get('gym_address', '')
        s.door_com_port = data.get('door_com_port', '')
        s.license_expiry_date = data.get('license_expiry_date', '')
        s.is_locally_locked = data.get('is_locally_locked', False)
        return s
    session = get_session()
    try:
        settings = session.query(Settings).first()
        if not settings:
            settings = Settings()
            session.add(settings)
            session.commit()
            session.refresh(settings)
        session.expunge(settings)
        return settings
    finally:
        session.close()

def update_settings(gym_name, gym_phone, gym_address="", door_com_port="", license_expiry_date="", is_locally_locked=False):
    if USE_FIREBASE:
        try:
            fb_update_settings({
                'gym_name': gym_name, 'gym_phone': gym_phone,
                'gym_address': gym_address, 'door_com_port': door_com_port,
                'license_expiry_date': license_expiry_date,
                'is_locally_locked': is_locally_locked
            })
            return True
        except Exception as e:
            print(f"Error updating settings: {e}")
            return False
    session = get_session()
    try:
        settings = session.query(Settings).first()
        if not settings:
            settings = Settings()
            session.add(settings)
            
        settings.gym_name = gym_name
        settings.gym_phone = gym_phone
        settings.gym_address = gym_address
        settings.door_com_port = door_com_port
        settings.license_expiry_date = license_expiry_date
        settings.is_locally_locked = is_locally_locked
        session.commit()
        return True
    except Exception as e:
        print(f"Error updating settings: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def update_license_cache(is_locked, expiry_date):
    if USE_FIREBASE:
        try:
            updates = {'is_locally_locked': is_locked}
            if expiry_date is not None:
                updates['license_expiry_date'] = expiry_date
            fb_update_settings(updates)
        except Exception as e:
            print(f"Error updating license cache: {e}")
        return
    session = get_session()
    try:
        settings = session.query(Settings).first()
        if settings:
            settings.is_locally_locked = is_locked
            if expiry_date is not None:
                settings.license_expiry_date = expiry_date
            session.commit()
    except Exception as e:
        print(f"Error updating license cache: {e}")
        session.rollback()
    finally:
        session.close()

def get_all_plans():
    if USE_FIREBASE:
        plans = fb_get_all_plans()
        return [{"id": p.get('id'), "name": p.get('name'), "price": p.get('price'), "duration_days": p.get('duration_days')} for p in plans]
    session = get_session()
    try:
        plans = session.query(SubscriptionPlan).all()
        return [{"id": p.id, "name": p.name, "price": p.price, "duration_days": p.duration_days} for p in plans]
    finally:
        session.close()

def add_plan(name, price, duration_days):
    if USE_FIREBASE:
        return fb_add_plan(name, price, duration_days)
    session = get_session()
    try:
        if session.query(SubscriptionPlan).filter_by(name=name).first():
            return False, "اسم الاشتراك موجود مسبقاً"
        plan = SubscriptionPlan(name=name, price=float(price), duration_days=int(duration_days))
        session.add(plan)
        session.commit()
        return True, "تم الإضافة بنجاح"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def update_plan_price_or_create(name, price, duration_days):
    if USE_FIREBASE:
        existing = fb_find_plan_by_name(name)
        if existing:
            fb_update_plan(existing['id'], name, price, duration_days)
        else:
            fb_add_plan(name, price, duration_days)
        return True, "تم الحفظ"
    session = get_session()
    try:
        plan = session.query(SubscriptionPlan).filter_by(name=name).first()
        if plan:
            plan.price = float(price)
            plan.duration_days = int(duration_days)
        else:
            plan = SubscriptionPlan(name=name, price=float(price), duration_days=int(duration_days))
            session.add(plan)
        session.commit()
        return True, "تم الحفظ"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def delete_plan(plan_id):
    if USE_FIREBASE:
        return fb_delete_plan(plan_id)
    session = get_session()
    try:
        plan = session.query(SubscriptionPlan).get(plan_id)
        if plan:
            session.delete(plan)
            session.commit()
            return True, "تم الحذف"
        return False, "الاشتراك غير موجود"
    finally:
        session.close()

def get_plan_config():
    plans = get_all_plans()
    config = {}
    for p in plans:
        config[p['name']] = {'price': p['price'], 'duration': p['duration_days'], 'unit': 'day'}
    return config

def calculate_end_date(start_date: date, plan_name: str) -> date:
    config = get_plan_config()
    if plan_name not in config:
        return start_date
    
    plan = config[plan_name]
    # For better UX, if duration is roughly a month (30 days), we can use relativedelta(months=1)
    # But sticking to exact days is more accurate for manual entries.
    days = plan['duration']
    if days == 30:
        return start_date + relativedelta(months=1)
    elif days == 90:
        return start_date + relativedelta(months=3)
    elif days == 180:
        return start_date + relativedelta(months=6)
    elif days == 365 or days == 360:
        return start_date + relativedelta(years=1)
    else:
        return start_date + timedelta(days=days)

def get_plan_price(plan_name: str) -> float:
    config = get_plan_config()
    if plan_name in config:
        return config[plan_name]['price']
    return 0.0

import time

def add_new_member(name, phone, address, landmark, plan_name, start_date, payment_method, notes="", receipt_number="", is_pending=False, card_id=None, trainer_name=""):
    price = get_plan_price(plan_name)
    end_date = calculate_end_date(start_date, plan_name)
    member_status = 'pending' if is_pending else 'active'
    clean_name = name.strip() if name else ""
    clean_phone = phone.strip() if phone else ""
    clean_trainer = trainer_name.strip() if trainer_name else ""

    if USE_FIREBASE:
        try:
            existing = fb_find_member_by_name(clean_name) if clean_name else None
            is_renewal = existing is not None

            if existing:
                member_id = existing['id']
                fb_update_member(member_id, {
                    'name': clean_name or existing.get('name'),
                    'phone': clean_phone or existing.get('phone'),
                    'address': address or existing.get('address'),
                    'landmark': landmark or existing.get('landmark'),
                    'plan_name': plan_name, 'price': price,
                    'notes': notes or existing.get('notes'),
                    'start_date': start_date, 'end_date': end_date,
                    'status': member_status, 'payment_method': payment_method,
                    'card_id': card_id or existing.get('card_id'),
                    'trainer_name': clean_trainer,
                    'is_frozen': False, 'frozen_date': None
                })
            else:
                member_id = fb_add_member({
                    'name': clean_name, 'phone': clean_phone,
                    'address': address, 'landmark': landmark,
                    'plan_name': plan_name, 'price': price, 'notes': notes,
                    'start_date': start_date, 'end_date': end_date,
                    'status': member_status, 'payment_method': payment_method,
                    'card_id': card_id, 'trainer_name': clean_trainer,
                    'is_frozen': False, 'has_face_registered': False
                })

            # Save trainer as staff
            if clean_trainer and not fb_find_staff_by_name(clean_trainer):
                fb_add_staff(clean_trainer, '', 'مدرب', 0.0, 'ثابت')

            # Generate receipt number
            if not receipt_number or not str(receipt_number).strip():
                last_id = fb_get_last_payment_id()
                receipt_number = f"REC-{last_id + 1}"

            # Add payment
            fb_add_payment({
                'member_id': member_id, 'amount': price,
                'payment_method': payment_method, 'payment_date': start_date,
                'plan_name': plan_name, 'receipt_number': str(receipt_number).strip()
            })

            msg = "تم تجديد اشتراك المشترك بنجاح" if is_renewal else "تم إضافة المشترك بنجاح"
            return True, msg, member_id
        except Exception as e:
            return False, str(e), None

    session = get_session()
    try:
        # Check if member already exists by exact name
        existing_member = None
        if clean_name:
            existing_member = session.query(Member).filter(func.lower(Member.name) == func.lower(clean_name)).first()
            if not existing_member:
                all_m = session.query(Member).all()
                for m in all_m:
                    if m.name and m.name.strip().lower() == clean_name.lower():
                        existing_member = m
                        break
                        
        if existing_member:
            target_member = existing_member
            target_member.name = clean_name or target_member.name
            target_member.phone = clean_phone or target_member.phone
            target_member.address = address or target_member.address
            target_member.landmark = landmark or target_member.landmark
            target_member.plan_name = plan_name
            target_member.price = price
            target_member.notes = notes or target_member.notes
            target_member.start_date = start_date
            target_member.end_date = end_date
            target_member.status = member_status
            target_member.payment_method = payment_method
            if card_id:
                target_member.card_id = card_id
            target_member.trainer_name = clean_trainer
            target_member.is_frozen = False
            target_member.frozen_date = None
        else:
            target_member = Member(
                name=clean_name,
                phone=clean_phone,
                address=address,
                landmark=landmark,
                plan_name=plan_name,
                price=price,
                notes=notes,
                start_date=start_date,
                end_date=end_date,
                status=member_status,
                payment_method=payment_method,
                card_id=card_id,
                trainer_name=clean_trainer
            )
            session.add(target_member)

        # Ensure trainer is saved in Staff table so it stays in the dropdown permanently
        if clean_trainer:
            existing_staff = session.query(Staff).filter(func.lower(Staff.name) == func.lower(clean_trainer)).first()
            if not existing_staff:
                new_staff = Staff(name=clean_trainer, role='مدرب', salary=0.0, salary_type='ثابت')
                session.add(new_staff)
            
        session.flush() 
        
        if not receipt_number or not str(receipt_number).strip():
            last_payment = session.query(Payment).order_by(Payment.id.desc()).first()
            next_id = (last_payment.id + 1) if last_payment else 1
            receipt_number = f"REC-{next_id}"
            
        new_payment = Payment(
            member_id=target_member.id,
            amount=price,
            payment_method=payment_method,
            payment_date=start_date,
            plan_name=plan_name,
            receipt_number=str(receipt_number).strip()
        )
        session.add(new_payment)
        
        session.commit()
        
        sync_manager.sync_member({
            'id': target_member.id,
            'name': target_member.name,
            'trainer_name': target_member.trainer_name or '',
            'phone': target_member.phone,
            'email': target_member.email,
            'plan_name': target_member.plan_name,
            'price': target_member.price,
            'start_date': str(target_member.start_date),
            'end_date': str(target_member.end_date),
            'status': target_member.status,
            'payment_method': target_member.payment_method
        })
        
        msg = "تم تجديد اشتراك المشترك بنجاح" if existing_member else "تم إضافة المشترك بنجاح"
        return True, msg, target_member.id
    except Exception as e:
        session.rollback()
        return False, str(e), None
    finally:
        session.close()

def get_member_by_card_id(card_id: str):
    if USE_FIREBASE:
        return fb_find_member_by_card(card_id)
    session = get_session()
    try:
        return session.query(Member).filter(Member.card_id == card_id).first()
    finally:
        session.close()

def activate_pending_member(member_id):
    if USE_FIREBASE:
        try:
            member = fb_get_member(member_id)
            if not member or member.get('status') != 'pending':
                return False, "المشترك غير موجود أو ليس قيد الانتظار"
            today = date.today()
            fb_update_member(member_id, {
                'start_date': today,
                'end_date': calculate_end_date(today, member.get('plan_name', '')),
                'status': 'active'
            })
            return True, "تم تفعيل المشترك بنجاح وبدء اشتراكه من اليوم"
        except Exception as e:
            return False, str(e)
    session = get_session()
    try:
        member = session.query(Member).get(member_id)
        if not member or member.status != 'pending':
            return False, "المشترك غير موجود أو ليس قيد الانتظار"
            
        today = date.today()
        member.start_date = today
        member.end_date = calculate_end_date(today, member.plan_name)
        member.status = 'active'
        session.commit()
        return True, "تم تفعيل المشترك بنجاح وبدء اشتراكه من اليوم"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def freeze_membership(member_id: int, manual_freeze_date: date):
    """Freezes membership starting from a specific manual date."""
    if USE_FIREBASE:
        try:
            member = fb_get_member(member_id)
            if not member:
                return False, "العضو غير موجود"
            if member.get('is_frozen'):
                return False, "الاشتراك مجمد مسبقاً"
            m_end = _parse_date(member.get('end_date'))
            m_start = _parse_date(member.get('start_date'))
            if m_end and m_end < manual_freeze_date:
                return False, "تاريخ التجميد بعد تاريخ انتهاء الاشتراك!"
            if m_start and manual_freeze_date < m_start:
                return False, "لا يمكن تجميد الاشتراك قبل تاريخ البدء"
            remaining_days = (m_end - manual_freeze_date).days if m_end else 0
            if remaining_days <= 0:
                return False, "لا توجد أيام متبقية للتجميد"
            fb_update_member(member_id, {
                'is_frozen': True, 'frozen_date': manual_freeze_date,
                'remaining_days_when_frozen': remaining_days, 'status': 'frozen'
            })
            return True, f"تم تجميد الاشتراك. الأيام المتبقية المحفوظة: {remaining_days} يوم"
        except Exception as e:
            return False, str(e)
    session = get_session()
    try:
        member = session.query(Member).filter(Member.id == member_id).first()
        if not member:
            return False, "العضو غير موجود"
            
        if member.is_frozen:
            return False, "الاشتراك مجمد مسبقاً"
            
        if member.end_date < manual_freeze_date:
            return False, "تاريخ التجميد بعد تاريخ انتهاء الاشتراك!"
            
        if manual_freeze_date < member.start_date:
             return False, "لا يمكن تجميد الاشتراك قبل تاريخ البدء"
             
        remaining_days = (member.end_date - manual_freeze_date).days
        
        if remaining_days <= 0:
             return False, "لا توجد أيام متبقية للتجميد في هذا التاريخ"
        
        member.is_frozen = True
        member.frozen_date = manual_freeze_date
        member.remaining_days_when_frozen = remaining_days
        member.status = 'frozen'
        
        session.commit()
        
        sync_manager.sync_member({
            'id': member.id,
            'is_frozen': member.is_frozen,
            'frozen_date': str(member.frozen_date) if member.frozen_date else None,
            'status': member.status,
            'remaining_days_when_frozen': member.remaining_days_when_frozen
        })
        
        return True, f"تم تجميد الاشتراك. الأيام المتبقية المحفوظة: {remaining_days} يوم"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def unfreeze_membership(member_id: int, manual_return_date: date):
    """Unfreezes membership assuming they returned on a specific manual date."""
    if USE_FIREBASE:
        try:
            member = fb_get_member(member_id)
            if not member:
                return False, "العضو غير موجود"
            if not member.get('is_frozen'):
                return False, "الاشتراك غير مجمد"
            m_frozen = _parse_date(member.get('frozen_date'))
            if m_frozen and manual_return_date < m_frozen:
                return False, "تاريخ العودة يجب أن يكون بعد تاريخ التجميد!"
            remaining = member.get('remaining_days_when_frozen', 0)
            new_end_date = manual_return_date + timedelta(days=remaining)
            fb_update_member(member_id, {
                'end_date': new_end_date, 'is_frozen': False,
                'frozen_date': None, 'status': 'active',
                'last_return_date': manual_return_date
            })
            return True, f"تم إلغاء التجميد. تاريخ الانتهاء الجديد هو: {new_end_date.strftime('%Y-%m-%d')}"
        except Exception as e:
            return False, str(e)
    session = get_session()
    try:
        member = session.query(Member).filter(Member.id == member_id).first()
        if not member:
            return False, "العضو غير موجود"
            
        if not member.is_frozen:
            return False, "الاشتراك غير مجمد"
            
        if manual_return_date < member.frozen_date:
             return False, "تاريخ العودة يجب أن يكون بعد تاريخ التجميد!"
        
        new_end_date = manual_return_date + timedelta(days=member.remaining_days_when_frozen)
        
        # Reset freeze info, but optionally we could keep a log of freezes in a new table if needed.
        member.end_date = new_end_date
        member.is_frozen = False
        member.frozen_date = None
        member.status = 'active'
        member.last_return_date = manual_return_date
        
        session.commit()
        
        sync_manager.sync_member({
            'id': member.id,
            'is_frozen': member.is_frozen,
            'frozen_date': None,
            'last_return_date': str(manual_return_date),
            'end_date': str(member.end_date),
            'status': member.status,
            'remaining_days_when_frozen': 0
        })
        
        return True, f"تم إلغاء التجميد. تاريخ الانتهاء الجديد هو: {new_end_date.strftime('%Y-%m-%d')}"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def update_member_statuses():
    if USE_FIREBASE:
        today = date.today()
        for m in fb_get_all_members():
            if m.get('status') == 'active':
                m_end = _parse_date(m.get('end_date'))
                if m_end and m_end < today:
                    fb_update_member(m['id'], {'status': 'expired'})
        return
    session = get_session()
    try:
        today = date.today()
        members = session.query(Member).filter(Member.status == 'active', Member.end_date < today).all()
        for member in members:
            member.status = 'expired'
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()

def get_dashboard_stats():
    if USE_FIREBASE:
        today = date.today()
        members = fb_get_all_members()
        total_members = len(members)
        active_members = len([m for m in members if m.get('status') == 'active'])
        frozen_members = len([m for m in members if m.get('status') == 'frozen'])
        expired_members = len([m for m in members if m.get('status') == 'expired'])
        expiring_threshold = today + timedelta(days=7)
        expiring_members = 0
        for m in members:
            if m.get('status') == 'active':
                m_end = _parse_date(m.get('end_date'))
                if m_end and today <= m_end <= expiring_threshold:
                    expiring_members += 1
        # Revenue
        current_month = today.month
        current_year = today.year
        month_prefix = f'{current_year}-{current_month:02d}'
        payments = fb_get_all_payments()
        total_revenue = sum(p.get('amount', 0) for p in payments if str(p.get('payment_date', '')).startswith(month_prefix))
        # Expenses
        expenses = fb_get_expenses(current_month, current_year)
        total_expenses = sum(e.get('amount', 0) for e in expenses)
        # Staff salaries
        staff_list = fb_get_all_staff()
        for s in staff_list:
            sal = s.get('salary', 0) or 0
            if not sal: continue
            if s.get('salary_type') and ('نسبة' in str(s.get('salary_type')) or '%' in str(s.get('salary_type'))):
                total_expenses += total_revenue * (sal / 100.0)
            else:
                total_expenses += sal
        return {
            'total_members': total_members, 'active_members': active_members,
            'frozen_members': frozen_members, 'expired_members': expired_members,
            'expiring_members': expiring_members, 'revenue_this_month': total_revenue,
            'expenses_this_month': total_expenses, 'net_profit': total_revenue - total_expenses
        }
    session = get_session()
    try:
        today = date.today()
        total_members = session.query(Member).count()
        active_members = session.query(Member).filter(Member.status == 'active').count()
        frozen_members = session.query(Member).filter(Member.status == 'frozen').count()
        expired_members = session.query(Member).filter(Member.status == 'expired').count()
        
        expiring_threshold = today + timedelta(days=7)
        expiring_members = session.query(Member).filter(
            Member.status == 'active',
            Member.end_date >= today,
            Member.end_date <= expiring_threshold
        ).count()
        
        current_month = today.month
        current_year = today.year
        start_of_month = date(current_year, current_month, 1)
        if current_month == 12:
            next_month = date(current_year + 1, 1, 1)
        else:
            next_month = date(current_year, current_month + 1, 1)
            
        revenue_this_month = session.query(Payment).filter(
            Payment.payment_date >= start_of_month,
            Payment.payment_date < next_month
        ).with_entities(Payment.amount).all()
        
        total_revenue = sum(r[0] for r in revenue_this_month if r[0] is not None)
        
        expenses_this_month = session.query(Expense).filter(
            Expense.expense_date >= start_of_month,
            Expense.expense_date < next_month
        ).with_entities(Expense.amount).all()
        
        total_expenses = sum(e[0] for e in expenses_this_month if e[0] is not None)
        
        # Include Staff salaries
        staff_members = session.query(Staff).all()
        total_staff_salaries = 0.0
        for s in staff_members:
            if not s.salary: continue
            if s.salary_type and ("نسبة" in s.salary_type or "%" in s.salary_type):
                total_staff_salaries += total_revenue * (s.salary / 100.0)
            else:
                total_staff_salaries += s.salary
        total_expenses += total_staff_salaries
        
        net_profit = total_revenue - total_expenses
        
        return {
            'total_members': total_members,
            'active_members': active_members,
            'frozen_members': frozen_members,
            'expired_members': expired_members,
            'expiring_members': expiring_members,
            'revenue_this_month': total_revenue,
            'expenses_this_month': total_expenses,
            'net_profit': net_profit
        }
    finally:
        session.close()

def export_members_to_excel(filepath):
    import pandas as pd
    session = get_session()
    try:
        members = session.query(Member).all()
        data = []
        for m in members:
            data.append({
                'الاسم': m.name,
                'اسم المدرب': m.trainer_name or '',
                'رقم الهاتف': m.phone,
                'نوع الاشتراك': m.plan_name,
                'تاريخ البدء': str(m.start_date),
                'تاريخ الاستحقاق': str(m.end_date),
                'الحالة': 'نشط' if m.status == 'active' else 'مجمد' if m.status == 'frozen' else 'منتهي',
                'تاريخ التجميد': str(m.frozen_date) if m.frozen_date else '',
                'تاريخ العودة بعد التجميد': str(m.last_return_date) if m.last_return_date else '',
                'ملاحظات': m.notes
            })
        df = pd.DataFrame(data)
        df.to_excel(filepath, index=False, engine='openpyxl')
        return True, "تم تصدير البيانات بنجاح."
    except Exception as e:
        return False, str(e)
    finally:
        session.close()

def smart_import_members(filepath):
    import pandas as pd
    from datetime import datetime, date
    session = get_session()
    try:
        df = pd.read_excel(filepath)
        # Smart matching of column names (lowercasing, stripping spaces)
        cols = {str(c).strip(): c for c in df.columns}
        
        # Helper to find column by possible names
        def get_col(possible_names):
            for name in possible_names:
                for c in cols:
                    if name in c:
                        return cols[c]
            return None
            
        name_col = get_col(['الاسم', 'اسم', 'name'])
        trainer_col = get_col(['مدرب', 'اسم المدرب', 'trainer'])
        phone_col = get_col(['هاتف', 'رقم', 'phone', 'موبايل'])
        plan_col = get_col(['نوع', 'اشتراك', 'plan', 'الباقة'])
        start_col = get_col(['بدء', 'تاريخ البدء', 'start'])
        end_col = get_col(['استحقاق', 'انتهاء', 'نهاية', 'end'])
        
        price_col = get_col(['سعر', 'مبلغ', 'السعر', 'المبلغ', 'price', 'amount'])
        
        added_count = 0
        for index, row in df.iterrows():
            name = str(row[name_col]).strip()
            if not name or name == 'nan': continue
            
            trainer_name = str(row[trainer_col]).strip() if trainer_col and not pd.isna(row[trainer_col]) else ""
            phone = str(row[phone_col]).strip() if phone_col and not pd.isna(row[phone_col]) else ""
            
            # Check if member exists
            existing = session.query(Member).filter(Member.name == name).first()
            if existing:
                continue # Skip duplicates
                
            plan_name = str(row[plan_col]).strip() if plan_col and not pd.isna(row[plan_col]) else "عام"
            
            # Parse dates
            start_date = date.today()
            if start_col and not pd.isna(row[start_col]):
                try:
                    if isinstance(row[start_col], pd.Timestamp):
                        start_date = row[start_col].date()
                    else:
                        start_date = datetime.strptime(str(row[start_col]).split(' ')[0], '%Y-%m-%d').date()
                except: pass
                
            end_date = date.today()
            if end_col and not pd.isna(row[end_col]):
                try:
                    if isinstance(row[end_col], pd.Timestamp):
                        end_date = row[end_col].date()
                    else:
                        end_date = datetime.strptime(str(row[end_col]).split(' ')[0], '%Y-%m-%d').date()
                except: pass
            
            # Determine price
            price = 0.0
            if price_col and not pd.isna(row[price_col]):
                try:
                    price = float(str(row[price_col]).replace(',', '').replace('د.ع', '').strip())
                except:
                    price = get_plan_price(plan_name)
            else:
                price = get_plan_price(plan_name)
                
            new_member = Member(
                name=name,
                trainer_name=trainer_name,
                phone=phone,
                plan_name=plan_name,
                price=price,
                start_date=start_date,
                end_date=end_date,
                payment_method="نقدي",
                status="active"
            )
            if (end_date - date.today()).days < 0:
                new_member.status = 'expired'
                
            session.add(new_member)
            session.flush()
            
            # Create payment record for imported member
            last_p = session.query(Payment).order_by(Payment.id.desc()).first()
            next_id = (last_p.id + 1) if last_p else 1
            rec_num = f"REC-{next_id}"
            
            p_record = Payment(
                member_id=new_member.id,
                amount=price,
                payment_method="نقدي",
                payment_date=start_date,
                plan_name=plan_name,
                receipt_number=rec_num
            )
            session.add(p_record)
            added_count += 1
            
        session.commit()
        return True, f"تم استيراد {added_count} مشترك جديد مع تسجيل مبالغهم بنجاح."
    except Exception as e:
        session.rollback()
        return False, f"حدث خطأ أثناء الاستيراد: {str(e)}"
    finally:
        session.close()

def backfill_missing_payments():
    session = get_session()
    try:
        members = session.query(Member).all()
        updated_count = 0
        for m in members:
            payment_count = session.query(Payment).filter(Payment.member_id == m.id).count()
            if payment_count == 0:
                last_p = session.query(Payment).order_by(Payment.id.desc()).first()
                next_id = (last_p.id + 1) if last_p else 1
                rec_num = f"REC-{next_id}"
                
                price = m.price if (m.price and m.price > 0) else get_plan_price(m.plan_name)
                if price <= 0:
                    price = 75000.0 # Default fallback plan price
                    m.price = price
                    
                p_record = Payment(
                    member_id=m.id,
                    amount=price,
                    payment_method=m.payment_method or "نقدي",
                    payment_date=m.start_date or date.today(),
                    plan_name=m.plan_name or "اشتراك",
                    receipt_number=rec_num
                )
                session.add(p_record)
                session.flush()
                updated_count += 1
        session.commit()
        return updated_count
    except Exception as e:
        session.rollback()
        print(f"Error backfilling missing payments: {e}")
        return 0
    finally:
        session.close()

def log_attendance(member_id):
    if USE_FIREBASE:
        fb_log_attendance(member_id)
        return
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
    if USE_FIREBASE:
        return fb_get_today_attendance()
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
    if USE_FIREBASE:
        return fb_add_expense(title, amount, category, notes)
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
    if USE_FIREBASE:
        return fb_get_expenses(month, year)
    session = get_session()
    try:
        query = session.query(Expense)
        if month and year:
            query = query.filter(extract('month', Expense.expense_date) == month, extract('year', Expense.expense_date) == year)
        return query.order_by(Expense.expense_date.desc()).all()
    finally:
        session.close()

def delete_expense(expense_id):
    if USE_FIREBASE:
        return fb_delete_expense(expense_id)
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
    if USE_FIREBASE:
        return fb_add_staff(name, phone, role, salary, salary_type)
    session = get_session()
    try:
        if isinstance(salary, str):
            salary = salary.replace(',', '').replace(' ', '')
        try:
            salary_val = float(salary)
        except ValueError:
            salary_val = 0.0
            
        staff = Staff(name=name, phone=phone, role=role, salary=salary_val, salary_type=salary_type)
        session.add(staff)
        session.commit()
        return True, "تم الحفظ بنجاح"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()

def get_all_staff():
    if USE_FIREBASE:
        return fb_get_all_staff()
    session = get_session()
    try:
        return session.query(Staff).all()
    finally:
        session.close()

def delete_staff(staff_id):
    if USE_FIREBASE:
        return fb_delete_staff(staff_id)
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

def update_staff(staff_id, name, phone, role, salary, salary_type):
    if USE_FIREBASE:
        return fb_update_staff(staff_id, name, phone, role, salary, salary_type)
    session = get_session()
    try:
        staff = session.query(Staff).get(staff_id)
        if not staff:
            return False, "عضو الكادر غير موجود"
        if isinstance(salary, str):
            salary = salary.replace(',', '').replace(' ', '')
        try:
            salary_val = float(salary)
        except ValueError:
            salary_val = 0.0
            
        staff.name = name
        staff.phone = phone
        staff.role = role
        staff.salary = salary_val
        staff.salary_type = salary_type
        session.commit()
        return True, "تم تعديل بيانات الكادر بنجاح"
    except Exception as e:
        session.rollback()
        return False, str(e)
    finally:
        session.close()
