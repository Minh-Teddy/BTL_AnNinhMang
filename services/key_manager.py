import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeyManager:
    """NHOM QUAN LY KHOA - Tao, doc, liet ke va xoa cap khoa RSA."""
    DEFAULT_KEY_SIZE = 2048
    SIGNATURE_IMAGE_TYPES = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }

    def __init__(self, storage_dir="storage/keys"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def create_key(self, key_name, owner_name):
        """Tao cap khoa RSA 2048-bit va metadata cua chu so huu."""
        key_id = self._normalize_key_id(key_name)
        owner_name = (owner_name or "").strip()
        key_size = self.DEFAULT_KEY_SIZE

        if not key_id:
            raise ValueError("Tên khóa không được để trống.")
        if not owner_name:
            raise ValueError("Tên chủ sở hữu không được để trống.")

        key_dir = self._key_dir(key_id)
        if key_dir.exists():
            raise FileExistsError("Tên khóa đã tồn tại.")

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        public_key = private_key.public_key()
        key_dir.mkdir(parents=True)

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        (key_dir / "private_key.pem").write_bytes(private_pem)
        (key_dir / "public_key.pem").write_bytes(public_pem)

        metadata = {
            "key_id": key_id,
            "key_name": key_name.strip(),
            "owner_name": owner_name,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "algorithm": "RSA",
            "key_size": key_size,
            "status": "active",
            "private_key_path": str(key_dir / "private_key.pem"),
            "public_key_path": str(key_dir / "public_key.pem"),
        }
        self._write_json(key_dir / "metadata.json", metadata)
        return metadata

    def save_signature_image(self, key_id, image_file):
        """Luu anh chu ky hien thi; anh nay khong tham gia phep ky RSA."""
        if not image_file or not image_file.filename:
            return self.get_metadata(key_id)

        suffix = Path(image_file.filename).suffix.lower()
        if suffix not in self.SIGNATURE_IMAGE_TYPES:
            raise ValueError("Ảnh chữ ký chỉ hỗ trợ PNG, JPG hoặc JPEG.")

        image_bytes = image_file.read()
        if not image_bytes:
            raise ValueError("Ảnh chữ ký không được để trống.")

        key_dir = self._key_dir(key_id)
        if not key_dir.exists():
            raise FileNotFoundError("Không tìm thấy khóa.")

        image_path = key_dir / f"signature_image{suffix}"
        image_path.write_bytes(image_bytes)

        metadata_path = key_dir / "metadata.json"
        metadata = self._read_json(metadata_path)
        metadata["signature_image_path"] = str(image_path)
        metadata["signature_image_type"] = self.SIGNATURE_IMAGE_TYPES[suffix]
        self._write_json(metadata_path, metadata)
        return metadata

    def list_keys(self):
        """Tra ve metadata cua cac khoa dang luu."""
        keys = []
        for metadata_path in sorted(self.storage_dir.glob("*/metadata.json")):
            try:
                keys.append(self._read_json(metadata_path))
            except json.JSONDecodeError:
                continue
        return keys

    def load_private_key(self, key_id):
        """Nap khoa rieng de ky noi dung."""
        private_path = self._key_dir(key_id) / "private_key.pem"
        if not private_path.exists():
            raise FileNotFoundError("Không tìm thấy khóa riêng tư.")
        return serialization.load_pem_private_key(private_path.read_bytes(), password=None)

    def load_public_key(self, key_id):
        """Nap khoa cong khai de xac thuc chu ky."""
        public_path = self._key_dir(key_id) / "public_key.pem"
        if not public_path.exists():
            raise FileNotFoundError("Không tìm thấy khóa công khai.")
        return serialization.load_pem_public_key(public_path.read_bytes())

    def export_public_key(self, key_id):
        public_path = self._key_dir(key_id) / "public_key.pem"
        if not public_path.exists():
            raise FileNotFoundError("Không tìm thấy khóa công khai.")
        return public_path.read_text(encoding="utf-8")

    def export_private_key(self, key_id):
        private_path = self._key_dir(key_id) / "private_key.pem"
        if not private_path.exists():
            raise FileNotFoundError("Không tìm thấy khóa riêng tư.")
        return private_path.read_text(encoding="utf-8")

    def get_metadata(self, key_id):
        metadata_path = self._key_dir(key_id) / "metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError("Không tìm thấy thông tin khóa.")
        return self._read_json(metadata_path)

    def get_signature_image_path(self, key_id):
        metadata = self.get_metadata(key_id)
        image_path = metadata.get("signature_image_path")
        if not image_path:
            return None

        path = Path(image_path)
        if not path.exists():
            return None
        return path

    def delete_key(self, key_id):
        """Xoa thu muc khoa sau khi kiem tra duong dan nam trong kho luu."""
        normalized_key_id = self._normalize_key_id(key_id)
        if not normalized_key_id:
            raise ValueError("Mã khóa không hợp lệ.")

        key_dir = self._key_dir(key_id)
        if not key_dir.exists():
            raise FileNotFoundError("Không tìm thấy khóa cần xóa.")

        storage_root = self.storage_dir.resolve()
        resolved_key_dir = key_dir.resolve()
        if storage_root not in resolved_key_dir.parents:
            raise ValueError("Đường dẫn khóa không hợp lệ.")

        shutil.rmtree(key_dir)

    def _key_dir(self, key_id):
        return self.storage_dir / self._normalize_key_id(key_id)

    @staticmethod
    def _normalize_key_id(value):
        value = (value or "").strip()
        value = re.sub(r"\s+", "_", value)
        return re.sub(r"[^A-Za-z0-9_-]", "", value)

    @staticmethod
    def _read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
