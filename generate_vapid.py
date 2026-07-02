"""
أداة توليد مفاتيح VAPID (تشغيل مرة واحدة فقط)
python generate_vapid.py
"""
from py_vapid import Vapid

def main():
    vapid = Vapid()
    vapid.generate_keys()
    private_key = vapid.private_pem().decode()
    public_key = vapid.public_key.public_bytes(
        encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.PEM,
        format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["PublicFormat"]).PublicFormat.SubjectPublicKeyInfo,
    ).decode()

    print("=== أضف هذه القيم إلى متغيرات البيئة في Railway ===\n")
    print(f"VAPID_PRIVATE_KEY=\n{private_key}")
    print(f"VAPID_PUBLIC_KEY=\n{public_key}")

if __name__ == "__main__":
    main()
