"""
وحدة مساعدة للتعامل مع توكنات JWT
"""

# استخدام مكتبة pyjwt المثبتة
try:
    import jwt as pyjwt
except ImportError:
    # إذا فشل الاستيراد، نحاول استيراد PyJWT
    try:
        import PyJWT as pyjwt
    except ImportError:
        # إذا فشل الاستيراد مرة أخرى، نستخدم تنفيذ بسيط
        print("Warning: JWT libraries not found. Using simple implementation.")

        class SimpleJWT:
            @staticmethod
            def encode(payload, key, algorithm=None):
                import json
                import base64
                import hashlib

                # تشفير البيانات
                header = {"alg": algorithm or "HS256", "typ": "JWT"}
                header_json = json.dumps(header).encode()
                header_b64 = base64.urlsafe_b64encode(header_json).decode().rstrip("=")

                payload_json = json.dumps(payload).encode()
                payload_b64 = base64.urlsafe_b64encode(payload_json).decode().rstrip("=")

                # توقيع البيانات
                signature_input = f"{header_b64}.{payload_b64}".encode()
                signature = hashlib.sha256(signature_input + key.encode()).digest()
                signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")

                # إنشاء التوكن
                return f"{header_b64}.{payload_b64}.{signature_b64}"

            @staticmethod
            def decode(token, key, algorithms=None):
                import json
                import base64

                # فك تشفير التوكن
                try:
                    header_b64, payload_b64, signature_b64 = token.split(".")

                    # فك تشفير البيانات
                    header_json = base64.urlsafe_b64decode(header_b64 + "==").decode()
                    header = json.loads(header_json)

                    payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode()
                    payload = json.loads(payload_json)

                    return payload
                except Exception as e:
                    raise InvalidTokenError(str(e))

        class InvalidTokenError(Exception):
            pass

        pyjwt = SimpleJWT()
        pyjwt.InvalidTokenError = InvalidTokenError

def encode(payload, key, algorithm="HS256"):
    """
    تشفير البيانات وإنشاء توكن JWT

    المعلمات:
        payload (dict): البيانات المراد تشفيرها
        key (str): المفتاح السري
        algorithm (str): خوارزمية التشفير

    العائد:
        str: توكن JWT
    """
    return pyjwt.encode(payload, key, algorithm=algorithm)

def decode(token, key, algorithms=None):
    """
    فك تشفير توكن JWT

    المعلمات:
        token (str): توكن JWT
        key (str): المفتاح السري
        algorithms (list): قائمة بخوارزميات التشفير المسموح بها

    العائد:
        dict: البيانات المشفرة
    """
    if algorithms is None:
        algorithms = ["HS256"]
    return pyjwt.decode(token, key, algorithms=algorithms)

# تصدير الاستثناءات
try:
    InvalidTokenError = pyjwt.InvalidTokenError
except AttributeError:
    class InvalidTokenError(Exception):
        pass
