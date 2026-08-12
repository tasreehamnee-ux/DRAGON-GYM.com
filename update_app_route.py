import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_route = '''
@app.route('/api/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.json
        img_data = data.get('image')
        if not img_data:
            return jsonify({"error": "No image provided"}), 400
            
        header, encoded = img_data.split(",", 1)
        import base64, numpy as np, cv2
        decoded = base64.b64decode(encoded)
        nparr = np.frombuffer(decoded, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        from face_recognition_system import recognize_face
        member_id, confidence, box = recognize_face(frame)
        
        if member_id and confidence < 70:
            session = get_session()
            try:
                member = session.query(Member).get(member_id)
                if member:
                    from business_logic import log_attendance
                    log_attendance(member.id)
                    return jsonify({"recognized": True, "member_name": member.name})
            finally:
                session.close()
                
        return jsonify({"recognized": False})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

content = re.sub(r'@app\.route\(''/api/process_frame''\).*?return jsonify\(\{"error": str\(e\)\}\), 500', new_route.strip(), content, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
