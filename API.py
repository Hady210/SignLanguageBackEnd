import sqlite3
from flask import Flask, request, jsonify, render_template, url_for, send_from_directory
import bcrypt
from flask_cors import CORS
import cv2
import pickle
import mediapipe as mp
import jwt_helper as jwt  # استخدام وحدة مساعدة للتعامل مع JWT
import datetime
import random
from twilio.rest import Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import numpy as np
from flask_socketio import SocketIO, emit
import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# إعداد Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# إعدادات تحميل الملفات
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'videos')
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mov', 'avi'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 ميجابايت كحد أقصى

# التأكد من وجود مجلد التحميل
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Connect to SQLite database (or create if it doesn't exist)
conn = sqlite3.connect("sign_language.db", check_same_thread=False)
cursor = conn.cursor()

#cursor.execute("DROP TABLE IF EXISTS Users")
# Create Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL UNIQUE,
    address TEXT,
    user_type TEXT,
    password TEXT NOT NULL,
    otp TEXT
);
''')


# Create SignVideos table
cursor.execute('''
CREATE TABLE IF NOT EXISTS SignVideos (
    character_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_name TEXT NOT NULL,
    character_video TEXT NOT NULL
);
''')

# # Create SignImages table
# cursor.execute('''
# CREATE TABLE IF NOT EXISTS SignImages (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT NOT NULL,
#     image BLOB NOT NULL
# );
# ''')

conn.commit()

# تحميل النموذج
try:
    model_dict = pickle.load(open('./model.p', 'rb'))
    model = model_dict['model']
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {str(e)}")
    model = None

# إعداد Mediapipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.5, min_tracking_confidence=0.5)

labels_dict_ar = {
    0: 'أ', 1: 'ب', 2: 'ت', 3: 'ث', 4: 'ج', 5: 'ح', 6: 'خ', 7: 'د', 8: 'ذ', 9: 'ر',
    10: 'ز', 11: 'س', 12: 'ش', 13: 'ص', 14: 'ض', 15: 'ط', 16: 'ظ', 17: 'ع', 18: 'غ',
    19: 'ف', 20: 'ق', 21: 'ك', 22: 'ل', 23: 'م', 24: 'ن', 25: 'ه', 26: 'و', 27: 'ي',
    28: 'ة', 29: 'ال', 30: 'أ', 31: 'لا', 32: 'اضحكني', 33: 'اراك لاحقا', 34: 'حقا احبك', 35: 'احبك', 36: 'لست متاكد',
    37: 'مرحبا ', 38: 'انا اراقبك', 39: 'هذا رهيب', 40: 'اقتبايس', 41: 'سؤال', 42: 'ممتاز', 43: 'انت ', 44: ' موافق', 45: "اتمني لك حياه سعيده",
    46: ' جيد', 47: 'لست متاكد', 48: ' شكرا', 49: ' احمر ', 50: 'ابيض', 51: 'اسود', 52: 'اصفر', 53: 'اخضر', 54: 'ازرق', 55: '1', 56: '2', 57: '3',
    58: '4', 59: '5', 60: '6', 61: '7', 62: '8', 63: '9', 64: '0'
}

labels_dict_en = {
    0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'E', 5: 'F', 6: 'G', 7: 'H', 8: 'I', 9: 'J',
    10: 'K', 11: 'L', 12: 'M', 13: 'N', 14: 'O', 15: 'P', 16: 'Q', 17: 'R', 18: 'S',
    19: 'T', 20: 'U', 21: 'V', 22: 'W', 23: 'X', 24: 'Y', 25: 'Z',
    26: '0', 27: '1', 28: '2', 29: '3', 30: '4', 31: '5', 32: '6', 33: '7', 34: '8',
    35: '9'
}
@app.route('/')
def index():
    return render_template('test_endpoints.html')
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # التحقق من وجود جميع الحقول المطلوبة
    if not all(key in data for key in ("name", "phone_number", "address", "user_type", "password")):
        return jsonify({"error": "Missing required fields"}), 400

    # تشفير كلمة المرور
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # التحقق من وجود المستخدم مسبقًا
    cursor.execute("SELECT id FROM Users WHERE phone_number = ?", (data['phone_number'],))
    existing_user = cursor.fetchone()

    if existing_user:
        return jsonify({"error": "Phone number already registered"}), 400

    try:
        # إدخال المستخدم الجديد في قاعدة البيانات
        cursor.execute(
            "INSERT INTO Users (name, phone_number, address, user_type, password) VALUES (?, ?, ?, ?, ?)",
            (data['name'], data['phone_number'], data['address'], data['user_type'], hashed_password)
        )
        conn.commit()

        # إنشاء توكن JWT
        user_id = cursor.lastrowid
        token = jwt.encode(
            {
                "user_id": user_id,
                "name": data['name'],
                "user_type": data['user_type'],
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)
            },
            SECRET_KEY,
            algorithm="HS256"
        )

        # إرسال رسالة ترحيب للمستخدم الجديد
        welcome_message = f"مرحبًا {data['name']}! شكرًا لتسجيلك في تطبيق لغة الإشارة. نتمنى لك تجربة ممتعة ومفيدة."
        send_sms(data['phone_number'], welcome_message)

        return jsonify({
            "message": "User registered successfully!",
            "token": token
        }), 201

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500


