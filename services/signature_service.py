import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from services.hash_service import HashService


class SignatureService:
    """NHOM CHU KY TEXT - Ky va xac thuc UTF-8 bang RSA PKCS#1 v1.5/SHA-256."""
    @staticmethod
    def sign_text(text, private_key):
        """Ky noi dung text va tra ve hash cung chu ky Base64."""
        signature = private_key.sign(
            text.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "hash": HashService.hash_text(text),
            "signature": SignatureService.encode_signature(signature),
            "algorithm": "RSA-SHA256",
        }

    @staticmethod
    def verify_text(text, signature_base64, public_key):
        """Xac thuc noi dung hien tai voi chu ky va khoa cong khai."""
        signature = SignatureService.decode_signature(signature_base64)
        try:
            public_key.verify(
                signature,
                text.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False

    @staticmethod
    def encode_signature(signature_bytes):
        """Ma hoa chu ky nhi phan sang Base64 de luu va trao doi."""
        return base64.b64encode(signature_bytes).decode("ascii")

    @staticmethod
    def decode_signature(signature_base64):
        """Kiem tra va giai ma chu ky Base64 sang du lieu nhi phan."""
        if not signature_base64 or not signature_base64.strip():
            raise ValueError("Chữ ký không được để trống.")
        try:
            return base64.b64decode(signature_base64.strip(), validate=True)
        except Exception as exc:
            raise ValueError("Chữ ký không đúng định dạng Base64.") from exc
