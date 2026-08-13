import os
from datetime import datetime, date
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Detect if running on Vercel (serverless) - use Firebase instead of SQLite
USE_FIREBASE = True

Base = declarative_base()

class Member(Base):
    __tablename__ = 'members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    trainer_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True) # Deprecated
    address = Column(String, nullable=True)
    landmark = Column(String, nullable=True)
    card_id = Column(String, nullable=True, unique=True) # RFID/Barcode
    plan_name = Column(String, nullable=False)
    
    # Financial and duration details
    price = Column(Float, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Status
    status = Column(String, default='active') # active, expired, frozen
    payment_method = Column(String, nullable=False)
    
    # Freeze logic
    is_frozen = Column(Boolean, default=False)
    frozen_date = Column(Date, nullable=True)    
    remaining_days_when_frozen = Column(Integer, nullable=True)
    last_return_date = Column(Date, nullable=True)
    notes = Column(String, nullable=True)
    has_face_registered = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)
    
    payments = relationship("Payment", back_populates="member", cascade="all, delete")

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    amount = Column(Float, nullable=False)
    payment_method = Column(String, nullable=False)
    payment_date = Column(Date, nullable=False, default=date.today)
    plan_name = Column(String, nullable=False)
    receipt_number = Column(String, nullable=True)
    
    member = relationship("Member", back_populates="payments")

class Settings(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True)
    gym_name = Column(String, default="نظام القاعة الرياضية")
    gym_phone = Column(String, default="")
    gym_address = Column(String, default="")
    door_com_port = Column(String, default="")
    license_expiry_date = Column(String, default="")
    is_locally_locked = Column(Boolean, default=False)

class SubscriptionPlan(Base):
    __tablename__ = 'subscription_plans'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    price = Column(Float, nullable=False)
    duration_days = Column(Integer, nullable=False)

class AttendanceLog(Base):
    __tablename__ = 'attendance_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('members.id'))
    entry_time = Column(DateTime, default=datetime.now)
    
class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    expense_date = Column(Date, default=date.today)
    category = Column(String, default='عام')
    notes = Column(String, nullable=True)

class Staff(Base):
    __tablename__ = 'staff'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    role = Column(String, default='مدرب') # مدرب، موظف استقبال، عامل نظافة
    salary = Column(Float, default=0.0)
    salary_type = Column(String, default='ثابت') # ثابت، نسبة


import os
import tempfile

base_dir = os.path.dirname(os.path.abspath(__file__))
if os.access(base_dir, os.W_OK):
    db_path = os.path.join(base_dir, 'gym.db')
else:
    db_path = os.path.join(tempfile.gettempdir(), 'gym.db')

engine = create_engine(f'sqlite:///{db_path}', echo=False)

def init_db():
    Base.metadata.create_all(engine)
    
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE members ADD COLUMN trainer_name VARCHAR"))
            conn.commit()
        except Exception:
            pass
            
    # Add default plans if none exist
    Session = sessionmaker(bind=engine)
    session = Session()
    if session.query(SubscriptionPlan).count() == 0:
        default_plans = [
            SubscriptionPlan(name='VIP شهري', price=75000, duration_days=30),
            SubscriptionPlan(name='خاص شهري', price=50000, duration_days=30),
            SubscriptionPlan(name='شهري', price=35000, duration_days=30),
            SubscriptionPlan(name='أسبوعي', price=12000, duration_days=7),
            SubscriptionPlan(name='يومي', price=3000, duration_days=1),
            SubscriptionPlan(name='3 أشهر', price=90000, duration_days=90),
        ]
        session.add_all(default_plans)
        session.commit()
    session.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    return SessionLocal()

# Initialize DB when module is imported so Vercel creates the tables
init_db()