SECRET_KEY = "your_secret_key"  # استخدم مفتاحًا سريًا آمنًا

# بيانات اعتماد Twilio لإرسال الرسائل النصية
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"  # قم بتغييرها إلى SID الخاص بك
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"  # قم بتغييرها إلى رمز المصادقة الخاص بك
TWILIO_PHONE_NUMBER = "+1234567890"  # قم بتغييرها إلى رقم Twilio الخاص بك


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    cursor.execute("SELECT id, name, user_type, password FROM Users WHERE phone_number = ?", (data['phone_number'],))
    user = cursor.fetchone()

    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user[3].encode('utf-8')):
        # إنشاء التوكن مع إضافة id, name, user_type
        token = jwt.encode(
            {
                "user_id": user[0],
                "name": user[1],
                "user_type": user[2],
                "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=12)
            },
            SECRET_KEY,
            algorithm="HS256"
        )
        return jsonify({
            "message": "Login successful!",
            "token": token
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    phone_number = data.get('phone_number')

    if not phone_number:
        return jsonify({"error": "Phone number is required"}), 400

    # التحقق من وجود المستخدم
    cursor.execute("SELECT id FROM Users WHERE phone_number = ?", (phone_number,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "No account found with this phone number"}), 404

    # إنشاء رمز OTP (6 أرقام)
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])

    # تخزين رمز OTP في قاعدة البيانات
    cursor.execute("UPDATE Users SET otp = ? WHERE phone_number = ?", (otp, phone_number))
    conn.commit()

    # إرسال رمز OTP عبر رسالة نصية باستخدام الوظيفة المساعدة
    message_text = f"رمز التحقق الخاص بك لاستعادة كلمة المرور هو: {otp}"
    sms_result = send_sms(phone_number, message_text)

    # طباعة رمز OTP في السجل للتتبع
    print(f"OTP for {phone_number}: {otp}")

    if sms_result["success"]:
        return jsonify({
            "message": "تم إرسال رمز التحقق بنجاح إلى رقم هاتفك",
            "phone_number": phone_number
        }), 200
    else:
        # في حالة فشل إرسال الرسالة، نعيد رسالة خطأ مع رمز OTP في وضع التصحيح
        return jsonify({
            "message": "تم إنشاء رمز التحقق ولكن لم يتم إرساله عبر رسالة نصية. يرجى الاتصال بالدعم الفني.",
            "phone_number": phone_number,
            "debug_otp": otp if app.debug else None,  # إرجاع OTP فقط في وضع التصحيح
            "error": sms_result["error"] if app.debug else None  # إرجاع تفاصيل الخطأ فقط في وضع التصحيح
        }), 200

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    phone_number = data.get('phone_number')
    otp = data.get('otp')
    new_password = data.get('new_password')

    if not all([phone_number, otp, new_password]):
        return jsonify({"error": "Phone number, OTP, and new password are required"}), 400

    # التحقق من صحة رمز OTP
    cursor.execute("SELECT id, otp FROM Users WHERE phone_number = ?", (phone_number,))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "No account found with this phone number"}), 404

    if not user[1] or user[1] != otp:
        return jsonify({"error": "Invalid OTP"}), 400

    # تشفير كلمة المرور الجديدة
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    # تحديث كلمة المرور وإزالة رمز OTP
    cursor.execute("UPDATE Users SET password = ?, otp = NULL WHERE phone_number = ?", (hashed_password, phone_number))
    conn.commit()

    return jsonify({"message": "Password reset successfully"}), 200

def verify_token(token):
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded
    except jwt.InvalidTokenError:
        return None

