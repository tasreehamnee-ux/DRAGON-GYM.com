import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the start of generate_frames
start_idx = content.find('def generate_frames():')

# Find the end of video_feed
end_idx = content.find('def payments_api():')

if start_idx != -1 and end_idx != -1:
    # Find the preceding decorator for payments_api
    end_idx = content.rfind('@app.route', start_idx, end_idx)
    
    # Replace the chunk
    new_content = content[:start_idx] + content[end_idx:]
    
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
        print('Successfully removed generate_frames')
