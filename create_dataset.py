import os
import pickle
import mediapipe as mp
import cv2

# إعداد MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

# المجلد الرئيسي للبيانات
DATA_DIR = './data'

# تحديد اللغة من المستخدم
language = input("Enter language (ar for Arabic, en for English): ").strip().lower()

if language not in ['ar', 'en']:
    print("Invalid language. Please enter 'ar' for Arabic or 'en' for English.")
    exit()

print(f"تم اختيار اللغة {'العربية' if language == 'ar' else 'الإنجليزية'}.")

data = []
labels = []

for dir_ in os.listdir(DATA_DIR):
    dir_index = int(dir_.split('_')[-1])  # استخراج الرقم من اسم المجلد (مثل 'ar_0' -> 0)
    for img_path in os.listdir(os.path.join(DATA_DIR, dir_)):
        data_aux = []
        x_ = []
        y_ = []

        # قراءة الصورة
        img = cv2.imread(os.path.join(DATA_DIR, dir_, img_path))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # استخراج معالم اليد
        results = hands.process(img_rgb)
        if results.multi_hand_landmarks:
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

            # إضافة البيانات مع التصنيف كرقم بسيط
            data.append(data_aux)
            labels.append(dir_index)

# حفظ البيانات في ملف pickle
with open('data.pickle', 'wb') as f:
    pickle.dump({'data': data, 'labels': labels, 'language': language}, f)

print(f"Dataset has been saved with language '{language}'.")
