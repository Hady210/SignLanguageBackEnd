import sqlite3
from flask import Flask, request, jsonify,render_template
import bcrypt
from flask_cors import CORS 
import cv2
import pickle
import mediapipe as mp
import jwt
import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 

 
# Connect to SQLite database (or create if it doesn't exist)
conn = sqlite3.connect("sign_language.db", check_same_thread=False)
cursor = conn.cursor()

#cursor.execute('DROP TABLE Users;')
# Create Users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_number TEXT NOT NULL UNIQUE,
    address TEXT,
    user_type TEXT ,
    password TEXT NOT NULL
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

conn.commit()
@app.route('/')
def index():
    return render_template('test_endpoints.html')
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cursor.execute("SELECT id FROM Users WHERE phone_number = ?", (data['phone_number'],))
    existing_user = cursor.fetchone()

    if existing_user:
        return jsonify({"error": "Phone number already registered"}), 400

    try:
        cursor.execute("INSERT INTO Users (name, phone_number, address, user_type, password) VALUES (?, ?, ?, ?, ?)", 
                       (data['name'], data['phone_number'], data['address'], data['user_type'], hashed_password))
        conn.commit()

        # جلب معرف المستخدم الجديد
        user_id = cursor.lastrowid  

        # إنشاء التوكن مع إضافة id, name, user_type
        token = jwt.encode(
            {
                "user_id": user_id,
                "name": data['name'],
                "user_type": data['user_type'],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
            },
            SECRET_KEY,
            algorithm="HS256"
        )

        return jsonify({
            "message": "User registered successfully!",
            "token": token
        }), 201

    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500



SECRET_KEY = "your_secret_key"  # استخدم مفتاحًا سريًا آمنًا

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
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=12)
            },
            SECRET_KEY,
            algorithm="HS256"
        )
        return jsonify({
            "message": "Login successful!",
            "token": token
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401

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

if __name__ == '__main__':
    app.run(debug=True)
