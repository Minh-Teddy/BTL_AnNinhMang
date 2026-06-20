import hashlib
from pathlib import Path


class HashService:
    """NHOM BAM DU LIEU - Tinh va so sanh SHA-256 cua text/tep."""
    @staticmethod
    def hash_text(text):
        normalized = text if text is not None else ""
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_file(file_path):
        data = Path(file_path).read_bytes()
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def compare_hash(hash1, hash2):
        return (hash1 or "").strip().lower() == (hash2 or "").strip().lower()