@app.route('/protected', methods=['GET'])
def protected_route():
    token = request.headers.get("Authorization")  # قراءة التوكن من الهيدر

    if not token:
        return jsonify({"error": "Token is missing"}), 403

    decoded = verify_token(token)
    if not decoded:
        return jsonify({"error": "Invalid or expired token"}), 403

    # جلب بيانات المستخدم من قاعدة البيانات
    cursor.execute("SELECT name, user_type FROM Users WHERE id = ?", (decoded["user_id"],))
    user = cursor.fetchone()

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "message": "Access granted",
        "user_id": decoded["user_id"],
        "name": user[0],  # اسم المستخدم
        "user_type": user[1]  # نوع المستخدم
    })
#education
@app.route('/get_videos', methods=['GET'])
def get_videos():
    cursor.execute("SELECT * FROM SignVideos")
    videos = cursor.fetchall()
    return jsonify({"videos": videos}), 200


from googletrans import Translator
translator = Translator()

@app.route('/get_sign_images', methods=['POST'])
def get_sign_images():
    data = request.get_json()
    text = data.get("text", "")
    language = data.get("language", None)  # يجب على المستخدم تحديد اللغة

    print(f"Received text: {text}, language: {language}")  # تتبع المدخلات

    # التحقق مما إذا كانت اللغة محددة
    if not language:
        return jsonify({"error": "Please specify the language (ar for Arabic, en for English)"}), 400

    # التحقق من اللغة المدخلة
    if language not in ["ar", "en"]:
        return jsonify({"error": "Only Arabic (ar) and English (en) are supported"}), 400

    try:
        # إذا كانت اللغة عربية، لا حاجة للترجمة
        if language == "ar":
            translated_text = text
        elif language == "en":
            # إذا كانت اللغة إنجليزية، قم بالترجمة إلى الإنجليزية (للتأكد من التوافق)
            translated_text = translator.translate(text, src=language, dest='en').text

        print(f"Translated text: {translated_text}")  # تتبع النص المترجم
    except Exception as e:
        print(f"Translation error: {str(e)}")  # تتبع الأخطاء
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

    # تحويل النص إلى أحرف كبيرة لضمان التوافق مع قاعدة البيانات
    translated_text = translated_text.upper()
    print(f"Uppercase translated text: {translated_text}")  # تتبع النص بعد التحويل إلى أحرف كبيرة

    # تحقق إذا كانت الكلمة بأكملها موجودة في قاعدة البيانات
    cursor.execute("SELECT character_video FROM SignVideos WHERE UPPER(character_name) = ?", (translated_text,))
    word_video = cursor.fetchone()

    if word_video:
        print(f"Word video found: {word_video[0]}")  # تتبع الفيديو إذا تم العثور عليه
        # إذا كانت الكلمة موجودة، أعد الفيديو الخاص بها
        return jsonify({"sign_videos": [{"word": translated_text, "video": word_video[0]}]}), 200

    # إذا لم تكن الكلمة موجودة، أعد فيديو لكل حرف
    result = []
    for char in translated_text:
        cursor.execute("SELECT character_video FROM SignVideos WHERE UPPER(character_name) = ?", (char,))
        video = cursor.fetchone()
        if video:
            print(f"Character video found for {char}: {video[0]}")  # تتبع الفيديو لكل حرف
            result.append({"character": char, "video": video[0]})
        else:
            print(f"No video found for character: {char}")  # تتبع الحروف التي لم يتم العثور على فيديو لها

    return jsonify({"sign_videos": result}), 200

