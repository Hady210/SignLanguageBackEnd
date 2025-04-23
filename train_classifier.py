import pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# تحميل البيانات من ملف pickle
data_dict = pickle.load(open('./data.pickle', 'rb'))

# تصفية البيانات غير المتسقة
valid_data = []
valid_labels = []

for i, sample in enumerate(data_dict['data']):
    if len(sample) == 42:  # عدد معالم اليد (21 نقطة × 2 إحداثيات)
        valid_data.append(sample)
        valid_labels.append(data_dict['labels'][i])

data = np.asarray(valid_data)

# استخدام التصنيفات مباشرة
simple_labels = valid_labels

# تقسيم البيانات إلى تدريب واختبار
x_train, x_test, y_train, y_test = train_test_split(data, simple_labels, test_size=0.2, shuffle=True, stratify=simple_labels)

# إنشاء نموذج Random Forest
model = RandomForestClassifier(n_estimators=100, random_state=42)

# تدريب النموذج
model.fit(x_train, y_train)

# التنبؤ بالاختبار
y_predict = model.predict(x_test)

# حساب الدقة
score = accuracy_score(y_predict, y_test)
print('{}% of samples were classified correctly!'.format(score * 100))

# عرض تقرير التصنيف
print("\nClassification Report:")
print(classification_report(y_test, y_predict))

# حفظ النموذج في ملف pickle
model_file = 'model.p'
with open(model_file, 'wb') as f:
    pickle.dump({'model': model}, f)

print(f"\nModel has been saved to {model_file}")
