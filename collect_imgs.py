import os
import cv2

# إعداد المجلد الرئيسي للبيانات
DATA_DIR = './data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# عدد الفئات: 66 للعربي (حروف، كلمات، وأرقام) + 37 للإنجليزي (حروف وأرقام) + 2 لإشارات اليد
number_of_classes_ar = 66  # عدد الفئات للعربي
number_of_classes_en = 37  # عدد الفئات للإنجليزي
number_of_hand_signs = 2   # إشارات اليد (اليمنى واليسرى)
dataset_size = 100         # عدد الصور لكل فئة

# فتح كاميرا الويب
cap = cv2.VideoCapture(0)

# جمع البيانات للحروف والكلمات والأرقام العربية
for j in range(number_of_classes_ar + number_of_hand_signs):
    # إنشاء مجلد لكل فئة إذا لم يكن موجودًا
    if not os.path.exists(os.path.join(DATA_DIR, f'ar_{j}')):
        os.makedirs(os.path.join(DATA_DIR, f'ar_{j}'))

    # تحديد اسم الفئة
    if j == number_of_classes_ar:
        class_name = "Right Hand (Arabic)"
    elif j == number_of_classes_ar + 1:
        class_name = "Left Hand (English)"
    else:
        class_name = f"Arabic Class {j}"

    print(f'Collecting data for {class_name}')

    # انتظار المستخدم للضغط على "Q" لبدء جمع الصور
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame. Exiting...")
            break

        cv2.putText(frame, f'Ready to collect {class_name}? Press "Q" to start!', (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('frame', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # جمع الصور للفئة الحالية
    counter = 0
    while counter < dataset_size:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame. Exiting...")
            break

        cv2.imshow('frame', frame)
        cv2.imwrite(os.path.join(DATA_DIR, f'ar_{j}', f'{counter}.jpg'), frame)
        counter += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):  # السماح بالخروج أثناء جمع الصور
            print("Exiting early...")
            break

# جمع البيانات للحروف والأرقام الإنجليزية
for j in range(number_of_classes_en):
    # إنشاء مجلد لكل فئة إذا لم يكن موجودًا
    if not os.path.exists(os.path.join(DATA_DIR, f'en_{j}')):
        os.makedirs(os.path.join(DATA_DIR, f'en_{j}'))

    # تحديد اسم الفئة
    class_name = f"English Class {j}"

    print(f'Collecting data for {class_name}')

    # انتظار المستخدم للضغط على "Q" لبدء جمع الصور
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame. Exiting...")
            break

        cv2.putText(frame, f'Ready to collect {class_name}? Press "Q" to start!', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('frame', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # جمع الصور للفئة الحالية
    counter = 0
    while counter < dataset_size:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame. Exiting...")
            break

        cv2.imshow('frame', frame)
        cv2.imwrite(os.path.join(DATA_DIR, f'en_{j}', f'{counter}.jpg'), frame)
        counter += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):  # السماح بالخروج أثناء جمع الصور
            print("Exiting early...")
            break

cap.release()
cv2.destroyAllWindows()
