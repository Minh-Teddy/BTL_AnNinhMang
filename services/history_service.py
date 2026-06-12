import json
from pathlib import Path


class HistoryService:
    def __init__(self, storage_dir="storage/histories"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sign_history_path = self.storage_dir / "sign_history.json"
        self.verify_history_path = self.storage_dir / "verify_history.json"

    def save_sign_history(self, data):
        records = self.get_sign_history()
        records.insert(0, data)
        self._write_records(self.sign_history_path, records)

    def save_verify_history(self, data):
        records = self.get_verify_history()
        records.insert(0, data)
        self._write_records(self.verify_history_path, records)

    def get_sign_history(self):
        return self._read_records(self.sign_history_path)

    def get_verify_history(self):
        return self._read_records(self.verify_history_path)

    def delete_records_for_key(self, key_id):
        normalized_key_id = (key_id or "").strip()
        if not normalized_key_id:
            return {"sign": 0, "verify": 0}

        sign_records = self.get_sign_history()
        verify_records = self.get_verify_history()
        kept_sign_records = [
            record for record in sign_records if record.get("key_id") != normalized_key_id
        ]
        kept_verify_records = [
            record for record in verify_records if record.get("key_id") != normalized_key_id
        ]

        self._write_records(self.sign_history_path, kept_sign_records)
        self._write_records(self.verify_history_path, kept_verify_records)
        return {
            "sign": len(sign_records) - len(kept_sign_records),
            "verify": len(verify_records) - len(kept_verify_records),
        }

    @staticmethod
    def _read_records(path):
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _write_records(path, records):
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
