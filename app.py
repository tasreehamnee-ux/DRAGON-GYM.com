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

def generate_frames():
    global cap
    if not FACE_RECOGNITION_ENABLED:
        # Fallback if cv2 is not available
        import time
        while camera_active:
            time.sleep(1)
            yield (b'--frame\r\n'
                   b'Content-Type: text/plain\r\n\r\n' + b'Camera unavailable' + b'\r\n')
        return

    last_detected_id = None
    import time
    last_log_time = 0
    
    while camera_active:
        if cap is None or not cap.isOpened():
            break
            
        success, frame = cap.read()
        if not success:
            break
        
        frame = cv2.flip(frame, 1)
        
        global enrollment_member, enrollment_frames, enrollment_status
        if enrollment_status == "capturing" and enrollment_member is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            from face_recognition_system import face_cascade
            faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                cv2.putText(frame, f"Capturing... {len(enrollment_frames)}/30", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                roi = gray[y:y+h, x:x+w]
                enrollment_frames.append(roi)
                break
                
            if len(enrollment_frames) >= 30:
                from face_recognition_system import train_user_face
                success, msg = train_user_face(enrollment_member, enrollment_frames)
                if success:
                    enrollment_status = "success"
                else:
                    enrollment_status = "error"
                enrollment_member = None
                enrollment_frames = []
        else:
            # Call the existing recognition logic
            try:
                member_id, confidence, box = recognize_face(frame)
            except:
                member_id = None
            
            if member_id is not None:
                # Draw box around face
                x, y, w, h = box
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {member_id}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                
                # Log attendance every 10 seconds to avoid spamming
                if member_id != last_detected_id or (time.time() - last_log_time) > 10:
                    try:
                        log_attendance(member_id)
                        last_detected_id = member_id
                        last_log_time = time.time()
                    except:
                        pass

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Start the Firebase listener in the background
def start_firebase():
    remote_control.start_listening()

firebase_thread = threading.Thread(target=start_firebase, daemon=True)
firebase_thread.start()

@app.route('/')
def index():
    if remote_control.is_locked:
        return "System is locked due to license expiration or remote lock command."
    return render_template('index.html')

@app.route('/api/stats')
def stats():
    try:
        data = get_dashboard_stats()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/plans', methods=['GET', 'POST'])
def plans():
    try:
        if request.method == 'POST':
            data = request.json
            name = data.get('name')
            price = data.get('price')
            duration = data.get('duration')
            success, msg = update_plan_price_or_create(name, price, duration)
            if success:
                return jsonify({"message": msg})
            else:
                return jsonify({"error": msg}), 400
                
        plans_list = get_all_plans()
        # get_all_plans already returns a list of dicts: [{"id":..., "name":..., "price":..., "duration_days":...}]
        # Map duration_days to duration for the frontend
        return jsonify([{"id": p["id"], "name": p["name"], "duration": p["duration_days"], "price": p["price"]} for p in plans_list])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def delete_plan_api(plan_id):
    from business_logic import delete_plan
    try:
        success, msg = delete_plan(plan_id)
        if success:
            return jsonify({"message": msg})
        return jsonify({"error": msg}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/settings', methods=['GET', 'POST'])
def system_settings():
    if request.method == 'POST':
        data = request.json
        gym_name = data.get('gym_name', '')
        gym_phone = data.get('gym_phone', '')
        gym_address = data.get('gym_address', '')
        door_com_port = data.get('door_com_port', '')
        success = update_settings(gym_name, gym_phone, gym_address, door_com_port)
        if success:
            return jsonify({"message": "تم الحفظ بنجاح"})
        return jsonify({"error": "حدث خطأ أثناء الحفظ"}), 400
        
    s = get_settings()
    return jsonify({
        "gym_name": s.gym_name,
        "gym_phone": s.gym_phone,
        "gym_address": s.gym_address,
        "door_com_port": s.door_com_port
    })

@app.route('/api/export_members')
def export_members():
    try:
        filepath = os.path.join(os.getcwd(), 'members_export.xlsx')
        success, msg = export_members_to_excel(filepath)
        if success and os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        return "فشل التصدير", 500
    except Exception as e:
        return str(e), 500

@app.route('/api/members', methods=['GET', 'POST'])
def members():
    session = get_session()
    try:
        if request.method == 'POST':
            data = request.json
            name = data.get('name')
            phone = data.get('phone')
            address = data.get('address', '')
            plan_name = data.get('plan_name')
            start_date = data.get('start_date')
            payment_method = data.get('payment_method', 'كاش')
            
            trainer_name = data.get('trainer_name', '')
            card_id = data.get('card_id', '')
            landmark = data.get('landmark', '')
            receipt_number = data.get('receipt_number', '')
            notes = data.get('notes', '')
            is_pending = data.get('is_pending', False)
            
            from datetime import datetime
            dt_start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else datetime.today().date()
            
            success, msg, member_id = add_new_member(
                name=name, phone=phone, address=address, landmark=landmark,
                plan_name=plan_name, start_date=dt_start, payment_method=payment_method,
                notes=notes, receipt_number=receipt_number, is_pending=is_pending,
                card_id=card_id, trainer_name=trainer_name
            )
            
            if success:
                return jsonify({"message": msg, "id": member_id}), 201
            else:
                return jsonify({"error": msg}), 400
                
        # GET method logic
        members_query = session.query(Member).order_by(Member.id.desc()).all()
        members_list = []
        for m in members_query:
            from datetime import date
            remaining = 0
            if m.end_date:
                remaining = (m.end_date - date.today()).days
                if remaining < 0: remaining = 0
                
            members_list.append({
                "id": m.id,
                "name": m.name,
                "phone": m.phone,
                "trainer_name": m.trainer_name or '',
                "plan": m.plan_name,
                "start_date": str(m.start_date) if m.start_date else '',
                "end_date": str(m.end_date) if m.end_date else '',
                "frozen_date": str(getattr(m, 'frozen_date', '')) if getattr(m, 'frozen_date', None) else '-',
                "last_return_date": str(getattr(m, 'last_return_date', '')) if getattr(m, 'last_return_date', None) else '-',
                "remaining_days": remaining,
                "notes": m.notes or '',
                "status": m.status
            })
        return jsonify(members_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/api/members/<int:member_id>', methods=['GET', 'DELETE'])
def get_member(member_id):
    session = get_session()
    try:
        m = session.query(Member).get(member_id)
        if not m:
            return jsonify({"error": "المشترك غير موجود"}), 404
            
        if request.method == 'DELETE':
            # Also delete associated payments if any
            from database import Payment
            session.query(Payment).filter(Payment.member_id == member_id).delete()
            session.delete(m)
            session.commit()
            return jsonify({"message": "تم الحذف بنجاح"})
            
        return jsonify({
            "id": m.id,
            "name": m.name,
            "phone": m.phone,
            "card_id": m.card_id,
            "address": m.address,
            "trainer_name": m.trainer_name,
            "plan_name": m.plan_name,
            "start_date": str(m.start_date),
            "end_date": str(m.end_date),
            "status": m.status,
            "notes": m.notes
        })
    finally:
        session.close()

@app.route('/api/members/<int:member_id>/freeze', methods=['POST'])
def api_freeze_member(member_id):
    from business_logic import freeze_membership
    from datetime import date
    try:
        success, msg = freeze_membership(member_id, date.today())
        if success:
            return jsonify({"message": msg})
        return jsonify({"error": msg}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/export_excel', methods=['GET'])
def api_export_excel():
    from business_logic import export_members_to_excel
    import os
    filepath = "members_export.xlsx"
    export_members_to_excel(filepath)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "Failed to generate Excel"}), 500

@app.route('/api/import_excel', methods=['POST'])
def api_import_excel():
    from business_logic import smart_import_members
    import os
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if file:
        filepath = "temp_import.xlsx"
        file.save(filepath)
        try:
            success = smart_import_members(filepath)
            os.remove(filepath)
            if success:
                return jsonify({"message": "تم استيراد البيانات بنجاح"})
            return jsonify({"error": "فشل الاستيراد"}), 500
        except Exception as e:
            if os.path.exists(filepath): os.remove(filepath)
            return jsonify({"error": str(e)}), 500

@app.route('/api/toggle_camera', methods=['POST'])
def toggle_camera():
    global camera_active, cap
    
    data = request.json
    turn_on = data.get('active', False)
    
    if turn_on:
        if not camera_active:
            if FACE_RECOGNITION_ENABLED:
                cap = cv2.VideoCapture(0)
            camera_active = True
        return jsonify({"status": "on"})
    else:
        camera_active = False
        if cap and FACE_RECOGNITION_ENABLED:
            cap.release()
            cap = None
        return jsonify({"status": "off"})

@app.route('/video_feed')
def video_feed():
    if not camera_active:
        return "", 204
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

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
