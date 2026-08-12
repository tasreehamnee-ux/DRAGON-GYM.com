import sys
from datetime import datetime, date, timedelta
import cv2
from remote_control import remote_control
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox, 
    QDateEdit, QMessageBox, QStackedWidget, QFrame, QScrollArea, QGridLayout, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

from database import init_db, get_session, Member, SubscriptionPlan, Payment, Staff
from business_logic import (
    add_new_member, get_dashboard_stats, update_member_statuses, 
    freeze_membership, unfreeze_membership, get_plan_config, 
    get_plan_price, calculate_end_date, get_settings, update_settings,
    add_plan, delete_plan, get_all_plans, activate_pending_member
)
from face_gui import FaceRegistrationDialog, FaceMonitorWindow

# EXACT THEME from the requested image (Light Gray Sidebar, Blue Active, White Main Area)
THEME = """
QMainWindow {
    background-color: #ffffff; /* White background for the main window */
}
QWidget {
    font-family: 'Segoe UI', 'Cairo', Arial, sans-serif;
    font-size: 14px;
    font-weight: bold;
    color: #000000;
}
QLabel {
    color: #000000;
}
QLineEdit, QComboBox, QDateEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 8px;
    color: #000000;
    font-weight: bold;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #3b82f6; 
}
QPushButton {
    font-weight: bold;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#PrimaryButton {
    background-color: #3b82f6; /* Blue matching the image */
    color: white;
    border: none;
}
QPushButton#PrimaryButton:hover {
    background-color: #2563eb;
}
QPushButton#DangerButton {
    background-color: #ef4444; /* Red logout / delete */
    color: white;
    border: none;
}
QPushButton#DangerButton:hover {
    background-color: #dc2626;
}
QPushButton#WarningButton {
    background-color: #f59e0b;
    color: white;
    border: none;
}
QPushButton#WarningButton:hover {
    background-color: #d97706;
}
QPushButton#GreenButton {
    background-color: #10b981;
    color: white;
    border: none;
}
QTableWidget {
    background-color: #ffffff;
    border: none;
    gridline-color: #cbd5e1;
    color: #000000;
    font-weight: bold;
    font-size: 14px;
    selection-background-color: #f1f5f9;
}
QTableWidget::item {
    padding: 6px 10px;
    text-align: center;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #000000;
    padding: 12px;
    font-weight: bold;
    font-size: 14px;
    border: none;
    border-bottom: 1px solid #cbd5e1;
    border-right: 1px solid #cbd5e1;
}
QDialog {
    background-color: #ffffff;
}
QGroupBox {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    margin-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
    color: #64748b;
}
"""

class FreezeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تجميد الاشتراك")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(THEME)
        layout = QVBoxLayout(self)
        lbl = QLabel("الرجاء إدخال تاريخ بداية التجميد:")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(lbl)
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        layout.addWidget(self.date_input)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("تأكيد التجميد")
        self.save_btn.setObjectName("WarningButton")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
    def get_date(self):
        qdate = self.date_input.date()
        return date(qdate.year(), qdate.month(), qdate.day())

class UnfreezeDialog(QDialog):
    def __init__(self, remaining_days, parent=None):
        super().__init__(parent)
        self.remaining_days = remaining_days
        self.setWindowTitle("إلغاء تجميد الاشتراك")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(THEME)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("تاريخ العودة للاشتراك:"))
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.dateChanged.connect(self.update_info)
        layout.addWidget(self.date_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("الأيام المتبقية:"))
        self.days_field = QLineEdit()
        self.days_field.setReadOnly(True)
        self.days_field.setText(f"{self.remaining_days} يوم")
        self.days_field.setStyleSheet("background-color: #f1f5f9; color: #475569; font-weight: bold;")
        layout.addWidget(self.days_field)
        
        layout.addWidget(QLabel("تاريخ انتهاء الاشتراك بعد التجميد:"))
        self.end_date_field = QLineEdit()
        self.end_date_field.setReadOnly(True)
        self.end_date_field.setStyleSheet("background-color: #eff6ff; color: #2563eb; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.end_date_field)
        
        self.update_info()
        layout.addSpacing(15)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("تأكيد العودة")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
    def update_info(self):
        d = self.get_date()
        from datetime import timedelta
        final_date = d + timedelta(days=self.remaining_days)
        self.end_date_field.setText(str(final_date))
        
    def get_date(self):
        qdate = self.date_input.date()
        return date(qdate.year(), qdate.month(), qdate.day())

class AddMemberDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة مشترك جديد")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(450)
        self.setStyleSheet(THEME)
        layout = QFormLayout(self)
        layout.setSpacing(15)
        self.name_combo = QComboBox()
        self.name_combo.setEditable(True)
        self.name_combo.setPlaceholderText("اكتب اسم المشترك أو اختر اسماً موجوداً...")
        
        self.trainer_combo = QComboBox()
        self.trainer_combo.setEditable(True)
        self.trainer_combo.setPlaceholderText("اكتب اسم المدرب أو اختر من القائمة...")

        session = get_session()
        try:
            members = session.query(Member).order_by(Member.name.asc()).all()
            self.existing_members = {m.name: m for m in members if m.name}
            self.name_combo.addItems([""] + [m.name for m in members if m.name])

            # Populate trainer options from Staff and existing Members
            trainers = set()
            staff_list = session.query(Staff).all()
            for s in staff_list:
                if s.name and s.name.strip():
                    trainers.add(s.name.strip())
            for m in members:
                if getattr(m, 'trainer_name', None) and m.trainer_name.strip():
                    trainers.add(m.trainer_name.strip())

            trainer_items = sorted(list(trainers))
            self.trainer_combo.clear()
            self.trainer_combo.addItem("بدون مدرب")
            for t_item in trainer_items:
                if t_item != "بدون مدرب":
                    self.trainer_combo.addItem(t_item)
        finally:
            session.close()
            
        self.name_combo.currentTextChanged.connect(self.on_name_selected)

        self.phone_input = QLineEdit()
        self.card_id_input = QLineEdit()
        self.card_id_input.setPlaceholderText("مرر الكارت هنا أو اتركه فارغاً")
        self.address_input = QLineEdit()
        self.landmark_input = QLineEdit()
        self.plan_combo = QComboBox()
        self.plan_config = get_plan_config()
        if not self.plan_config:
            QMessageBox.warning(self, "تنبيه", "لا توجد اشتراكات مسجلة. الرجاء إضافة اشتراكات من الإعدادات أولاً.")
            self.reject()
            return
        self.plan_combo.addItems(list(self.plan_config.keys()))
        self.plan_combo.currentTextChanged.connect(self.update_price_and_date)
        self.start_date_input = QDateEdit(QDate.currentDate())
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.dateChanged.connect(self.update_price_and_date)
        
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("ملاحظات أو مهام خاصة بالمشترك...")
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["نقدي", "بطاقة", "تحويل", "آجل (دين)"])
        self.receipt_number_input = QLineEdit()
        self.receipt_number_input.setPlaceholderText("رقم الوصل (اختياري - يولد تلقائياً إن تُرك فارغاً)")
        self.price_label = QLabel("0 د.ع")
        self.price_label.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 18px;")
        self.end_date_label = QLabel()
        self.end_date_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #10b981;")
        layout.addRow("الاسم الكامل:", self.name_combo)
        layout.addRow("اسم المدرب:", self.trainer_combo)
        layout.addRow("رقم الهاتف:", self.phone_input)
        layout.addRow("رقم الكارت (RFID):", self.card_id_input)
        layout.addRow("العنوان:", self.address_input)
        layout.addRow("أقرب نقطة دالة:", self.landmark_input)
        layout.addRow("نوع الاشتراك:", self.plan_combo)
        layout.addRow("طريقة الدفع:", self.payment_method_combo)
        layout.addRow("رقم الوصل:", self.receipt_number_input)
        layout.addRow("ملاحظات:", self.notes_input)
        self.postpone_checkbox = QCheckBox("تأجيل بدء الاشتراك (دفع ولم يباشر بعد)")
        self.postpone_checkbox.setStyleSheet("color: #ea580c; font-weight: bold;")
        layout.addRow("", self.postpone_checkbox)
        layout.addRow("تاريخ البدء:", self.start_date_input)
        layout.addRow("تاريخ الانتهاء:", self.end_date_label)
        layout.addRow("المبلغ المطلوب:", self.price_label)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ البيانات ثم تسجيل الوجه")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)
        self.update_price_and_date()

    def on_name_selected(self, text):
        name = text.strip()
        if hasattr(self, 'existing_members') and name in self.existing_members:
            m = self.existing_members[name]
            self.phone_input.setText(m.phone or "")
            self.card_id_input.setText(m.card_id or "")
            self.address_input.setText(m.address or "")
            self.landmark_input.setText(m.landmark or "")
            if getattr(m, 'trainer_name', None) and m.trainer_name:
                self.trainer_combo.setCurrentText(m.trainer_name)
            else:
                self.trainer_combo.setCurrentText("بدون مدرب")
        else:
            self.phone_input.clear()
            self.card_id_input.clear()
            self.address_input.clear()
            self.landmark_input.clear()
            self.notes_input.clear()
            self.trainer_combo.setCurrentText("بدون مدرب")

    def update_price_and_date(self):
        plan_name = self.plan_combo.currentText()
        if not plan_name: return
        price = get_plan_price(plan_name)
        self.price_label.setText(f"{price:,.0f} د.ع")
        qdate = self.start_date_input.date()
        start_date = date(qdate.year(), qdate.month(), qdate.day())
        end_date = calculate_end_date(start_date, plan_name)
        self.end_date_label.setText(end_date.strftime("%Y-%m-%d"))

    def get_data(self):
        qdate = self.start_date_input.date()
        start_date = date(qdate.year(), qdate.month(), qdate.day())
        card_id = self.card_id_input.text().strip()
        if not card_id:
            card_id = None
        trainer = self.trainer_combo.currentText().strip()
        if trainer == "بدون مدرب":
            trainer = ""
        return {
            'name': self.name_combo.currentText().strip(),
            'trainer_name': trainer,
            'phone': self.phone_input.text().strip(),
            'card_id': card_id,
            'address': self.address_input.text(),
            'landmark': self.landmark_input.text(),
            'plan_name': self.plan_combo.currentText(),
            'start_date': self.start_date_input.date().toPyDate(),
            'payment_method': self.payment_method_combo.currentText(),
            'notes': self.notes_input.text(),
            'receipt_number': self.receipt_number_input.text(),
            'is_pending': self.postpone_checkbox.isChecked()
        }

class AddPaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة دفعة يدوية / مبيعات")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(380)
        layout = QFormLayout(self)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("مثال: زينب / ملتي فيتامين، مكملات، الخ")
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("المبلغ بالدينار")
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["نقدي", "بطاقة", "تحويل", "آجل (دين)"])
        self.receipt_number_input = QLineEdit()
        self.receipt_number_input.setPlaceholderText("رقم الوصل (اختياري)")
        
        layout.addRow("المشترك / الوصف:", self.desc_input)
        layout.addRow("المبلغ (د.ع):", self.amount_input)
        layout.addRow("طريقة الدفع:", self.payment_method_combo)
        layout.addRow("رقم الوصل:", self.receipt_number_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ الدفعة")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'desc': self.desc_input.text().strip() or "دفعة يدوية",
            'amount': self.amount_input.text().strip(),
            'payment_method': self.payment_method_combo.currentText(),
            'receipt_number': self.receipt_number_input.text().strip()
        }

class AddPlanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة اشتراك جديد")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(THEME)
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.price_input = QLineEdit()
        self.duration_input = QLineEdit()
        layout.addRow("اسم الاشتراك (مثال: عرض صيفي):", self.name_input)
        layout.addRow("السعر (د.ع):", self.price_input)
        layout.addRow("المدة بالأيام (مثال 30 لشهر):", self.duration_input)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("إضافة")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.setStyleSheet("background-color: #f1f5f9; border: 1px solid #cbd5e1;")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)
    def get_data(self):
        return {
            'name': self.name_input.text(),
            'price': self.price_input.text(),
            'duration': self.duration_input.text()
        }

