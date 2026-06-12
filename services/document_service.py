from pathlib import Path


class DocumentService:
    def __init__(self, storage_dir="storage/documents"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def read_text_file(self, file_storage):
        if not file_storage or not file_storage.filename:
            return ""
        if not file_storage.filename.lower().endswith(".txt"):
            raise ValueError("Chỉ hỗ trợ file .txt trong bản demo.")
        return file_storage.read().decode("utf-8-sig")

    def save_text_file(self, content, file_name):
        self.validate_text(content)
        safe_name = Path(file_name).name or "document.txt"
        if not safe_name.lower().endswith(".txt"):
            safe_name += ".txt"
        target = self.storage_dir / safe_name
        counter = 1
        while target.exists():
            target = self.storage_dir / f"{target.stem}_{counter}{target.suffix}"
            counter += 1
        target.write_text(content, encoding="utf-8")
        return str(target)

    @staticmethod
    def validate_text(content):
        if not content or not content.strip():
            raise ValueError("Văn bản không được để trống.")

    @staticmethod
    def normalize_text(content):
        return (content or "").replace("\r\n", "\n").replace("\r", "\n")
