import cv2
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox, QWidget, QApplication
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
from face_recognition_system import train_user_face, recognize_face, face_cascade
from database import get_session, Member

class FaceRegistrationDialog(QDialog):
    def __init__(self, member_id, parent=None):
        super().__init__(parent)
        self.member_id = member_id
        self.setWindowTitle("تسجيل بصمة الوجه")
        self.setFixedSize(640, 560)
        self.setStyleSheet("background-color: #ffffff;")
        
        layout = QVBoxLayout(self)
        
        self.status_label = QLabel("يرجى النظر إلى الكاميرا بشكل مباشر...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b;")
        layout.addWidget(self.status_label)
        
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setFixedSize(600, 400)
        self.video_label.setStyleSheet("background-color: #000000; border: 2px solid #cbd5e1; border-radius: 8px;")
        layout.addWidget(self.video_label)
        
        self.capture_btn = QPushButton("التقاط وتسجيل الوجه")
        self.capture_btn.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold; padding: 10px; border-radius: 6px; font-size: 14px;")
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        self.cap = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        
        self.is_capturing = False
        self.captured_frames = []
        self.capture_count = 0
        self.required_frames = 20
        
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
            
        # Optional: flip frame for mirror effect
        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        faces = []
        if not face_cascade.empty():
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
        else:
            self.status_label.setText("خطأ: تعذر تحميل ملف التعرف على الوجوه (haarcascade)")
        
        for (x, y, w, h) in faces:
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            if self.is_capturing:
                roi = gray[y:y+h, x:x+w]
                self.captured_frames.append(roi)
                
                if self.capture_count == 0:
                    import os
                    os.makedirs('profiles', exist_ok=True)
                    # save color crop with some padding if possible
                    color_roi = frame[max(0, y-20):min(frame.shape[0], y+h+20), max(0, x-20):min(frame.shape[1], x+w+20)]
                    cv2.imwrite(f'profiles/{self.member_id}.jpg', color_roi)
                
                self.capture_count += 1
                self.status_label.setText(f"جاري الالتقاط... {self.capture_count}/{self.required_frames}")
                
                if self.capture_count >= self.required_frames:
                    self.is_capturing = False
                    self.process_training()
                    
        rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image).scaled(600, 400, Qt.AspectRatioMode.KeepAspectRatio))
        
    def start_capture(self):
        self.is_capturing = True
        self.captured_frames = []
        self.capture_count = 0
        self.capture_btn.setEnabled(False)
        
    def process_training(self):
        self.timer.stop()
        self.status_label.setText("جاري حفظ بصمة الوجه، يرجى الانتظار...")
        # Force UI update
        QApplication.processEvents()
        
        success, msg = train_user_face(self.member_id, self.captured_frames)
        if success:
            QMessageBox.information(self, "نجاح", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "خطأ", msg)
            self.capture_btn.setEnabled(True)
            self.timer.start(30)
            
    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        self.timer.stop()
        event.accept()


class FaceMonitorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("المراقبة والتحكم بالباب")
        self.setStyleSheet("background-color: #f8fafc;")
        
        layout = QHBoxLayout(self)
        
        # Left side: Camera feed
        left_panel = QVBoxLayout()
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("background-color: #000; border: 3px solid #334155; border-radius: 10px;")
        left_panel.addWidget(self.video_label)
        
        self.start_btn = QPushButton("بدء المراقبة")
        self.start_btn.setStyleSheet("background-color: #10b981; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        self.start_btn.clicked.connect(self.toggle_monitoring)
        left_panel.addWidget(self.start_btn)
        
        layout.addLayout(left_panel)
        
        # Right side: Status and Logs
        right_panel = QVBoxLayout()
        
        self.status_display = QLabel("نظام المراقبة متوقف")
        self.status_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #475569; padding: 20px; background-color: #e2e8f0; border-radius: 10px;")
        right_panel.addWidget(self.status_display)
        
        right_panel.addStretch()
        layout.addLayout(right_panel)
        
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        self.is_monitoring = False
        self.last_recognized_id = None
        self.consecutive_recognitions = 0
        
    def toggle_monitoring(self):
        if self.is_monitoring:
            self.is_monitoring = False
            self.timer.stop()
            if self.cap:
                self.cap.release()
            self.start_btn.setText("بدء المراقبة")
            self.start_btn.setStyleSheet("background-color: #10b981; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
            self.video_label.clear()
            self.status_display.setText("نظام المراقبة متوقف")
            self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #475569; padding: 20px; background-color: #e2e8f0; border-radius: 10px;")
        else:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "خطأ", "لا يمكن الوصول إلى الكاميرا!")
                return
                
            self.is_monitoring = True
            self.timer.start(30)
            self.start_btn.setText("إيقاف المراقبة")
            self.start_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
            self.status_display.setText("جاري المراقبة...")
            self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #3b82f6; padding: 20px; background-color: #dbeafe; border-radius: 10px;")

    def update_frame(self):
        if not self.is_monitoring or not self.cap:
            return
            
        ret, frame = self.cap.read()
        if not ret:
            return
            
        frame = cv2.flip(frame, 1)
        display_frame = frame.copy()
        
        member_id, confidence, box = recognize_face(frame)
        
        if member_id is not None and box is not None:
            x, y, w, h = box
            cv2.rectangle(display_frame, (x, y), (x+w, y+h), (255, 165, 0), 2)
            
            if member_id == self.last_recognized_id:
                self.consecutive_recognitions += 1
            else:
                self.last_recognized_id = member_id
                self.consecutive_recognitions = 1
                
            # If recognized consistently for ~15 frames (half a second)
            if self.consecutive_recognitions == 15:
                self.handle_door_access(member_id)
                self.consecutive_recognitions = 0 # reset to prevent spamming
        else:
            self.last_recognized_id = None
            self.consecutive_recognitions = 0
            
        rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image).scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio))
        
    def handle_door_access(self, member_id):
        from remote_control import remote_control
        if remote_control.is_locked:
            self.status_display.setText("النظام مقفل - لا يمكن الدخول")
            self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef4444; padding: 20px; background-color: #fee2e2; border-radius: 10px;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.reset_status())
            return
            
        session = get_session()
        try:
            member = session.query(Member).filter(Member.id == member_id).first()
            if member:
                if member.status == 'active':
                    # HERE is where the physical door opening logic goes
                    print(f"OPEN DOOR FOR: {member.name}")
                    from door_controller import open_door
                    from business_logic import log_attendance
                    open_door()
                    log_attendance(member.id)
                    self.status_display.setText(f"أهلاً بك {member.name}\nتم فتح الباب")
                    self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #16a34a; padding: 20px; background-color: #dcfce7; border-radius: 10px;")
                elif member.status == 'pending':
                    print(f"ACCESS PENDING FOR: {member.name}")
                    self.status_display.setText(f"عذراً {member.name}\nاشتراكك قيد الانتظار، يرجى مراجعة الإدارة للتفعيل")
                    self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #ea580c; padding: 20px; background-color: #ffedd5; border-radius: 10px;")
                else:
                    print(f"ACCESS DENIED FOR: {member.name}")
                    self.status_display.setText(f"عذراً {member.name}\nاشتراكك غير فعال")
                    self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef4444; padding: 20px; background-color: #fee2e2; border-radius: 10px;")
                
                # Revert status text after 3 seconds
                QTimer.singleShot(3000, lambda: self.reset_status())
        except Exception as e:
            print(f"Error handling access: {e}")
        finally:
            session.close()
            
    def reset_status(self):
        if self.is_monitoring:
            self.status_display.setText("جاري المراقبة...")
            self.status_display.setStyleSheet("font-size: 24px; font-weight: bold; color: #3b82f6; padding: 20px; background-color: #dbeafe; border-radius: 10px;")

    def closeEvent(self, event):
        if self.is_monitoring:
            self.toggle_monitoring()
        event.accept()