@app.route('/add_video', methods=['POST'])
def add_video():
    data = request.get_json()
    print("Received data:", data)

    character_name = data.get("character_name")
    character_video = data.get("character_video")

    if not character_name or not character_video:
        return jsonify({"error": "Missing character_name or character_video"}), 400

    try:
        cursor.execute("INSERT INTO SignVideos (character_name, character_video) VALUES (?, ?)",
                       (character_name, character_video))
        conn.commit()
        return jsonify({"message": "Video added successfully!"}), 201
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
#not useed for best version
@app.route('/upload_sign_image', methods=['POST'])
def upload_sign_image():
    data = request.get_json()
    name = data.get("name")
    image_data = data.get("image")

    if not name or not image_data:
        return jsonify({"error": "Name and image are required"}), 400

    try:
        # تحويل الصورة من Base64 إلى بايت
        image_bytes = base64.b64decode(image_data)

        # تخزين الصورة في قاعدة البيانات
        cursor.execute("INSERT INTO SignImages (name, image) VALUES (?, ?)", (name, image_bytes))
        conn.commit()
        return jsonify({"message": "Image uploaded successfully!"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to upload image: {str(e)}"}), 500

@app.route('/detect_sign', methods=['POST'])
def detect_sign():
    data = request.get_json()
    image_data = data.get("image")  # الصورة المرسلة من المستخدم (Base64)
    language = data.get("language")  # اللغة المحددة

    if not image_data or not language:
        return jsonify({"error": "Image and language are required"}), 400

    # فك ترميز الصورة من Base64
    try:
        image_bytes = base64.b64decode(image_data)
        np_image = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(np_image, cv2.IMREAD_COLOR)
    except Exception as e:
        return jsonify({"error": f"Failed to decode image: {str(e)}"}), 400

    # تحليل الصورة باستخدام Mediapipe
    try:
        # استخدم Mediapipe لاستخراج الحركات
        mp_hands = mp.solutions.hands
        hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5)
        results = hands.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

        if not results.multi_hand_landmarks:
            return jsonify({"error": "No hand detected in the image"}), 400

        # استخراج النقاط (landmarks) من اليد
        hand_landmarks = results.multi_hand_landmarks[0]
        data_aux = []
        x_ = []
        y_ = []

        for lm in hand_landmarks.landmark:
            x_.append(lm.x)
            y_.append(lm.y)

        for lm in hand_landmarks.landmark:
            data_aux.append(lm.x - min(x_))
            data_aux.append(lm.y - min(y_))

        # التحقق من تحميل النموذج بنجاح
        if model is None:
            return jsonify({"error": "Model not loaded. Please check server logs."}), 500

        try:
            # استخدام النموذج للتنبؤ
            prediction = model.predict([np.asarray(data_aux)])
            print(f"Prediction result: {prediction}")

            # التحقق من صحة اللغة
            if language not in ["ar", "en"]:
                language = "en"  # استخدام الإنجليزية كلغة افتراضية

            if language == "ar":
                predicted_character = labels_dict_ar.get(int(prediction[0]), "Unknown")
            else:  # language == "en"
                predicted_character = labels_dict_en.get(int(prediction[0]), "Unknown")

            print(f"Predicted character: {predicted_character}")
        except Exception as e:
            print(f"Error during prediction: {str(e)}")
            return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

        # البحث عن فيديو للحرف أو الكلمة المتوقعة
        cursor.execute("SELECT character_video FROM SignVideos WHERE character_name = ?", (predicted_character,))
        video_match = cursor.fetchone()

        video_url = None
        if video_match:
            video_url = video_match[0]

        return jsonify({
            "gesture": predicted_character,
            "video": video_url,
            "confidence": float(np.max(prediction[1])) if len(prediction) > 1 else 1.0
        }), 200

    except Exception as e:
        print(f"Error in detect_sign: {str(e)}")
        return jsonify({"error": f"Failed to process image: {str(e)}"}), 500



def send_sms(phone_number, message):
    """
    وظيفة مساعدة لإرسال رسائل نصية باستخدام Twilio

    المعلمات:
        phone_number (str): رقم الهاتف المستلم
        message (str): نص الرسالة

    العائد:
        dict: نتيجة إرسال الرسالة (نجاح أو فشل)
    """
    try:
        # تنسيق رقم الهاتف (إضافة رمز البلد إذا لم يكن موجودًا)
        formatted_phone = phone_number
        if not phone_number.startswith('+'):
            # إضافة رمز البلد (مثال: +20 لمصر)
            formatted_phone = "+20" + phone_number.lstrip('0')

        # إنشاء عميل Twilio
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # إرسال الرسالة
        message_obj = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=formatted_phone
        )

        # طباعة معرف الرسالة للتتبع
        print(f"Message SID: {message_obj.sid}")

        return {
            "success": True,
            "message_sid": message_obj.sid
        }
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def compare_images(image1, image2):
    try:
        # التحقق من أن الصور صالحة
        if image1 is None or image2 is None:
            print("Error: One of the images is None")
            return 0.0

        # تحويل الصور إلى تدرج الرمادي
        gray1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(image2, cv2.COLOR_BGR2GRAY)

        # تغيير حجم الصور لتكون بنفس الأبعاد
        gray1 = cv2.resize(gray1, (100, 100))
        gray2 = cv2.resize(gray2, (100, 100))

        # حساب الفرق بين الصور
        difference = cv2.absdiff(gray1, gray2)
        similarity = 1 - (np.sum(difference) / (100 * 100 * 255))

        return float(similarity)  # التأكد من أن القيمة المرجعة هي float
    except Exception as e:
        print(f"Error in compare_images: {str(e)}")
        return 0.0  # إرجاع قيمة افتراضية في حالة حدوث خطأ

