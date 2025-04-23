import pickle
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# تحميل النموذج
model_dict = pickle.load(open('./model.p', 'rb'))
model = model_dict['model']

# إعداد MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.5)

# القواميس للحروف والأرقام والكلمات
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

# تحديد اللغة من المستخدم
language = input("هل تريد عرض الإشارات باللغة العربية أم الإنجليزية؟ (ar للغة العربية، en للغة الإنجليزية): ").strip().lower()

if language not in ['ar', 'en']:
    print("اختيار غير صحيح. يرجى إدخال 'ar' للغة العربية أو 'en' للغة الإنجليزية.")
    exit()

# اختيار القاموس بناءً على اللغة
labels_dict = labels_dict_ar if language == 'ar' else labels_dict_en
print(f"تم اختيار اللغة {'العربية' if language == 'ar' else 'الإنجليزية'}.")

# تحميل الخط المناسب
font_path = "arial.ttf"  # تأكد من وجود ملف الخط المناسب
font = ImageFont.truetype(font_path, 32)

# فتح كاميرا الويب
cap = cv2.VideoCapture(0)

# بدء التعرف على الإشارات
collected_text = ""  # النص المجمع
while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            data_aux = []
            x_ = []
            y_ = []

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

            prediction = model.predict([np.asarray(data_aux)])
            predicted_character = labels_dict.get(int(prediction[0]), "Unknown")

            # إعادة تشكيل النصوص العربية إذا كانت اللغة عربية
            if language == 'ar':
                reshaped_text = arabic_reshaper.reshape(predicted_character)
                predicted_character = get_display(reshaped_text)

            # تحويل الإطار إلى صورة PIL لرسم النصوص
            frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(frame_pil)
            draw.text((50, 50), predicted_character, font=font, fill=(0, 255, 0))

            # تحويل الصورة مرة أخرى إلى إطار OpenCV
            frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

    # عرض النص المجمع
    frame_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(frame_pil)
    reshaped_collected_text = arabic_reshaper.reshape(collected_text) if language == 'ar' else collected_text
    collected_text_display = get_display(reshaped_collected_text) if language == 'ar' else collected_text
    draw.text((10, 400), f"Collected Text: {collected_text_display}", font=font, fill=(255, 0, 0))
    frame = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)

    cv2.imshow('Sign Language Recognition', frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord(' '):  # إذا تم الضغط على المسطرة
        collected_text += predicted_character + " "
    elif key == ord('\r'):  # إذا تم الضغط على Enter
        break

cap.release()
cv2.destroyAllWindows()

print(f"Final Collected Text: {collected_text}")