class MemberCardDialog(QDialog):
    def __init__(self, member, parent=None):
        super().__init__(parent)
        self.member = member
        self.setWindowTitle("بطاقة المشترك")
        self.setMinimumSize(450, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #f8fafc;
            }
            QLabel {
                color: #1e293b;
                font-size: 14px;
            }
        """)
        layout = QVBoxLayout(self)
        
        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #3b82f6;
                border-radius: 12px;
            }
        """)
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)
        
        from business_logic import get_settings
        settings = get_settings()
        gym_name = settings.gym_name if settings.gym_name else "الجيم"
        
        title = QLabel(f"بطاقة عضوية - {gym_name}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; border: none;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(title)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("border: 1px solid #e2e8f0;")
        card_layout.addWidget(line)
        
        content_layout = QHBoxLayout()
        info_layout = QFormLayout()
        info_layout.setSpacing(15)
        
        def add_info(label_text, value_text):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; color: #64748b; border: none;")
            val = QLabel(str(value_text))
            val.setStyleSheet("font-weight: bold; color: #000000; border: none;")
            info_layout.addRow(lbl, val)

        session = get_session()
        receipt_num = None
        try:
            pay = session.query(Payment).filter(Payment.member_id == member.id).order_by(Payment.id.desc()).first()
            if pay and pay.receipt_number:
                receipt_num = pay.receipt_number
        finally:
            session.close()

        if not receipt_num:
            receipt_num = f"REC-{member.id}"

        add_info("الاسم:", member.name)
        if getattr(member, 'trainer_name', None):
            add_info("اسم المدرب:", member.trainer_name)
        add_info("رقم الوصل:", receipt_num)
        add_info("رقم المشترك:", str(member.id))
        add_info("نوع الاشتراك:", member.plan_name)
        add_info("تاريخ البدء:", member.start_date)
        add_info("الانتهاء:", member.end_date)
        
        status_text = "نشط" if member.status == 'active' else "مجمد" if member.status == 'frozen' else "منتهي"
        add_info("الحالة:", status_text)
        
        content_layout.addLayout(info_layout)
        
        import os
        from PyQt6.QtGui import QPixmap
        photo_label = QLabel()
        photo_label.setFixedSize(120, 120)
        photo_label.setStyleSheet("border: 2px solid #cbd5e1; border-radius: 60px; background-color: #f1f5f9;")
        photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        photo_path = f"profiles/{member.id}.jpg"
        if os.path.exists(photo_path):
            pixmap = QPixmap(photo_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            photo_label.setPixmap(pixmap)
        else:
            photo_label.setText("لا توجد\nصورة")
        
        content_layout.addWidget(photo_label)
        
        card_layout.addLayout(content_layout)
        layout.addWidget(self.card_frame)
        
        btn_layout = QHBoxLayout()
        print_btn = QPushButton("طباعة البطاقة")
        print_btn.setStyleSheet("background-color: #10b981; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        print_btn.clicked.connect(self.print_card)
        btn_layout.addWidget(print_btn)
        
        wa_btn = QPushButton("مراسلة واتساب")
        wa_btn.setStyleSheet("background-color: #25D366; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        wa_btn.clicked.connect(self.send_whatsapp)
        btn_layout.addWidget(wa_btn)
        
        close_btn = QPushButton("إغلاق")
        close_btn.setObjectName("PrimaryButton")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)

    def send_whatsapp(self):
        try:
            import urllib.parse
            from PyQt6.QtGui import QDesktopServices
            from PyQt6.QtCore import QUrl
            from PyQt6.QtWidgets import QMessageBox
            
            if not self.member.phone:
                QMessageBox.warning(self, "تنبيه", "لا يوجد رقم هاتف مسجل لهذا المشترك")
                return
                
            phone = str(self.member.phone).strip()
            if phone.startswith('0'):
                phone = '964' + phone[1:]
                
            msg = f"مرحباً {self.member.name}،\nاشتراكك {self.member.plan_name} فعال لغاية {self.member.end_date}.\nشكراً لك!"
            encoded_msg = urllib.parse.quote(msg)
            # Using https://wa.me/ is safer than whatsapp:// as it handles fallbacks to web
            url = QUrl(f"https://wa.me/{phone}?text={encoded_msg}")
            
            if not QDesktopServices.openUrl(url):
                QMessageBox.warning(self, "خطأ", "لم يتمكن النظام من فتح الرابط. تأكد من وجود متصفح افتراضي.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء فتح واتساب: {str(e)}")

    def print_card(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from PyQt6.QtGui import QPainter
        import os
        
        path, _ = QFileDialog.getSaveFileName(self, "حفظ كصورة", f"بطاقة_{self.windowTitle()}.png", "Images (*.png *.jpg)")
        if path:
            try:
                pixmap = self.card_frame.grab()
                pixmap.save(path)
                QMessageBox.information(self, "نجاح", "تم حفظ بطاقة المشترك للطباعة بنجاح!")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء الحفظ:\n{e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.setWindowTitle(f"نظام الاشتراكات - {self.settings.gym_name}")
        self.setMinimumSize(1200, 800)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(THEME)
        update_member_statuses()
        
        self.root_stack = QStackedWidget()
        self.setCentralWidget(self.root_stack)

        main_widget = QWidget()
        self.root_stack.addWidget(main_widget)
        
        self.lock_widget = QWidget()
        self.lock_widget.setStyleSheet("background-color: #111827;")
        lock_layout = QVBoxLayout(self.lock_widget)
        self.lock_label = QLabel("البرنامج في حالة صيانة يرجى الاتصال بالمبرمج")
        self.lock_label.setStyleSheet("color: #ef4444; font-size: 48px; font-weight: bold;")
        self.lock_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_layout.addWidget(self.lock_label)
        self.root_stack.addWidget(self.lock_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- Sidebar --- (Light Gray matching the image #eef2f5)
        sidebar = QFrame()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("background-color: #eef2f5; border-left: 1px solid #cbd5e1;") 
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(15, 30, 15, 30)
        sidebar_layout.setSpacing(5)
        
        self.lbl_title = QLabel(self.settings.gym_name)
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e40af; border: none;")
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.lbl_title)
        
        sidebar_layout.addSpacing(30)
        
        # Buttons matching the layout but with GYM text
        self.nav_dashboard = QPushButton("لوحة التحكم والمؤشرات")
        self.nav_members = QPushButton("قائمة المشتركين")
        self.nav_new = QPushButton("إضافة مشترك جديد")
        self.nav_card = QPushButton("بطاقة المشترك")
        self.nav_all = QPushButton("سجل الاشتراكات عامة")
        self.nav_stats = QPushButton("الإحصائيات الشاملة")
        self.nav_settings = QPushButton("إعدادات النظام")
        self.nav_face = QPushButton("بوابة الدخول (الوجه)")
        
        self.nav_buttons = [
            self.nav_dashboard, self.nav_members, self.nav_new, 
            self.nav_card, self.nav_all, self.nav_stats, self.nav_settings, self.nav_face
        ]
        
        for btn in self.nav_buttons:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sidebar_layout.addWidget(btn)
            sidebar_layout.addSpacing(5)
            
        sidebar_layout.addStretch()
        
        # Red Logout button at the bottom
        logout_btn = QPushButton("الخروج من النظام")
        logout_btn.setObjectName("DangerButton")
        logout_btn.setStyleSheet("QPushButton#DangerButton { padding: 12px; font-size: 16px; font-weight: bold; border-radius: 6px; margin-bottom: 20px;}")
        logout_btn.clicked.connect(self.close)
        sidebar_layout.addWidget(logout_btn)
        
        # Staff count (matching the green text at the bottom)
        staff_count = QLabel(f"عدد المشتركين الفعلي: {get_session().query(Member).count()}")
        staff_count.setStyleSheet("color: #10b981; font-weight: bold; font-size: 12px; border: none;")
        staff_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(staff_count)
        
        dev_info = QLabel("نظام إدارة القاعات الرياضية\nبرمجة: م.م رنا علي ذويب")
        dev_info.setStyleSheet("color: #94a3b8; font-size: 11px; border: none; font-weight: bold;")
        dev_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(dev_info)
        
        main_layout.addWidget(sidebar)
        
        # --- Content Area ---
        content_area = QWidget()
        content_area.setStyleSheet("background-color: #ffffff;")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.setSpacing(0)
        
        # Top Tabs Container (matching exactly)
        top_tabs_container = QFrame()
        top_tabs_container.setStyleSheet("background-color: #f1f5f9; border-bottom: 1px solid #cbd5e1;")
        top_tabs_container.setFixedHeight(50)
        t_layout = QHBoxLayout(top_tabs_container)
        t_layout.setContentsMargins(20, 0, 20, 0)
        t_layout.setSpacing(5)
        
        # Top tabs matching Gym context
        self.top_tabs = [
            QPushButton("لوحة التحكم"),
            QPushButton("المشتركين"),
            QPushButton("المدفوعات"),
            QPushButton("التقارير"),
            QPushButton("المصروفات"),
            QPushButton("الكادر"),
            QPushButton("الإعدادات")
        ]
        
        for tb in self.top_tabs:
            tb.setCursor(Qt.CursorShape.PointingHandCursor)
            t_layout.addWidget(tb)
            
        t_layout.addStretch() # Add stretch at the end (left side in RTL)
        
        content_layout.addWidget(top_tabs_container)
        
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        main_layout.addWidget(content_area)
        
        # Pages - Mapping to correct indices
        self.dashboard_page = QWidget()
        self.setup_dashboard()
        self.stack.addWidget(self.dashboard_page) # Index 0
        
        self.members_page = QWidget()
        self.setup_members()
        self.stack.addWidget(self.members_page) # Index 1
        
        self.payments_page = QWidget()
        self.setup_payments()
        self.stack.addWidget(self.payments_page) # Index 2
        
        self.reports_page = QWidget()
        self.setup_reports()
        self.stack.addWidget(self.reports_page) # Index 3
        
        self.expenses_page = QWidget()
        self.setup_expenses()
        self.stack.addWidget(self.expenses_page) # Index 4
        
        self.staff_page = QWidget()
        self.setup_staff()
        self.stack.addWidget(self.staff_page) # Index 5
        
        self.settings_page = QWidget()
        self.setup_settings()
        self.stack.addWidget(self.settings_page) # Index 6
        
        self.card_page = QWidget()
        self.setup_card_page()
        self.stack.addWidget(self.card_page) # Index 7
        
        self.face_page = FaceMonitorWindow(self)
        self.stack.addWidget(self.face_page) # Index 8

        # Connections using correct indices
        self.nav_dashboard.clicked.connect(lambda: self.switch_page(0))
        self.nav_members.clicked.connect(lambda: self.switch_page(1))
        self.nav_new.clicked.connect(self.show_add_member_dialog)
        self.nav_card.clicked.connect(lambda: self.switch_page(7))
        self.nav_all.clicked.connect(lambda: self.switch_page(2)) # سجل الاشتراكات -> المدفوعات
        self.nav_stats.clicked.connect(lambda: self.switch_page(3)) # الإحصائيات -> التقارير
        self.nav_settings.clicked.connect(lambda: self.switch_page(6))
        self.nav_face.clicked.connect(lambda: self.switch_page(8))
        
        for i, tb in enumerate(self.top_tabs):
            tb.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
            
        self.switch_page(0)

        self.lock_dialog = None
        self.setup_remote_control()
        self.handle_lock_state() # Initial local lock check

    def setup_remote_control(self):
        remote_control.lock_state_changed.connect(self.handle_lock_state)
        remote_control.close_app_requested.connect(self.handle_close_app)
        remote_control.start_listening()

    def handle_close_app(self):
        print("Closing application per remote cloud signal...")
        QApplication.quit()

    def handle_lock_state(self, is_locked=False):
        from datetime import datetime, date
        from business_logic import get_settings
        
        # Fallback for when signal provides no argument or we just want to recheck
        if isinstance(is_locked, bool):
            remote_lock = is_locked
        else:
            remote_lock = False
            
        settings = get_settings()
        local_lock = settings.is_locally_locked
        expired = False
        
        if settings.license_expiry_date:
            try:
                expiry = datetime.strptime(settings.license_expiry_date, "%Y-%m-%d").date()
                if date.today() > expiry:
                    expired = True
            except Exception:
                pass
                
        if remote_lock or local_lock or expired:
            self.root_stack.setCurrentWidget(self.lock_widget)
        else:
            self.root_stack.setCurrentIndex(0)
    def setup_placeholder(self, widget, text):
        layout = QVBoxLayout(widget)
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 24px; color: #94a3b8;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

    def setup_card_page(self):
        layout = QVBoxLayout(self.card_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("بطاقة المشترك")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        layout.addWidget(title)
        
        search_layout = QHBoxLayout()
        self.card_search_input = QLineEdit()
        self.card_search_input.setPlaceholderText("ابحث بالاسم أو رقم الهاتف لعرض البطاقة واضغط Enter...")
        self.card_search_input.setMinimumWidth(300)
        self.card_search_input.returnPressed.connect(self.search_and_show_card)
        
        self.card_search_btn = QPushButton("بحث")
        self.card_search_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 16px; border-radius: 4px; font-weight: bold;")
        self.card_search_btn.clicked.connect(self.search_and_show_card)
        
        search_layout.addWidget(self.card_search_input)
        search_layout.addWidget(self.card_search_btn)
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        layout.addSpacing(20)
        self.card_display_frame = QFrame()
        self.card_display_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #3b82f6;
                border-radius: 12px;
            }
            QLabel { border: none; }
        """)
        self.card_display_frame.setMinimumSize(400, 300)
        self.card_display_frame.setMaximumWidth(500)
        self.card_display_layout = QFormLayout(self.card_display_frame)
        self.card_display_layout.setContentsMargins(20, 20, 20, 20)
        self.card_display_layout.setSpacing(15)
        
        card_title = QLabel(f"بطاقة عضوية - {self.settings.gym_name}")
        card_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2563eb;")
        card_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_display_layout.addRow(card_title)
        
        # Add a placeholder label initially
        self.card_placeholder = QLabel("يرجى البحث عن مشترك لعرض بطاقته هنا")
        self.card_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_display_layout.addRow(self.card_placeholder)
        
        layout.addWidget(self.card_display_frame, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()

    def search_and_show_card(self):
        query = self.card_search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم أو رقم هاتف للبحث")
            return
            
        session = get_session()
        try:
            from sqlalchemy import or_
            member = session.query(Member).filter(or_(Member.name.like(f"%{query}%"), Member.phone.like(f"%{query}%"))).first()
            if not member:
                QMessageBox.warning(self, "تنبيه", "لم يتم العثور على مشترك مطابق!")
                return
                
            # Clear current layout (except title)
            while self.card_display_layout.rowCount() > 1:
                self.card_display_layout.removeRow(1)
                
            # We will use a horizontal layout: Info on one side, Photo on the other
            content_layout = QHBoxLayout()
            info_layout = QFormLayout()
            
            def add_info(label_text, value_text):
                lbl = QLabel(label_text)
                lbl.setStyleSheet("color: #64748b; font-size: 14px;")
                val = QLabel(str(value_text))
                val.setStyleSheet("font-weight: bold; color: #000000; font-size: 14px;")
                val.setWordWrap(True)
                info_layout.addRow(lbl, val)
                
            pay = session.query(Payment).filter(Payment.member_id == member.id).order_by(Payment.id.desc()).first()
            receipt_num = pay.receipt_number if (pay and pay.receipt_number) else f"REC-{member.id}"
            
            add_info("الاسم:", member.name)
            if getattr(member, 'trainer_name', None):
                add_info("اسم المدرب:", member.trainer_name)
            add_info("رقم الوصل:", receipt_num)
            add_info("رقم المشترك:", str(member.id))
            add_info("نوع الاشتراك:", member.plan_name)
            add_info("تاريخ البدء:", member.start_date)
            add_info("تاريخ الانتهاء:", member.end_date)
            
            if member.status == 'frozen' and member.frozen_date:
                add_info("تاريخ التجميد:", member.frozen_date)
                add_info("الأيام المتبقية:", member.remaining_days_when_frozen)
                
            status_text = "نشط" if member.status == 'active' else "مجمد" if member.status == 'frozen' else "منتهي"
            status_color = "#10b981" if member.status == 'active' else "#f59e0b" if member.status == 'frozen' else "#ef4444"
            
            status_val = QLabel(status_text)
            status_val.setStyleSheet(f"font-weight: bold; color: {status_color}; font-size: 14px;")
            lbl = QLabel("الحالة:")
            lbl.setStyleSheet("color: #64748b; font-size: 14px;")
            info_layout.addRow(lbl, status_val)
            
            content_layout.addLayout(info_layout)
            
            import os
            from PyQt6.QtGui import QPixmap
            photo_label = QLabel()
            photo_label.setFixedSize(120, 120)
            photo_label.setStyleSheet("border: 2px solid #cbd5e1; border-radius: 60px; background-color: #f1f5f9;")
            photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            photo_path = f"profiles/{member.id}.jpg"
            if os.path.exists(photo_path):
                pixmap = QPixmap(photo_path).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                photo_label.setPixmap(pixmap)
            else:
                photo_label.setText("لا توجد\nصورة")
                
            content_layout.addWidget(photo_label)
            self.card_display_layout.addRow(content_layout)
            
            print_btn = QPushButton("طباعة البطاقة")
            print_btn.setStyleSheet("background-color: #10b981; color: white; padding: 10px; font-weight: bold; border-radius: 6px; margin-top: 15px;")
            print_btn.clicked.connect(self.print_card_from_page)
            self.card_display_layout.addRow(print_btn)
            
        finally:
            session.close()

    def print_card_from_page(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        
        path, _ = QFileDialog.getSaveFileName(self, "حفظ كصورة", "بطاقة_المشترك.png", "Images (*.png *.jpg)")
        if path:
            try:
                pixmap = self.card_display_frame.grab()
                pixmap.save(path)
                QMessageBox.information(self, "نجاح", "تم حفظ بطاقة المشترك للطباعة بنجاح!")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء الحفظ:\n{e}")

    def setup_dashboard(self):
        layout = QVBoxLayout(self.dashboard_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("لوحة المعلومات والمؤشرات الدورية للمشتركين")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #334155;")
        layout.addWidget(title)
        
        # Stats Cards EXACTLY matching the colors of the user's image (Red, Yellow, Blue outlines)
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        
        self.lbl_frozen_members = self.create_stat_card("المشتركين المجمدين حالياً", "0", "#ef4444") # Red
        self.lbl_expiring = self.create_stat_card("المشتركين المنتهين قريباً", "0", "#f59e0b") # Yellow
        self.lbl_total_members = self.create_stat_card("إجمالي المشتركين", "0", "#3b82f6") # Blue
        
        stats_layout.addWidget(self.lbl_frozen_members['widget'])
        stats_layout.addWidget(self.lbl_expiring['widget'])
        stats_layout.addWidget(self.lbl_total_members['widget'])
        
        # Financial Stats Row
        fin_stats_layout = QHBoxLayout()
        fin_stats_layout.setSpacing(15)
        
        self.lbl_expenses = self.create_stat_card("إجمالي المصروفات (الشهر)", "0", "#ef4444") # Red
        self.lbl_revenue = self.create_stat_card("الوارد الكلي (الشهر)", "0", "#3b82f6") # Blue
        self.lbl_net_profit = self.create_stat_card("صافي الأرباح (الشهر)", "0", "#10b981") # Green
        
        fin_stats_layout.addWidget(self.lbl_expenses['widget'])
        fin_stats_layout.addWidget(self.lbl_revenue['widget'])
        fin_stats_layout.addWidget(self.lbl_net_profit['widget'])
        
        layout.addLayout(stats_layout)
        layout.addSpacing(10)
        layout.addLayout(fin_stats_layout)
        layout.addSpacing(20)
        
        # Table inside a QGroupBox (matching the image bounding box)
        group_box = QGroupBox("التنبيه الفوري للمشتركين المستحقين خلال الفترة المحددة")
        group_box.setStyleSheet("QGroupBox { border: 1px solid #cbd5e1; border-radius: 6px; margin-top: 15px; } QGroupBox::title { color: #64748b; subcontrol-origin: margin; left: 20px; padding: 0 5px 0 5px; }")
        g_layout = QVBoxLayout(group_box)
        g_layout.setContentsMargins(10, 20, 10, 10)
        
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(5)
        self.alert_table.setHorizontalHeaderLabels([
            "تسلسل", "اسم المشترك الرباعي", "نوع الاشتراك", "تاريخ الاستحقاق", "الأيام المتبقية"
        ])
        self.alert_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alert_table.verticalHeader().setVisible(False)
        self.alert_table.setStyleSheet("border: none;")
        self.alert_table.setAlternatingRowColors(True)
        g_layout.addWidget(self.alert_table)
        
        layout.addWidget(group_box)
        self.refresh_dashboard()

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"background-color: white; border-radius: 8px; border: 2px solid {color};")
        card.setMinimumHeight(80)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; border: 1px solid {color}; border-radius: 10px; padding: 2px 10px; background-color: white;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold; border: none;")
        lbl_value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0,0,0,0)
        top_layout.addStretch()
        top_layout.addWidget(title_lbl)
        
        layout.addLayout(top_layout)
        layout.addWidget(lbl_value)
        
        return {'widget': card, 'label': lbl_value}

    def refresh_dashboard(self):
        stats = get_dashboard_stats()
        self.lbl_total_members['label'].setText(str(stats['total_members']))
        self.lbl_frozen_members['label'].setText(str(stats['frozen_members']))
        
        # Format numbers with commas
        self.lbl_revenue['label'].setText(f"{stats.get('revenue_this_month', 0):,.0f} د.ع")
        self.lbl_expenses['label'].setText(f"{stats.get('expenses_this_month', 0):,.0f} د.ع")
        self.lbl_net_profit['label'].setText(f"{stats.get('net_profit', 0):,.0f} د.ع")
        
        session = get_session()
        try:
            today = date.today()
            threshold = today + timedelta(days=2)
            from sqlalchemy import or_, and_
            expiring_members = session.query(Member).filter(
                or_(
                    and_(Member.status == 'active', Member.end_date <= threshold),
                    Member.status == 'expired'
                )
            ).all()
            
            self.lbl_expiring['label'].setText(str(len(expiring_members)))
            
            self.alert_table.setRowCount(len(expiring_members))
            for row, m in enumerate(expiring_members):
                self.alert_table.setItem(row, 0, QTableWidgetItem(str(row+1)))
                
                name_item = QTableWidgetItem(m.name)
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alert_table.setItem(row, 1, name_item)
                
                type_item = QTableWidgetItem(m.plan_name)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alert_table.setItem(row, 2, type_item)
                
                end_item = QTableWidgetItem(str(m.end_date))
                end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alert_table.setItem(row, 3, end_item)
                
                days_left = (m.end_date - today).days
                if days_left < 0:
                    status_text = "منتهي"
                elif days_left == 0:
                    status_text = "ينتهي اليوم"
                else:
                    status_text = f"ينتهي بعد {days_left} يوم"
                
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                if days_left < 0:
                    status_item.setForeground(QColor("#ef4444")) # Red for expired
                else:
                    status_item.setForeground(QColor("#f59e0b")) # Yellow for expiring soon
                
                font = QFont()
                font.setBold(True)
                status_item.setFont(font)
                self.alert_table.setItem(row, 4, status_item)
                
        finally:
            session.close()

    def setup_members(self):
        layout = QVBoxLayout(self.members_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header_layout = QHBoxLayout()
        title = QLabel("قائمة المشتركين الحاليين")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000;")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.import_btn = QPushButton("استيراد ذكي من Excel")
        self.import_btn.setStyleSheet("background-color: #10b981; color: white; padding: 6px 15px; font-size: 13px; font-weight: bold; border-radius: 4px;")
        self.import_btn.clicked.connect(self.import_from_excel)
        header_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("تصدير إلى Excel")
        self.export_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 6px 15px; font-size: 13px; font-weight: bold; border-radius: 4px;")
        self.export_btn.clicked.connect(self.export_to_excel)
        header_layout.addWidget(self.export_btn)
        layout.addLayout(header_layout)
        layout.addSpacing(10)

        self.member_search_input = QLineEdit()
        self.member_search_input.setPlaceholderText("بحث عن مشترك بالاسم، رقم الهاتف...")
        self.member_search_input.textChanged.connect(self.refresh_members_table)
        self.member_search_input.setMinimumWidth(300)
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.member_search_input)
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        layout.addSpacing(10)
        
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "اسم المشترك", "اسم المدرب", "نوع الاشتراك", "تاريخ البدء", "تاريخ الاستحقاق", "تاريخ التجميد", "الانتهاء بعد التجميد", "الأيام المتبقية", "ملاحظات", "الحالة", "الإجراءات"
        ])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch) # Notes
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Interactive) # Actions
        self.table.setColumnWidth(10, 360)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        self.refresh_members_table()

    def export_to_excel(self):
        from PyQt6.QtWidgets import QMessageBox
        from business_logic import export_members_to_excel
        import os
        from datetime import datetime
        
        # Save to the user's Downloads folder
        export_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.exists(export_dir):
            os.makedirs(export_dir, exist_ok=True)
            
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"مشتركين_{timestamp}.xlsx"
        path = os.path.join(export_dir, filename)
        
        success, msg = export_members_to_excel(path)
        if success:
            QMessageBox.information(self, "نجاح", f"تم تصدير البيانات بنجاح إلى ملف:\n{path}")
        else:
            QMessageBox.warning(self, "خطأ", msg)

    def import_from_excel(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from business_logic import smart_import_members
        path, _ = QFileDialog.getOpenFileName(self, "استيراد من Excel", "", "Excel Files (*.xlsx *.xls)")
        if path:
            success, msg = smart_import_members(path)
            if success:
                QMessageBox.information(self, "نجاح", msg)
                self.refresh_members_table()
                self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "خطأ", msg)

    def refresh_members_table(self):
        session = get_session()
        try:
            search_query = ""
            if hasattr(self, 'member_search_input'):
                search_query = self.member_search_input.text().strip()
            
            if search_query:
                from sqlalchemy import or_
                members = session.query(Member).filter(
                    or_(
                        Member.name.ilike(f"%{search_query}%"),
                        Member.phone.ilike(f"%{search_query}%"),
                        Member.trainer_name.ilike(f"%{search_query}%")
                    )
                ).order_by(Member.id.desc()).all()
            else:
                members = session.query(Member).order_by(Member.id.desc()).all()
            self.table.setRowCount(len(members))
            
            for row, m in enumerate(members):
                name_item = QTableWidgetItem(m.name)
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 0, name_item)
                
                trainer_item = QTableWidgetItem(m.trainer_name or "-")
                trainer_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 1, trainer_item)
                
                plan_item = QTableWidgetItem(m.plan_name)
                plan_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 2, plan_item)
                
                start_item = QTableWidgetItem(str(m.start_date))
                start_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 3, start_item)
                
                end_item = QTableWidgetItem(str(m.end_date))
                end_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 4, end_item)
                
                freeze_date_str = str(m.frozen_date) if m.frozen_date else "-"
                freeze_item = QTableWidgetItem(freeze_date_str)
                freeze_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 5, freeze_item)
                
                after_freeze_str = str(m.end_date) if m.last_return_date else "-"
                after_freeze_item = QTableWidgetItem(after_freeze_str)
                after_freeze_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 6, after_freeze_item)

                today = date.today()
                if m.status == 'frozen':
                    days_left = m.remaining_days_when_frozen
                    days_str = f"{days_left} (مجمد)"
                elif m.status == 'pending':
                    days_left = 999
                    days_str = "- (تأجيل)"
                else:
                    days_left = (m.end_date - today).days
                    days_str = str(days_left) if days_left > 0 else "منتهي"
                
                days_item = QTableWidgetItem(days_str)
                days_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if days_left <= 3 and m.status not in ['frozen', 'pending']:
                    days_item.setForeground(QColor("#ef4444"))
                    days_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.table.setItem(row, 7, days_item)
                
                notes_item = QTableWidgetItem(m.notes or "")
                notes_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, 8, notes_item)
                
                status_str = "نشط" if m.status == 'active' else "مجمد" if m.status == 'frozen' else "قيد الانتظار" if m.status == 'pending' else "منتهي"
                status_item = QTableWidgetItem(status_str)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if m.status == 'active':
                    status_item.setForeground(QColor("#10b981"))
                elif m.status == 'frozen':
                    status_item.setForeground(QColor("#f59e0b"))
                elif m.status == 'pending':
                    status_item.setForeground(QColor("#ea580c"))
                else:
                    status_item.setForeground(QColor("#ef4444"))
                
                font = QFont()
                font.setBold(True)
                status_item.setFont(font)
                self.table.setItem(row, 9, status_item)
                self.table.setRowHeight(row, 48)
                # Actions
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(4)
                
                btn_style = "QPushButton { color: white; font-weight: bold; font-size: 11px; padding: 4px 8px; border-radius: 5px; border: none; min-height: 26px; } QPushButton:hover { opacity: 0.9; }"
                
                if m.status == 'active':
                    freeze_btn = QPushButton("تجميد ⏸️")
                    freeze_btn.setStyleSheet("background-color: #f59e0b; " + btn_style)
                    freeze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    freeze_btn.clicked.connect(lambda checked, mid=m.id: self.freeze_member(mid))
                    action_layout.addWidget(freeze_btn)
                elif m.status == 'frozen':
                    unfreeze_btn = QPushButton("فك التجميد ▶️")
                    unfreeze_btn.setStyleSheet("background-color: #10b981; " + btn_style)
                    unfreeze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    unfreeze_btn.clicked.connect(lambda checked, mid=m.id: self.unfreeze_member(mid))
                    action_layout.addWidget(unfreeze_btn)
                elif m.status == 'pending':
                    activate_btn = QPushButton("تفعيل ▶️")
                    activate_btn.setStyleSheet("background-color: #ea580c; " + btn_style)
                    activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    activate_btn.clicked.connect(lambda checked, mid=m.id: self.activate_pending_member_gui(mid))
                    action_layout.addWidget(activate_btn)
                
                face_btn = QPushButton("بصمة الوجه 👤")
                face_btn.setStyleSheet("background-color: #6366f1; " + btn_style)
                face_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                face_btn.clicked.connect(lambda checked, mid=m.id: self.register_face(mid))
                action_layout.addWidget(face_btn)
                
                del_btn = QPushButton("حذف 🗑️")
                del_btn.setStyleSheet("background-color: #ef4444; " + btn_style)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.clicked.connect(lambda checked, mid=m.id: self.delete_member(mid))
                action_layout.addWidget(del_btn)
                
                card_btn = QPushButton("البطاقة 💳")
                card_btn.setStyleSheet("background-color: #3b82f6; " + btn_style)
                card_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                card_btn.clicked.connect(lambda checked, mid=m.id: self.show_member_card(mid))
                action_layout.addWidget(card_btn)
                
                self.table.setCellWidget(row, 10, action_widget)
                
        finally:
            session.close()

    def register_face(self, member_id):
        session = get_session()
        try:
            m = session.query(Member).get(member_id)
            if m and m.has_face_registered:
                QMessageBox.information(
                    self,
                    "بصمة الوجه مسجلة",
                    f"بصمة الوجه للمشترك ({m.name}) مسجلة سابقاً وتعمل تلقائياً دون الحاجة لإعادة التسجيل."
                )
                return
        finally:
            session.close()
            
        dialog = FaceRegistrationDialog(member_id, self)
        dialog.exec()

    def setup_payments(self):
        layout = QVBoxLayout(self.payments_page)
        layout.setContentsMargins(20, 20, 20, 20)
        header_layout = QHBoxLayout()
        title = QLabel("سجل المدفوعات والاشتراكات")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #334155;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        add_payment_btn = QPushButton("➕ إضافة دفعة يدوية")
        add_payment_btn.setObjectName("PrimaryButton")
        add_payment_btn.clicked.connect(self.show_add_payment_dialog)
        header_layout.addWidget(add_payment_btn)
        layout.addLayout(header_layout)
        layout.addSpacing(20)
        
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(6)
        self.payments_table.setHorizontalHeaderLabels(["رقم الوصل", "المشترك / الوصف", "المبلغ المدفوع", "طريقة الدفع", "التاريخ", "الإجراءات / الحالة"])
        self.payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payments_table.setAlternatingRowColors(True)
        self.payments_table.verticalHeader().setVisible(False)
        self.payments_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.payments_table)
        self.refresh_payments_table()

    def refresh_payments_table(self):
        from business_logic import backfill_missing_payments
        backfill_missing_payments()
        session = get_session()
        from database import Payment
        try:
            payments = session.query(Payment).order_by(Payment.id.desc()).all()
            self.payments_table.setRowCount(len(payments))
            for row, p in enumerate(payments):
                self.payments_table.setRowHeight(row, 48)
                receipt_val = p.receipt_number if p.receipt_number else f"REC-{p.id}"
                rec_item = QTableWidgetItem(str(receipt_val))
                rec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.payments_table.setItem(row, 0, rec_item)
                
                member_name = p.member.name if p.member else p.plan_name
                name_item = QTableWidgetItem(member_name)
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.payments_table.setItem(row, 1, name_item)
                
                amount_item = QTableWidgetItem(f"{p.amount:,.0f} د.ع")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.payments_table.setItem(row, 2, amount_item)
                
                method_item = QTableWidgetItem(p.payment_method)
                method_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if "آجل" in p.payment_method or "دين" in p.payment_method:
                    method_item.setForeground(QColor("#ef4444"))
                    method_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                elif "مسدد" in p.payment_method or "تسديد" in p.payment_method:
                    method_item.setForeground(QColor("#10b981"))
                    method_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                self.payments_table.setItem(row, 3, method_item)
                
                date_item = QTableWidgetItem(p.payment_date.strftime("%Y-%m-%d"))
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.payments_table.setItem(row, 4, date_item)
                
                # Actions column
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 4, 4, 4)
                action_layout.setSpacing(6)
                
                if "آجل" in p.payment_method or "دين" in p.payment_method:
                    pay_btn = QPushButton("تسديد الدين 💰")
                    pay_btn.setStyleSheet("background-color: #10b981; color: white; padding: 6px 12px; font-size: 12px; font-weight: bold; border-radius: 5px; border: none; min-height: 24px;")
                    pay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    pay_btn.clicked.connect(lambda checked, pid=p.id: self.settle_debt_dialog(pid))
                    action_layout.addWidget(pay_btn)
                else:
                    status_lbl = QLabel("مسدد 🟢")
                    status_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
                    status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    action_layout.addWidget(status_lbl)
                    
                self.payments_table.setCellWidget(row, 5, action_widget)
        finally:
            session.close()

    def settle_debt_dialog(self, payment_id):
        session = get_session()
        from database import Payment
        try:
            payment = session.query(Payment).get(payment_id)
            if not payment: return
            
            from PyQt6.QtWidgets import QInputDialog, QMessageBox
            methods = ["نقدي", "بطاقة", "تحويل"]
            member_name = payment.member.name if payment.member else payment.plan_name
            method, ok = QInputDialog.getItem(self, "تسديد الدين", 
                f"اختر طريقة دفع الدين للمشترك ({member_name}) بمبلغ {payment.amount:,.0f} د.ع:",
                methods, 0, False)
                
            if ok and method:
                payment.payment_method = f"تم التسديد ({method})"
                session.commit()
                
                reply_print = QMessageBox.question(self, "طباعة الوصل", 
                    "تم تسديد الدين بنجاح! هل تريد طباعة وصل التسديد الآن؟",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes)
                    
                if reply_print == QMessageBox.StandardButton.Yes:
                    from print_utils import print_receipt
                    print_receipt(self, payment.receipt_number, member_name, payment.amount, payment.plan_name, payment.payment_date.strftime('%Y-%m-%d'))
                    
                self.refresh_payments_table()
                self.refresh_dashboard()
                self.show_toast("تم تسديد الدين بنجاح", is_success=True)
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء تسديد الدين: {str(e)}")
        finally:
            session.close()

    def show_add_payment_dialog(self):
        dialog = AddPaymentDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['amount']:
                QMessageBox.warning(self, "خطأ", "يرجى إدخال المبلغ")
                return
            try:
                session = get_session()
                from database import Payment
                import time
                
                receipt = data.get('receipt_number', '').strip()
                if not receipt:
                    last_payment = session.query(Payment).order_by(Payment.id.desc()).first()
                    next_id = (last_payment.id + 1) if last_payment else 1
                    receipt = f"REC-{next_id}"
                    
                new_payment = Payment(
                    amount=float(data['amount']),
                    payment_method=data['payment_method'],
                    plan_name=data['desc'],
                    receipt_number=receipt
                )
                session.add(new_payment)
                session.commit()
                
                # Get the assigned id and date
                session.refresh(new_payment)
                
                self.refresh_payments_table()
                self.refresh_dashboard()
                
                reply = QMessageBox.question(self, "نجاح", "تم تسجيل الدفعة بنجاح.\nهل تريد طباعة وصل الاستلام؟", 
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                             QMessageBox.StandardButton.Yes)
                if reply == QMessageBox.StandardButton.Yes:
                    from print_utils import print_receipt
                    payer_name = new_payment.member.name if new_payment.member else new_payment.plan_name
                    success, msg = print_receipt(self, new_payment.receipt_number, payer_name, new_payment.amount, new_payment.plan_name, new_payment.payment_date.strftime('%Y-%m-%d'))
                    if not success:
                        QMessageBox.warning(self, "خطأ", msg)
                        
            except Exception as e:
                session.rollback()
                QMessageBox.warning(self, "خطأ", str(e))
            finally:
                session.close()

    def setup_reports(self):
        layout = QVBoxLayout(self.reports_page)
        layout.setContentsMargins(20, 20, 20, 20)
        header_layout = QHBoxLayout()
        title = QLabel("الإحصائيات الشاملة والتقارير المالية")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #000000; margin-bottom: 10px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        export_btn = QPushButton("📤 تصدير إلى Excel")
        export_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px; border-radius: 4px;")
        export_btn.clicked.connect(self.export_reports_to_excel)
        
        import_btn = QPushButton("📥 استيراد من Excel")
        import_btn.setStyleSheet("background-color: #f59e0b; color: white; padding: 8px; border-radius: 4px;")
        import_btn.clicked.connect(self.import_reports_from_excel)
        
        header_layout.addWidget(export_btn)
        header_layout.addWidget(import_btn)
        layout.addLayout(header_layout)
        
        stats_layout = QHBoxLayout()
        self.lbl_month_revenue = self.create_stat_card("إيرادات هذا الشهر", "0 د.ع", "#10b981")
        self.lbl_total_members_report = self.create_stat_card("إجمالي المشتركين الفعليين", "0", "#3b82f6")
        self.lbl_active_members_report = self.create_stat_card("المشتركين النشطين", "0", "#8b5cf6")
        stats_layout.addWidget(self.lbl_month_revenue['widget'])
        stats_layout.addWidget(self.lbl_total_members_report['widget'])
        stats_layout.addWidget(self.lbl_active_members_report['widget'])
        layout.addLayout(stats_layout)
        
        group_box = QGroupBox("أحدث المدفوعات")
        group_box.setStyleSheet("QGroupBox { border: 1px solid #cbd5e1; border-radius: 6px; margin-top: 15px; } QGroupBox::title { color: #64748b; subcontrol-origin: margin; left: 20px; padding: 0 5px 0 5px; }")
        g_layout = QVBoxLayout(group_box)
        g_layout.setContentsMargins(10, 20, 10, 10)
        
        self.recent_payments_table = QTableWidget()
        self.recent_payments_table.setColumnCount(4)
        self.recent_payments_table.setHorizontalHeaderLabels(["المشترك / الوصف", "المبلغ المدفوع", "طريقة الدفع", "التاريخ"])
        self.recent_payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.recent_payments_table.verticalHeader().setVisible(False)
        self.recent_payments_table.setStyleSheet("border: none;")
        self.recent_payments_table.setAlternatingRowColors(True)
        g_layout.addWidget(self.recent_payments_table)
        
        layout.addWidget(group_box)
        self.refresh_reports()

    def refresh_reports(self):
        session = get_session()
        from database import Payment
        try:
            stats = get_dashboard_stats()
            self.lbl_total_members_report['label'].setText(str(stats['total_members']))
            self.lbl_active_members_report['label'].setText(str(stats['active_members']))
            
            today = date.today()
            start_of_month = date(today.year, today.month, 1)
            if today.month == 12:
                next_month = date(today.year + 1, 1, 1)
            else:
                next_month = date(today.year, today.month + 1, 1)
                
            revenue_this_month = session.query(Payment).filter(
                Payment.payment_date >= start_of_month,
                Payment.payment_date < next_month
            ).with_entities(Payment.amount).all()
            total_revenue = sum(r[0] for r in revenue_this_month)
            self.lbl_month_revenue['label'].setText(f"{total_revenue:,.0f} د.ع")
            
            recent_payments = session.query(Payment).order_by(Payment.id.desc()).limit(50).all()
            self.recent_payments_table.setRowCount(len(recent_payments))
            for row, p in enumerate(recent_payments):
                member_name = p.member.name if p.member else p.plan_name
                name_item = QTableWidgetItem(member_name)
                name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_payments_table.setItem(row, 0, name_item)
                
                amount_item = QTableWidgetItem(f"{p.amount:,.0f} د.ع")
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_payments_table.setItem(row, 1, amount_item)
                
                method_item = QTableWidgetItem(p.payment_method)
                method_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_payments_table.setItem(row, 2, method_item)
                
                date_item = QTableWidgetItem(p.payment_date.strftime("%Y-%m-%d"))
                date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.recent_payments_table.setItem(row, 3, date_item)
        finally:
            session.close()

    def export_reports_to_excel(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        from database import get_session, Payment
        
        filepath, _ = QFileDialog.getSaveFileName(self, "حفظ كملف Excel", "Payments_Report.xlsx", "Excel Files (*.xlsx)")
        if not filepath:
            return
            
        session = get_session()
        try:
            payments = session.query(Payment).all()
            data = []
            for p in payments:
                member_name = p.member.name if p.member else p.plan_name
                receipt = p.receipt_number if p.receipt_number else f"REC-{p.id}"
                data.append({
                    "رقم الوصل": receipt,
                    "المشترك / الوصف": member_name,
                    "المبلغ المدفوع": p.amount,
                    "طريقة الدفع": p.payment_method,
                    "التاريخ": p.payment_date.strftime("%Y-%m-%d") if p.payment_date else ""
                })
            df = pd.DataFrame(data)
            df.to_excel(filepath, index=False)
            QMessageBox.information(self, "نجاح", "تم تصدير البيانات بنجاح!")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء التصدير:\n{str(e)}")
        finally:
            session.close()

    def import_reports_from_excel(self):
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        import pandas as pd
        from database import get_session, Payment
        from datetime import datetime
        
        filepath, _ = QFileDialog.getOpenFileName(self, "اختيار ملف Excel", "", "Excel Files (*.xlsx *.xls)")
        if not filepath:
            return
            
        session = get_session()
        try:
            df = pd.read_excel(filepath)
            
            required_cols = ["المبلغ المدفوع"]
            for col in required_cols:
                if col not in df.columns:
                    raise ValueError(f"العمود '{col}' مفقود من ملف الإكسل.")
                    
            count = 0
            for index, row in df.iterrows():
                try:
                    amount = float(row.get("المبلغ المدفوع", 0))
                    if pd.isna(amount) or amount <= 0:
                        continue
                        
                    desc = str(row.get("المشترك / الوصف", "دفعة مستوردة"))
                    if pd.isna(row.get("المشترك / الوصف")):
                        desc = "دفعة مستوردة"
                        
                    method = str(row.get("طريقة الدفع", "نقدي"))
                    if pd.isna(row.get("طريقة الدفع")):
                        method = "نقدي"
                        
                    receipt = str(row.get("رقم الوصل", ""))
                    if pd.isna(row.get("رقم الوصل")) or receipt.lower() == 'nan':
                        receipt = ""
                        
                    date_str = str(row.get("التاريخ", ""))
                    try:
                        p_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except Exception:
                        try:
                            p_date = pd.to_datetime(date_str).date()
                        except:
                            p_date = datetime.today().date()
                            
                    new_payment = Payment(
                        amount=amount,
                        payment_method=method,
                        plan_name=desc,
                        receipt_number=receipt,
                        payment_date=p_date
                    )
                    session.add(new_payment)
                    count += 1
                except Exception as e:
                    print(f"Skipping row {index} due to error: {e}")
                    continue
                    
            session.commit()
            self.refresh_reports()
            self.refresh_dashboard()
            self.refresh_payments_table()
            QMessageBox.information(self, "نجاح", f"تم استيراد {count} دفعة بنجاح!")
            
        except Exception as e:
            session.rollback()
            QMessageBox.warning(self, "خطأ", f"حدث خطأ أثناء الاستيراد:\n{str(e)}")
        finally:
            session.close()

    def setup_settings(self):
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("إعدادات النظام")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #334155; margin-bottom: 20px;")
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(20)
        
        gen_box = QGroupBox("⚙️ معلومات القاعة")
        gen_layout = QVBoxLayout(gen_box)
        gen_layout.setContentsMargins(20,20,20,20)
        gen_layout.setSpacing(15)
        
        self.gym_name_input = QLineEdit(self.settings.gym_name)
        self.gym_name_input.setPlaceholderText("اكتب اسم القاعة هنا...")
        self.gym_name_input.setStyleSheet("background-color: #f8fafc; border: 2px solid #cbd5e1;")
        
        self.gym_phone_input = QLineEdit(self.settings.gym_phone)
        self.gym_phone_input.setPlaceholderText("اكتب رقم الهاتف هنا...")
        self.gym_phone_input.setStyleSheet("background-color: #f8fafc; border: 2px solid #cbd5e1;")
        
        self.gym_address_input = QLineEdit(getattr(self.settings, 'gym_address', ''))
        self.gym_address_input.setPlaceholderText("اكتب العنوان هنا...")
        self.gym_address_input.setStyleSheet("background-color: #f8fafc; border: 2px solid #cbd5e1;")
        
        self.door_com_port_input = QLineEdit(getattr(self.settings, 'door_com_port', ''))
        self.door_com_port_input.setPlaceholderText("مثال: COM3")
        self.door_com_port_input.setStyleSheet("background-color: #f8fafc; border: 2px solid #cbd5e1;")

        form_layout = QFormLayout()
        form_layout.addRow("اسم القاعة:", self.gym_name_input)
        form_layout.addRow("رقم الهاتف:", self.gym_phone_input)
        form_layout.addRow("العنوان:", self.gym_address_input)
        form_layout.addRow("منفذ قفل الباب (COM Port):", self.door_com_port_input)
        gen_layout.addLayout(form_layout)
        
        save_gen_btn = QPushButton("حفظ الإعدادات")
        save_gen_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 10px 20px; font-size: 14px; font-weight: bold; border-radius: 6px; min-height: 40px;")
        save_gen_btn.clicked.connect(self.save_general_settings)
        gen_layout.addWidget(save_gen_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        scroll_layout.addWidget(gen_box)


        plans_box = QGroupBox("💡 الاشتراكات المتاحة")
        plans_layout = QVBoxLayout(plans_box)
        
        plans_header = QHBoxLayout()
        add_plan_btn = QPushButton("➕ إضافة اشتراك جديد")
        add_plan_btn.setStyleSheet("background-color: #10b981; color: white; padding: 8px 15px; font-size: 13px; font-weight: bold; border-radius: 4px; min-height: 35px;")
        add_plan_btn.clicked.connect(self.show_add_plan_dialog)
        plans_header.addWidget(add_plan_btn, alignment=Qt.AlignmentFlag.AlignRight)
        plans_header.addStretch()
        plans_layout.addLayout(plans_header)
        
        self.plans_table = QTableWidget()
        self.plans_table.setColumnCount(4)
        self.plans_table.setHorizontalHeaderLabels(["الاسم", "السعر", "المدة (أيام)", "إجراءات"])
        self.plans_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.plans_table.verticalHeader().setVisible(False)
        self.plans_table.verticalHeader().setDefaultSectionSize(48)
        plans_layout.addWidget(self.plans_table)
        self.refresh_plans_table()
        
        scroll_layout.addWidget(plans_box)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def refresh_plans_table(self):
        plans = get_all_plans()
        self.plans_table.setRowCount(len(plans))
        for row, p in enumerate(plans):
            self.plans_table.setRowHeight(row, 48)
            item0 = QTableWidgetItem(p['name'])
            item0.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.plans_table.setItem(row, 0, item0)
            
            item1 = QTableWidgetItem(f"{p['price']:,.0f} د.ع")
            item1.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.plans_table.setItem(row, 1, item1)
            
            item2 = QTableWidgetItem(str(p['duration_days']))
            item2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.plans_table.setItem(row, 2, item2)
            
            del_btn = QPushButton("حذف 🗑️")
            del_btn.setStyleSheet("background-color: #ef4444; color: white; border-radius: 5px; padding: 6px 14px; font-weight: bold; font-size: 13px; border: none; min-height: 24px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, pid=p['id']: self.remove_plan(pid))
            
            widget = QWidget()
            l = QHBoxLayout(widget)
            l.setContentsMargins(4, 4, 4, 4)
            l.addWidget(del_btn)
            self.plans_table.setCellWidget(row, 3, widget)

    def show_add_plan_dialog(self):
        dialog = AddPlanDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name'] or not data['price'] or not data['duration']:
                QMessageBox.warning(self, "خطأ", "يرجى تعبئة جميع الحقول")
                return
            try:
                success, msg = add_plan(data['name'], data['price'], data['duration'])
                if success:
                    self.refresh_plans_table()
                else:
                    QMessageBox.warning(self, "خطأ", msg)
            except ValueError:
                QMessageBox.warning(self, "خطأ", "تأكد من إدخال السعر والمدة كأرقام صحيحة.")

    def remove_plan(self, plan_id):
        reply = QMessageBox.question(self, "تأكيد", "هل أنت متأكد من حذف هذا الاشتراك؟")
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = delete_plan(plan_id)
            if success:
                self.refresh_plans_table()
            else:
                QMessageBox.warning(self, "خطأ", msg)

    def save_general_settings(self):
        success = update_settings(
            self.gym_name_input.text(),
            self.gym_phone_input.text(),
            self.gym_address_input.text(),
            self.door_com_port_input.text()
        )
        
        # Refresh global plans cache just in case if needed in combo box
        if hasattr(self, 'plan_combo'):
            pass # Usually handled via re-init
            
        if success:
            self.settings = get_settings()
            self.setWindowTitle(f"نظام الاشتراكات - {self.settings.gym_name}")
            if hasattr(self, 'lbl_title'):
                self.lbl_title.setText(self.settings.gym_name)
            QMessageBox.information(self, "نجاح", "تم حفظ الإعدادات بنجاح!")
        else:
            QMessageBox.critical(self, "خطأ", "حدث خطأ أثناء الحفظ.")

    def activate_pending_member_gui(self, member_id):
        reply = QMessageBox.question(self, 'تفعيل المباشرة', 
                                     'هل أنت متأكد من بدء اشتراك هذا المشترك من اليوم؟', 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = activate_pending_member(member_id)
            if success:
                QMessageBox.information(self, "نجاح", msg)
                self.refresh_members_table()
                self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "خطأ", msg)

    def show_add_member_dialog(self):
        dialog = AddMemberDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name'] or not data['phone']:
                QMessageBox.warning(self, "خطأ", "يرجى تعبئة الاسم ورقم الهاتف")
                return
                
            success, msg, member_id = add_new_member(
                data['name'], data['phone'], data['address'], data['landmark'],
                data['plan_name'], data['start_date'], data['payment_method'], data['notes'],
                data.get('receipt_number', ''), data.get('is_pending', False), card_id=data.get('card_id'),
                trainer_name=data.get('trainer_name', '')
            )
            if success:
                self.refresh_members_table()
                self.refresh_dashboard()
                
                # Check if member already has a registered face
                session = get_session()
                has_face = False
                try:
                    m = session.query(Member).get(member_id)
                    if m and m.has_face_registered:
                        has_face = True
                finally:
                    session.close()

                if not has_face:
                    reply = QMessageBox.question(self, "تسجيل الوجه", 
                        f"{msg}\nهل تريد تسجيل بصمة وجه المشترك الآن لفتح الباب التلقائي؟",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes)
                        
                    if reply == QMessageBox.StandardButton.Yes:
                        self.register_face(member_id)
                else:
                    self.show_toast("تم تجديد الاشتراك بنجاح (بصمة الوجه محفوظة سابقاً وتعمل تلقائياً)")
            else:
                QMessageBox.critical(self, "خطأ", msg)

    def show_member_card(self, member_id):
        session = get_session()
        try:
            if isinstance(member_id, int):
                member = session.query(Member).get(member_id)
            else:
                member = member_id
            if member:
                dialog = MemberCardDialog(member, self)
                dialog.exec()
        finally:
            session.close()

    def freeze_member(self, member_id):
        dialog = FreezeDialog(self)
        if dialog.exec():
            freeze_date = dialog.get_date()
            success, msg = freeze_membership(member_id, freeze_date)
            if success:
                QMessageBox.information(self, "نجاح", msg)
                self.refresh_members_table()
                self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "خطأ", msg)

    def unfreeze_member(self, member_id):
        session = get_session()
        try:
            member = session.query(Member).get(member_id)
            if not member:
                return
            remaining_days = member.remaining_days_when_frozen or 0
        finally:
            session.close()
            
        dialog = UnfreezeDialog(remaining_days, self)
        if dialog.exec():
            return_date = dialog.get_date()
            success, msg = unfreeze_membership(member_id, return_date)
            if success:
                QMessageBox.information(self, "نجاح", msg)
                self.refresh_members_table()
                self.refresh_dashboard()
            else:
                QMessageBox.warning(self, "خطأ", msg)
                
    def delete_member(self, member_id):
        reply = QMessageBox.question(self, 'تأكيد الحذف', 
                                     'هل أنت متأكد من حذف هذه البيانات نهائياً؟',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                member = session.query(Member).get(member_id)
                if member:
                    session.delete(member)
                    session.commit()
                    
                    from sync_manager import sync_manager
                    sync_manager.delete_member(member_id)
                    
                    QMessageBox.information(self, "نجاح", "تم الحذف بنجاح")
                    self.refresh_members_table()
                    self.refresh_dashboard()
            finally:
                session.close()

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        
        # Reset sidebar buttons
        for btn in self.nav_buttons:
            btn.setStyleSheet("""
                QPushButton { text-align: right; padding: 15px 20px; color: #475569; background: transparent; border: none; font-size: 14px; font-weight: bold; }
                QPushButton:hover { background: #e2e8f0; border-radius: 4px; }
            """)
        
        # Set active sidebar button (Blue #3b82f6 with white text, rounded corners)
        active_sidebar_style = """
            QPushButton { text-align: right; padding: 15px 20px; color: white; background: #3b82f6; border-radius: 6px; font-size: 14px; font-weight: bold; }
        """
        
        # Map stack index to nav_buttons index
        # 0=Dashboard(0), 1=Members(1), 2=Payments(4), 3=Reports(5), 4=Stats(5), 5=Settings(6)
        stack_to_nav_map = {0: 0, 1: 1, 2: 4, 3: 5, 4: 6, 5: 3}
        if index in stack_to_nav_map:
            self.nav_buttons[stack_to_nav_map[index]].setStyleSheet(active_sidebar_style)
        
        # Reset Top tabs
        for tb in self.top_tabs:
            tb.setStyleSheet("background-color: #f1f5f9; color: #64748b; border: none; padding: 15px; font-weight: bold; font-size: 14px;")
            
        active_top_tab_style = """
            QPushButton { background-color: #ffffff; border-top: 3px solid #3b82f6; border-left: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; color: #3b82f6; padding: 15px; font-weight: bold; font-size: 14px; }
        """
        if index < len(self.top_tabs):
            self.top_tabs[index].setStyleSheet(active_top_tab_style)
        
        if index == 0:
            self.refresh_dashboard()
        elif index == 1:
            self.refresh_members_table()
        elif index == 2:
            self.refresh_payments_table()
        elif index == 3:
            self.refresh_reports()
        elif index == 4:
            self.refresh_expenses()
        elif index == 5:
            self.refresh_staff()
        elif index == 6:
            self.refresh_plans_table()

    def keyPressEvent(self, event):
        import time
        from PyQt6.QtCore import Qt
        
        # Secret unlock shortcut (Ctrl + Shift + U)
        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier) and event.key() == Qt.Key.Key_U:
            self.root_stack.setCurrentIndex(0)
            self.switch_page(6) # Go to settings
            return
            
        if not hasattr(self, '_card_buffer'):
            self._card_buffer = []
            self._last_key_time = 0
            
        current_time = time.time()
        if current_time - self._last_key_time > 1.0:
            self._card_buffer = []
            
        self._last_key_time = current_time
        key = event.key()
        text = event.text()
        
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            card_id = "".join(self._card_buffer).strip()
            self._card_buffer = []
            if card_id:
                self.process_card_scan(card_id)
        else:
            if text and text.isprintable():
                self._card_buffer.append(text)
                
        super().keyPressEvent(event)

    def process_card_scan(self, card_id):
        from business_logic import get_member_by_card_id
        from remote_control import remote_control
        
        if remote_control.is_locked:
            self.show_toast("النظام مقفل - لا يمكن الدخول حالياً", is_success=False)
            return

        member = get_member_by_card_id(card_id)
        if not member:
            self.show_toast(f"الكارت رقم {card_id} غير مسجل!", is_success=False)
            return
            
        from PyQt6.QtCore import QTimer
        if member.status == 'active':
            from door_controller import open_door
            from business_logic import log_attendance
            open_door()
            log_attendance(member.id)
            self.show_toast(f"مرحباً {member.name} - تم فتح الباب", is_success=True)
            
            if hasattr(self, 'face_page') and self.face_page:
                self.face_page.status_display.setText(f"أهلاً بك {member.name}\nتم فتح الباب (بالكارت)")
                self.face_page.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #16a34a; padding: 20px; background-color: #dcfce7; border-radius: 10px;")
                QTimer.singleShot(3000, lambda: self.face_page.reset_status())
        elif member.status == 'pending':
            self.show_toast(f"عذراً {member.name} - اشتراكك قيد الانتظار", is_success=False)
            if hasattr(self, 'face_page') and self.face_page:
                self.face_page.status_display.setText(f"عذراً {member.name}\nاشتراكك قيد الانتظار")
                self.face_page.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #ea580c; padding: 20px; background-color: #ffedd5; border-radius: 10px;")
                QTimer.singleShot(3000, lambda: self.face_page.reset_status())
        else:
            self.show_toast(f"عذراً {member.name} - اشتراكك غير فعال!", is_success=False)
            if hasattr(self, 'face_page') and self.face_page:
                self.face_page.status_display.setText(f"عذراً {member.name}\nاشتراكك غير فعال")
                self.face_page.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef4444; padding: 20px; background-color: #fee2e2; border-radius: 10px;")
                QTimer.singleShot(3000, lambda: self.face_page.reset_status())

    def show_toast(self, message, is_success=True):
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import QTimer
        
        toast = QLabel(message, self)
        color = "#16a34a" if is_success else "#ef4444"
        bg_color = "#dcfce7" if is_success else "#fee2e2"
        toast.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color}; padding: 15px 30px; background-color: {bg_color}; border-radius: 8px; border: 2px solid {color};")
        toast.adjustSize()
        
        x = (self.width() - toast.width()) // 2
        y = self.height() - toast.height() - 100
        toast.move(x, y)
        toast.show()
        
        # Self destruct
        QTimer.singleShot(3500, toast.close)


    def setup_expenses(self):
        layout = QVBoxLayout(self.expenses_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        add_btn = QPushButton("➕ إضافة مصروف جديد")
        add_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 8px 15px; font-weight: bold;")
        add_btn.clicked.connect(self.show_add_expense_dialog)
        header.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        header.addStretch()
        layout.addLayout(header)
        
        self.expenses_table = QTableWidget()
        self.expenses_table.setColumnCount(6)
        self.expenses_table.setHorizontalHeaderLabels(["التاريخ", "العنوان", "التصنيف", "المبلغ", "ملاحظات", "إجراءات"])
        self.expenses_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.expenses_table.verticalHeader().setVisible(False)
        self.expenses_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.expenses_table)
        self.refresh_expenses()

    def show_add_expense_dialog(self):
        dialog = AddExpenseDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['title'] or not data['amount']: return
            from business_logic import add_expense
            success, msg = add_expense(data['title'], data['amount'], data['category'], data['notes'])
            if success:
                self.refresh_expenses()
                self.refresh_dashboard()
                self.show_toast(msg)

    def refresh_expenses(self):
        from business_logic import get_expenses
        expenses = get_expenses()
        self.expenses_table.setRowCount(len(expenses))
        for row, e in enumerate(expenses):
            self.expenses_table.setRowHeight(row, 48)
            items = [
                QTableWidgetItem(str(e.expense_date)),
                QTableWidgetItem(e.title),
                QTableWidgetItem(e.category),
                QTableWidgetItem(f"{e.amount:,.0f} د.ع"),
                QTableWidgetItem(e.notes or "")
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.expenses_table.setItem(row, col, item)
                
            del_btn = QPushButton("حذف 🗑️")
            del_btn.setStyleSheet("background-color: #ef4444; color: white; font-weight: bold; font-size: 13px; border: none; padding: 6px 14px; border-radius: 5px; min-height: 24px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, eid=e.id: self.delete_expense_gui(eid))
            
            widget = QWidget()
            l = QHBoxLayout(widget)
            l.setContentsMargins(4, 4, 4, 4)
            l.setSpacing(6)
            l.addWidget(del_btn)
            self.expenses_table.setCellWidget(row, 5, widget)

    def delete_expense_gui(self, expense_id):
        reply = QMessageBox.question(self, 'تأكيد الحذف', 'هل أنت متأكد من حذف هذا المصروف؟',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from business_logic import delete_expense
            success, msg = delete_expense(expense_id)
            if success:
                self.refresh_expenses()
                self.refresh_dashboard()
                self.show_toast("تم حذف المصروف")

    def setup_staff(self):
        layout = QVBoxLayout(self.staff_page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        add_btn = QPushButton("➕ إضافة كادر جديد")
        add_btn.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px 15px; font-weight: bold;")
        add_btn.clicked.connect(self.show_add_staff_dialog)
        header.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        header.addStretch()
        layout.addLayout(header)
        
        self.staff_table = QTableWidget()
        self.staff_table.setColumnCount(6)
        self.staff_table.setHorizontalHeaderLabels(["الاسم", "المنصب", "الراتب", "النوع", "الهاتف", "إجراءات"])
        self.staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.staff_table.verticalHeader().setVisible(False)
        self.staff_table.verticalHeader().setDefaultSectionSize(48)
        layout.addWidget(self.staff_table)
        self.refresh_staff()

    def show_add_staff_dialog(self):
        dialog = AddStaffDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name']: return
            from business_logic import add_staff
            success, msg = add_staff(data['name'], data['phone'], data['role'], data['salary'] or 0, data['salary_type'])
            if success:
                self.refresh_staff()
                self.refresh_dashboard()
                self.show_toast(msg)
            else:
                QMessageBox.critical(self, "خطأ", msg)

    def refresh_staff(self):
        from business_logic import get_all_staff, get_dashboard_stats
        stats = get_dashboard_stats()
        total_rev = stats.get('revenue_this_month', 0.0)
        
        staffs = get_all_staff()
        self.staff_table.setRowCount(len(staffs))
        for row, s in enumerate(staffs):
            self.staff_table.setRowHeight(row, 48)
            
            if s.salary_type and ("نسبة" in s.salary_type or "%" in s.salary_type):
                calculated = total_rev * ((s.salary or 0) / 100.0)
                salary_str = f"{calculated:,.0f} د.ع ({s.salary:g}%)"
            else:
                salary_str = f"{s.salary:,.0f} د.ع" if s.salary else "0 د.ع"
                
            items = [
                QTableWidgetItem(s.name),
                QTableWidgetItem(s.role),
                QTableWidgetItem(salary_str),
                QTableWidgetItem(s.salary_type),
                QTableWidgetItem(s.phone or "")
            ]
            for col, item in enumerate(items):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.staff_table.setItem(row, col, item)
                
            edit_btn = QPushButton("تعديل ✏️")
            edit_btn.setStyleSheet("background-color: #3b82f6; color: white; border: none; padding: 6px 14px; font-size: 13px; font-weight: bold; border-radius: 5px; min-height: 24px;")
            edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            edit_btn.clicked.connect(lambda checked, staff_obj=s: self.edit_staff_gui(staff_obj))

            del_btn = QPushButton("حذف 🗑️")
            del_btn.setStyleSheet("background-color: #ef4444; color: white; border: none; padding: 6px 14px; font-size: 13px; font-weight: bold; border-radius: 5px; min-height: 24px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, sid=s.id: self.delete_staff_gui(sid))
            
            widget = QWidget()
            l = QHBoxLayout(widget)
            l.setContentsMargins(4, 4, 4, 4)
            l.setSpacing(6)
            l.addWidget(edit_btn)
            l.addWidget(del_btn)
            self.staff_table.setCellWidget(row, 5, widget)

    def edit_staff_gui(self, staff_obj):
        staff_data = {
            'name': staff_obj.name,
            'phone': staff_obj.phone,
            'role': staff_obj.role,
            'salary': staff_obj.salary,
            'salary_type': staff_obj.salary_type
        }
        dialog = AddStaffDialog(self, staff_data=staff_data)
        if dialog.exec():
            data = dialog.get_data()
            if not data['name']: return
            from business_logic import update_staff
            success, msg = update_staff(staff_obj.id, data['name'], data['phone'], data['role'], data['salary'] or 0, data['salary_type'])
            if success:
                self.refresh_staff()
                self.refresh_dashboard()
                self.show_toast(msg)
            else:
                QMessageBox.critical(self, "خطأ", msg)

    def delete_staff_gui(self, staff_id):
        reply = QMessageBox.question(self, 'تأكيد الحذف', 'هل أنت متأكد من حذف هذا العضو من الكادر؟',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            from business_logic import delete_staff
            success, msg = delete_staff(staff_id)
            if success:
                self.refresh_staff()
                self.refresh_dashboard()
                self.show_toast("تم الحذف بنجاح")




class AddExpenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة مصروف جديد")
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        layout = QFormLayout(self)
        
        self.title_input = QLineEdit()
        self.amount_input = QLineEdit()
        self.category_combo = QComboBox()
        self.category_combo.addItems(["إيجار", "رواتب", "كهرباء", "صيانة", "أخرى"])
        self.notes_input = QLineEdit()
        
        layout.addRow("العنوان (الوصف):", self.title_input)
        layout.addRow("المبلغ (د.ع):", self.amount_input)
        layout.addRow("التصنيف:", self.category_combo)
        layout.addRow("ملاحظات:", self.notes_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'title': self.title_input.text(),
            'amount': self.amount_input.text(),
            'category': self.category_combo.currentText(),
            'notes': self.notes_input.text()
        }

class AddStaffDialog(QDialog):
    def __init__(self, parent=None, staff_data=None):
        super().__init__(parent)
        title = "تعديل بيانات الكادر" if staff_data else "إضافة كادر/مدرب"
        self.setWindowTitle(title)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setMinimumWidth(350)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit(staff_data.get('name', '') if staff_data else '')
        self.phone_input = QLineEdit(staff_data.get('phone', '') if staff_data else '')
        
        self.role_combo = QComboBox()
        roles = ["مدرب", "موظف استقبال", "عامل نظافة", "مدير"]
        self.role_combo.addItems(roles)
        if staff_data and staff_data.get('role') in roles:
            self.role_combo.setCurrentText(staff_data.get('role'))
        elif staff_data and staff_data.get('role'):
            self.role_combo.addItem(staff_data.get('role'))
            self.role_combo.setCurrentText(staff_data.get('role'))
            
        self.salary_type_combo = QComboBox()
        salary_types = ["ثابت", "نسبة"]
        self.salary_type_combo.addItems(salary_types)
        if staff_data and staff_data.get('salary_type') in salary_types:
            self.salary_type_combo.setCurrentText(staff_data.get('salary_type'))
        elif staff_data and staff_data.get('salary_type'):
            self.salary_type_combo.addItem(staff_data.get('salary_type'))
            self.salary_type_combo.setCurrentText(staff_data.get('salary_type'))

        salary_val = staff_data.get('salary', 0) if staff_data else ''
        salary_str = f"{salary_val:,.0f}".replace(',', '') if staff_data and salary_val else ''
        self.salary_input = QLineEdit(str(salary_str))
        
        layout.addRow("الاسم:", self.name_input)
        layout.addRow("رقم الهاتف:", self.phone_input)
        layout.addRow("المنصب:", self.role_combo)
        layout.addRow("نوع الراتب:", self.salary_type_combo)
        layout.addRow("الراتب / النسبة:", self.salary_input)
        
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("حفظ")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("إلغاء")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            'name': self.name_input.text(),
            'phone': self.phone_input.text(),
            'role': self.role_combo.currentText(),
            'salary_type': self.salary_type_combo.currentText(),
            'salary': self.salary_input.text()
        }


def main():
    init_db()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
