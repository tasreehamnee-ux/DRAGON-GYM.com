import cv2
import os
import numpy as np
from database import get_session, Member

import os
import tempfile

base_dir = os.path.dirname(os.path.abspath(__file__))
if os.access(base_dir, os.W_OK):
    MODEL_FILE = os.path.join(base_dir, 'face_model.yml')
else:
    MODEL_FILE = os.path.join(tempfile.gettempdir(), 'face_model.yml')

# Initialize LBPH Face Recognizer
if hasattr(cv2.face, 'LBPHFaceRecognizer_create'):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
else:
    print("Error: cv2.face module not found. Make sure opencv-contrib-python is installed.")
    recognizer = None

import sys
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

cascade_path = get_resource_path('haarcascade_frontalface_default.xml')
face_cascade = cv2.CascadeClassifier(cascade_path)
if face_cascade.empty():
    print("Warning: Could not load cascade classifier.")
def load_model():
    if recognizer and os.path.exists(MODEL_FILE):
        recognizer.read(MODEL_FILE)
        return True
    return False

def save_model():
    if recognizer:
        recognizer.write(MODEL_FILE)

def train_user_face(member_id, frames):
    """
    Trains the LBPH model for a specific member using a list of frames containing their face.
    frames: list of grayscale ROI images containing the face.
    """
    if not recognizer:
        return False, "Recognizer not initialized"
        
    labels = np.array([member_id] * len(frames))
    
    # If model exists, update it, otherwise train it
    if os.path.exists(MODEL_FILE):
        load_model()
        recognizer.update(frames, labels)
    else:
        recognizer.train(frames, labels)
        
    save_model()
    
    # Update DB
    session = get_session()
    try:
        member = session.query(Member).filter(Member.id == member_id).first()
        if member:
            member.has_face_registered = True
            session.commit()
            return True, "تم حفظ البصمة الوجهية بنجاح."
        return False, "لم يتم العثور على المشترك."
    except Exception as e:
        return False, str(e)
    finally:
        session.close()
        
def recognize_face(frame):
    """
    Detects face in the frame and predicts the member ID.
    Returns: (member_id, confidence, (x, y, w, h))
    """
    if not recognizer or not os.path.exists(MODEL_FILE):
        return None, 0, None
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))
    
    for (x, y, w, h) in faces:
        roi_gray = gray[y:y+h, x:x+w]
        label, confidence = recognizer.predict(roi_gray)
        
        # Confidence is distance; lower is better. 
        # Usually < 60 is a good match for LBPH.
        if confidence < 70:
            return label, confidence, (x, y, w, h)
            
    return None, 0, None
