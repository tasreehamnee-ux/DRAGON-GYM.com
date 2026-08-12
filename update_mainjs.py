import codecs

with codecs.open('static/js/main.js', 'r', 'utf-8') as f:
    content = f.read()

new_js = '''
let isCameraOn = false;
let cameraStream = null;
let captureInterval = null;

async function toggleCamera() {
    isCameraOn = !isCameraOn;
    const btn = document.getElementById('btn-toggle-camera');
    const feed = document.getElementById('video-feed');
    const statusText = document.getElementById('face-status-text');
    
    if (isCameraOn) {
        try {
            cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
            feed.srcObject = cameraStream;
            feed.style.display = "block";
            btn.innerText = "إيقاف المراقبة";
            btn.style.backgroundColor = "#ef4444";
            statusText.innerText = "المراقبة تعمل...";
            statusText.style.color = "#10b981";
            
            startFrameCapture();
        } catch (err) {
            console.error("Error accessing camera:", err);
            alert("حدث خطأ أثناء الوصول للكاميرا.");
            isCameraOn = false;
        }
    } else {
        if (cameraStream) {
            cameraStream.getTracks().forEach(track => track.stop());
            cameraStream = null;
        }
        if (captureInterval) {
            clearInterval(captureInterval);
            captureInterval = null;
        }
        feed.srcObject = null;
        feed.style.display = "none";
        btn.innerText = "بدء المراقبة";
        btn.style.backgroundColor = "#10b981";
        statusText.innerText = "نظام المراقبة متوقف";
        statusText.style.color = "#64748b";
    }
}

function startFrameCapture() {
    const video = document.getElementById('video-feed');
    const canvas = document.getElementById('camera-canvas');
    const context = canvas.getContext('2d');
    
    captureInterval = setInterval(() => {
        if (!isCameraOn || video.videoWidth === 0) return;
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const frameData = canvas.toDataURL('image/jpeg', 0.5);
        
        fetch('/api/process_frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: frameData })
        })
        .then(res => res.json())
        .then(data => {
            if (data.recognized) {
                document.getElementById('face-status-text').innerText = "تم التعرف: " + data.member_name;
            }
        })
        .catch(err => console.error("Error sending frame:", err));
        
    }, 1000);
}
'''

import re
content = re.sub(r'let isCameraOn = false;.*?}$', new_js.strip(), content, flags=re.DOTALL)

with codecs.open('static/js/main.js', 'w', 'utf-8') as f:
    f.write(content)