def allowed_file(filename):
    """التحقق من أن امتداد الملف مسموح به"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_unique_filename(filename):
    """إنشاء اسم فريد للملف باستخدام UUID"""
    # الحصول على الامتداد الأصلي للملف
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    # إنشاء اسم فريد باستخدام UUID
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    return unique_filename

# متغير لتتبع حالة النموذج
model_running = True

@socketio.on('toggle_model')
def toggle_model(data):
    global model_running
    model_running = data.get("running", True)
    status = "running" if model_running else "stopped"
    print(f"Model is now {status}")
    emit('model_status', {'status': status})

# استقبال إطارات الفيديو من العميل
@socketio.on('video_frame')
def handle_video_frame(data):
    global model_running
    if not model_running:
        emit('error', {'message': 'Model is stopped'})
        return

    try:
        # استلام البيانات (الإطار واللغة)
        # Check if data is bytes (direct blob) or dictionary
        if isinstance(data, bytes):
            frame_data = data
            language = "en"  # Default language if sent as blob
        else:
            # If it's a dictionary with frame and language
            frame_data = data.get("frame")
            language = data.get("language", "en")  # اللغة الافتراضية هي الإنجليزية

        if not frame_data:
            emit('error', {'message': 'Frame is required'})
            return

        # تحويل البيانات إلى صورة
        np_arr = np.frombuffer(frame_data, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # معالجة الصورة باستخدام Mediapipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(frame_rgb)

        recognized_text = ""

        if results.multi_hand_landmarks:
            data_aux = []
            x_, y_ = [], []

            for hand_landmarks in results.multi_hand_landmarks:
                for i in range(len(hand_landmarks.landmark)):
                    x = hand_landmarks.landmark[i].x
                    y = hand_landmarks.landmark[i].y
                    x_.append(x)
                    y_.append(y)

                for i in range(len(hand_landmarks.landmark)):
                    x = hand_landmarks.landmark[i].x
                    y = hand_landmarks.landmark[i].y
                    data_aux.append(x - min(x_))
                    data_aux.append(y - min(y_))

            # التنبؤ بالإشارة باستخدام النموذج
            prediction = model.predict([np.asarray(data_aux)])
            if language == "ar":
                recognized_text = labels_dict_ar.get(int(prediction[0]), "Unknown")
            elif language == "en":
                recognized_text = labels_dict_en.get(int(prediction[0]), "Unknown")
            else:
                emit('error', {'message': 'Unsupported language'})
                return

        # إرسال النص المعترف به إلى العميل
        emit('recognized_text', {'text': recognized_text})

    except Exception as e:
        print(f"Error processing frame: {str(e)}")
        emit('error', {'message': 'Failed to process frame'})

@app.route('/upload_video', methods=['POST'])
def upload_video():
    """وظيفة لرفع ملف فيديو وتخزينه في المجلد المحدد"""
    # التحقق من وجود ملف في الطلب
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files['video']
    character_name = request.form.get('character_name', '')

    # التحقق من أن اسم الحرف أو الكلمة موجود
    if not character_name:
        return jsonify({"error": "Character name is required"}), 400

    # التحقق من أن الملف موجود وله اسم
    if video_file.filename == '':
        return jsonify({"error": "No video file selected"}), 400

    # التحقق من أن امتداد الملف مسموح به
    if not allowed_file(video_file.filename):
        return jsonify({"error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    try:
        # إنشاء اسم فريد للملف
        filename = secure_filename(video_file.filename)
        unique_filename = get_unique_filename(filename)

        # حفظ الملف في المجلد المحدد
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        video_file.save(file_path)

        # إنشاء رابط مباشر للفيديو
        video_url = url_for('static', filename=f'uploads/videos/{unique_filename}', _external=True)

        # تخزين معلومات الفيديو في قاعدة البيانات
        cursor.execute("INSERT INTO SignVideos (character_name, character_video) VALUES (?, ?)",
                      (character_name, video_url))
        conn.commit()

        return jsonify({
            "message": "Video uploaded successfully",
            "character_name": character_name,
            "video_url": video_url,
            "file_size": os.path.getsize(file_path)
        }), 201

    except Exception as e:
        return jsonify({"error": f"Failed to upload video: {str(e)}"}), 500

@app.route('/static/uploads/videos/<filename>')
def serve_video(filename):
    """وظيفة لتقديم ملفات الفيديو المخزنة"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# مثال على إنشاء التوكن (تم تعليقه لتجنب التنفيذ في كل مرة)
# token = pyjwt.encode(
#     {
#         "user_id": 1,
#         "name": "John Doe",
#         "user_type": "user",
#         "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
#     },
#     SECRET_KEY,
#     algorithm="HS256"
# )
#
# print(token)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
