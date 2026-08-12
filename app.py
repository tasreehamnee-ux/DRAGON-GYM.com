from flask import Flask, render_template, jsonify, request, send_file, Response
from business_logic import get_dashboard_stats, get_all_plans, add_new_member, update_plan_price_or_create, export_members_to_excel, get_settings, update_settings, log_attendance
from database import get_session, Member, Payment, Staff
from remote_control import remote_control
import threading
import os

try:
    from face_recognition_system import recognize_face
    import cv2
    FACE_RECOGNITION_ENABLED = True
except Exception as e:
    print(f"Face recognition disabled due to error: {e}")
    FACE_RECOGNITION_ENABLED = False

app = Flask(__name__)

camera_active = False
cap = None

import base64
import numpy as np
import cv2

@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        img_data = data.get('image')
        if not img_data:
            return jsonify({"error": "No image provided"}), 400
            
        header, encoded = img_data.split(",", 1)
        decoded = base64.b64decode(encoded)
        nparr = np.frombuffer(decoded, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        from face_recognition_system import detect_faces, recognize_faces
        faces = detect_faces(frame)
        if len(faces) == 0:
            return jsonify({"recognized": False})
            
        (x, y, w, h) = faces[0]
        face_roi = frame[y:y+h, x:x+w]
        
        member_id, confidence = recognize_faces(face_roi)
        
        if member_id and confidence > 40:
            session = get_session()
            try:
                member = session.query(Member).get(member_id)
                if member:
                    # Log attendance
                    from business_logic import log_attendance
                    log_attendance(member.id)
                    return jsonify({"recognized": True, "member_name": member.name})
            finally:
                session.close()
                
        return jsonify({"recognized": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/payments', methods=['GET', 'POST'])
def payments_api():
    session = get_session()
    try:
        if request.method == 'POST':
            data = request.json
            desc = data.get('description', '')
            amount = float(data.get('amount', 0))
            method = data.get('method', 'نقدي')
            receipt = data.get('receipt', '')
            
            new_p = Payment(
                amount=amount,
                payment_method=method,
                plan_name=desc,
                receipt_number=receipt
            )
            session.add(new_p)
            session.commit()
            return jsonify({"message": "تم إضافة الدفعة بنجاح"})
            
        else:
            payments = session.query(Payment, Member.name).outerjoin(Member, Payment.member_id == Member.id).order_by(Payment.id.desc()).limit(100).all()
            result = []
            for p, m_name in payments:
                result.append({
                    "receipt": p.receipt_number or f"REC-{p.id}",
                    "member_name": m_name or p.plan_name or "غير معروف",
                    "amount": p.amount,
                    "method": p.payment_method,
                    "date": str(p.payment_date)
                })
            return jsonify(result)
    finally:
        session.close()

enrollment_member = None
enrollment_frames = []
enrollment_status = ""

@app.route('/api/enroll_face/<int:member_id>', methods=['POST'])
def enroll_face_api(member_id):
    global enrollment_member, enrollment_frames, camera_active, enrollment_status
    if not camera_active:
        return jsonify({"error": "يرجى تشغيل الكاميرا أولاً من بوابة الدخول لتتمكن من تسجيل البصمة."}), 400
    
    enrollment_frames = []
    enrollment_status = "capturing"
    enrollment_member = member_id
    
    import time
    timeout = 10
    start = time.time()
    while enrollment_status == "capturing" and time.time() - start < timeout:
        time.sleep(0.5)
        
    if enrollment_status == "success":
        return jsonify({"message": "تم التقاط بصمة الوجه وحفظها بنجاح!"})
    elif enrollment_status == "error":
        return jsonify({"error": "فشل حفظ البصمة."}), 500
    else:
        enrollment_member = None
        enrollment_status = ""
        return jsonify({"error": "انتهى الوقت ولم يتمكن النظام من التقاط الوجه بوضوح."}), 400

@app.route('/api/staff', methods=['GET', 'POST', 'DELETE'])
def staff_api():
    session = get_session()
    try:
        if request.method == 'POST':
            data = request.json
            new_staff = Staff(
                name=data.get('name'),
                role=data.get('role'),
                salary=float(data.get('salary', 0)),
                salary_type=data.get('salary_type'),
                phone=data.get('phone')
            )
            session.add(new_staff)
            session.commit()
            return jsonify({"message": "تم الإضافة"})
            
        elif request.method == 'GET':
            staff_members = session.query(Staff).all()
            return jsonify([{
                "id": s.id, "name": s.name, "role": s.role,
                "salary": s.salary, "salary_type": s.salary_type, "phone": s.phone
            } for s in staff_members])
            
    finally:
        session.close()

@app.route('/api/staff/<int:staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    session = get_session()
    try:
        s = session.query(Staff).get(staff_id)
        if s:
            session.delete(s)
            session.commit()
            return jsonify({"message": "تم الحذف"})
        return jsonify({"error": "غير موجود"}), 404
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
