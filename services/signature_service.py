import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from services.hash_service import HashService


class SignatureService:
    @staticmethod
    def sign_text(text, private_key):
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
        return base64.b64encode(signature_bytes).decode("ascii")

    @staticmethod
    def decode_signature(signature_base64):
        if not signature_base64 or not signature_base64.strip():
            raise ValueError("Chữ ký không được để trống.")
        try:
            return base64.b64decode(signature_base64.strip(), validate=True)
        except Exception as exc:
            raise ValueError("Chữ ký không đúng định dạng Base64.") from exc
