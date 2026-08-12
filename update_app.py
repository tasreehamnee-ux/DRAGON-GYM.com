import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the old generate_frames and video_feed functions
content = re.sub(r'def generate_frames\(\):.*?@app\.route\(''/video_feed''\)\ndef video_feed\(\):.*?\n    return Response.*?boundary=frame''\)\n', '', content, flags=re.DOTALL)

# Add new API endpoints
new_endpoints = '''
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

'''

content = content.replace('camera_active = False\ncap = None\n', 'camera_active = False\ncap = None\n' + new_endpoints)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
