import base64
import html
import io
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

from services.document_service import DocumentService
from services.hash_service import HashService
from services.history_service import HistoryService
from services.key_manager import KeyManager
from services.pdf_signature_service import PdfSignatureService
from services.signature_service import SignatureService


app = Flask(__name__)
app.config["SECRET_KEY"] = "rsa-digital-signature-demo"

key_manager = KeyManager()
document_service = DocumentService()
history_service = HistoryService()
signature_dir = Path("storage/signatures")
signature_dir.mkdir(parents=True, exist_ok=True)
signed_document_dir = Path("storage/signed_documents")
signed_document_dir.mkdir(parents=True, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html", key_count=len(key_manager.list_keys()))


@app.route("/keys", methods=["GET", "POST"])
def keys():
    public_key = None
    selected_key = request.args.get("view")

    if request.method == "POST":
        try:
            metadata = key_manager.create_key(
                request.form.get("key_name"),
                request.form.get("owner_name"),
            )
            key_manager.save_signature_image(metadata["key_id"], request.files.get("signature_image"))
            flash(f"Tạo khóa {metadata['key_id']} thành công.", "success")
            return redirect(url_for("keys"))
        except Exception as exc:
            flash(str(exc), "error")

    if selected_key:
        try:
            public_key = key_manager.export_public_key(selected_key)
        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "keys.html",
        keys=key_manager.list_keys(),
        public_key=public_key,
        selected_key=selected_key,
    )


@app.post("/keys/<key_id>/delete")
def delete_key(key_id):
    try:
        key_manager.delete_key(key_id)
        deleted_history = history_service.delete_records_for_key(key_id)
        flash(
            f"Đã xóa khóa {key_id} khỏi dữ liệu hệ thống "
            f"và dọn {deleted_history['sign']} lịch sử ký, "
            f"{deleted_history['verify']} lịch sử xác thực liên quan.",
            "success",
        )
    except Exception as exc:
        flash(str(exc), "error")
    return redirect(url_for("keys"))


@app.route("/sign", methods=["GET", "POST"])
def sign():
    result = None
    content = ""
    selected_key = ""
    method = request.args.get("method", "")

    if request.method == "POST" and not method:
        method = request.form.get("processing_method", "")
        if method not in {"text", "pdf"}:
            flash("Vui lòng chọn phương thức xử lý", "error")
        else:
            return redirect(url_for("sign", method=method))

    if method not in {"", "text", "pdf"}:
        return redirect(url_for("sign"))

    if request.method == "POST" and method:
        selected_key = request.form.get("key_id", "")
        try:
            if method == "pdf":
                result = _sign_pdf_from_form(selected_key)
                history_service.save_sign_history(
                    {
                        "document_name": result["document_name"],
                        "owner_name": result["owner_name"],
                        "key_id": selected_key,
                        "signed_at": result["signed_at"],
                        "hash": result["hash"],
                        "signature_path": result["signed_document_path"],
                    }
                )
                flash("Ky PDF thanh cong.", "success")
                return render_template(
                    "sign.html",
                    keys=key_manager.list_keys(),
                    result=result,
                    content=content,
                    selected_key=selected_key,
                    method=method,
                )

            content, source_file_name = _content_from_form(method)
            normalized = document_service.normalize_text(content)
            document_service.validate_text(normalized)
            if not selected_key:
                raise ValueError("Vui lòng chọn khóa riêng tư để ký.")

            private_key = key_manager.load_private_key(selected_key)
            sign_result = SignatureService.sign_text(normalized, private_key)
            metadata = key_manager.get_metadata(selected_key)
            signed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            signature_path = _save_signature_file(
                selected_key,
                sign_result["signature"],
                sign_result["hash"],
                signed_at,
            )
            signed_document_path = None

            result = {
                **sign_result,
                "key_id": selected_key,
                "owner_name": metadata.get("owner_name", ""),
                "signed_at": signed_at,
                "signature_path": signature_path,
                "signed_document_path": signed_document_path,
            }
            history_service.save_sign_history(
                {
                    "document_name": request.form.get("document_name") or source_file_name or "Văn bản nhập trực tiếp",
                    "owner_name": metadata.get("owner_name", ""),
                    "key_id": selected_key,
                    "signed_at": signed_at,
                    "hash": sign_result["hash"],
                    "signature_path": signature_path,
                }
            )
            flash("Ký văn bản thành công.", "success")
        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "sign.html",
        keys=key_manager.list_keys(),
        result=result,
        content=content,
        selected_key=selected_key,
        method=method,
    )


@app.route("/verify", methods=["GET", "POST"])
def verify():
    result = None
    content = ""
    signature = ""
    selected_key = ""
    method = request.args.get("method", "")

    if request.method == "POST" and not method:
        method = request.form.get("processing_method", "")
        if method not in {"text", "file", "pdf"}:
            flash("Vui lòng chọn phương thức xử lý", "error")
        else:
            return redirect(url_for("verify", method=method))

    if method not in {"", "text", "file", "pdf"}:
        return redirect(url_for("verify"))

    if request.method == "POST" and method:
        selected_key = request.form.get("key_id", "")
        signature = request.form.get("signature", "")
        try:
            if method == "pdf":
                if not selected_key:
                    raise ValueError("Vui long chon khoa cong khai de xac thuc.")
                uploaded_file = request.files.get("document_file")
                if not uploaded_file or not uploaded_file.filename:
                    raise ValueError("Vui long tai len file PDF can xac thuc.")
                if Path(uploaded_file.filename).suffix.lower() != ".pdf":
                    raise ValueError("Chi ho tro xac thuc file PDF.")

                public_key = key_manager.load_public_key(selected_key)
                result = PdfSignatureService.verify_pdf(uploaded_file.read(), public_key)
                history_service.save_verify_history(
                    {
                        "document_name": Path(uploaded_file.filename).name,
                        "key_id": selected_key,
                        "verified_at": result["verified_at"],
                        "result": "Hop le" if result["valid"] else "Khong hop le",
                        "message": result["message"],
                        "hash": result["hash"],
                    }
                )
                return render_template(
                    "verify.html",
                    keys=key_manager.list_keys(),
                    result=result,
                    content=content,
                    signature=signature,
                    selected_key=selected_key,
                    method=method,
                )

            content, source_file_name = _content_from_form(method)
            normalized = document_service.normalize_text(content)
            document_service.validate_text(normalized)
            if not selected_key:
                raise ValueError("Vui lòng chọn khóa công khai để xác thực.")

            public_key = key_manager.load_public_key(selected_key)
            valid = SignatureService.verify_text(normalized, signature, public_key)
            verified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_hash = HashService.hash_text(normalized)
            message = (
                "Chữ ký hợp lệ. Văn bản chưa bị sửa đổi."
                if valid
                else "Chữ ký không hợp lệ. Văn bản có thể đã bị sửa đổi, chữ ký bị sai hoặc dùng sai khóa."
            )
            result = {
                "valid": valid,
                "message": message,
                "hash": text_hash,
                "verified_at": verified_at,
            }
            history_service.save_verify_history(
                {
                    "document_name": request.form.get("document_name") or "Văn bản nhập trực tiếp",
                    "key_id": selected_key,
                    "verified_at": verified_at,
                    "result": "Hợp lệ" if valid else "Không hợp lệ",
                    "message": message,
                    "hash": text_hash,
                }
            )
        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "verify.html",
        keys=key_manager.list_keys(),
        result=result,
        content=content,
        signature=signature,
        selected_key=selected_key,
        method=method,
    )


@app.route("/history")
def history():
    return render_template(
        "history.html",
        sign_history=history_service.get_sign_history(),
        verify_history=history_service.get_verify_history(),
    )


@app.route("/download/public/<key_id>")
def download_public_key(key_id):
    path = Path("storage/keys") / key_id / "public_key.pem"
    if not path.exists():
        flash("Không tìm thấy khóa công khai.", "error")
        return redirect(url_for("keys"))
    return send_file(path, as_attachment=True)


@app.route("/keys/<key_id>/signature-image")
def key_signature_image(key_id):
    try:
        path = key_manager.get_signature_image_path(key_id)
        if not path:
            raise FileNotFoundError("Không tìm thấy ảnh chữ ký.")
        return send_file(path)
    except Exception as exc:
        flash(str(exc), "error")
        return redirect(url_for("keys"))


@app.route("/download/signature")
def download_signature():
    path = request.args.get("path", "")
    target = Path(path)
    if not target.exists() or signature_dir.resolve() not in target.resolve().parents:
        flash("Không tìm thấy file chữ ký.", "error")
        return redirect(url_for("sign"))
    return send_file(target, as_attachment=True)


@app.route("/download/signed-document")
def download_signed_document():
    path = request.args.get("path", "")
    target = Path(path)
    if not target.exists() or signed_document_dir.resolve() not in target.resolve().parents:
        flash("Không tìm thấy file đã ký.", "error")
        return redirect(url_for("sign", method="file"))
    return send_file(target, as_attachment=True)


def _content_from_form(method):
    if method == "file":
        uploaded_file = request.files.get("document_file")
        if not uploaded_file or not uploaded_file.filename:
            raise ValueError("Vui lòng tải lên file cần xử lý.")
        return document_service.read_text_file(uploaded_file), Path(uploaded_file.filename).name
    return request.form.get("content", ""), ""


def _sign_pdf_from_form(selected_key):
    if not selected_key:
        raise ValueError("Vui long chon khoa rieng tu de ky.")

    uploaded_file = request.files.get("document_file")
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("Vui long tai len file PDF can ky.")
    if Path(uploaded_file.filename).suffix.lower() != ".pdf":
        raise ValueError("Chi ho tro ky file PDF.")

    pdf_bytes = uploaded_file.read()
    if not pdf_bytes:
        raise ValueError("File PDF khong duoc de trong.")

    metadata = key_manager.get_metadata(selected_key)
    sign_result = PdfSignatureService.sign_pdf(
        pdf_bytes,
        key_manager.load_private_key(selected_key),
        selected_key,
        metadata.get("owner_name", ""),
        _pdf_placement_from_form(),
        _pdf_signature_image_source_from_form(selected_key),
    )

    source_name = Path(uploaded_file.filename).name
    source_stem = Path(source_name).stem or "document"
    safe_stem = "".join(ch for ch in source_stem if ch.isalnum() or ch in ("-", "_")) or "document"
    output_path = signed_document_dir / f"signed_{safe_stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path.write_bytes(sign_result["pdf_bytes"])

    return {
        "hash": sign_result["hash"],
        "signature": sign_result["signature"],
        "algorithm": sign_result["algorithm"],
        "key_id": selected_key,
        "owner_name": metadata.get("owner_name", ""),
        "signed_at": sign_result["signed_at"],
        "signature_path": str(output_path),
        "signed_document_path": str(output_path),
        "document_name": source_name,
        "signed_page": sign_result["page"],
    }


def _pdf_placement_from_form():
    return {
        "x": _int_from_form("x", 160, 0, 10000),
        "y": _int_from_form("y", 120, 0, 10000),
        "w": _int_from_form("w", 220, 50, 10000),
        "h": _int_from_form("h", 90, 30, 10000),
        "page": _int_from_form("page", 1, 1, 10000),
    }


def _pdf_signature_image_source_from_form(key_id):
    image_file = request.files.get("signature_image")
    if image_file and image_file.filename:
        suffix = Path(image_file.filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Anh chu ky chi ho tro PNG, JPG hoac JPEG.")
        image_bytes = image_file.read()
        if not image_bytes:
            raise ValueError("Anh chu ky khong duoc de trong.")
        return io.BytesIO(image_bytes)

    return key_manager.get_signature_image_path(key_id)


def _save_signature_file(key_id, signature, text_hash, signed_at):
    file_name = f"signature_{key_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = signature_dir / file_name
    payload = {
        "signature": signature,
        "hash_algorithm": "SHA-256",
        "signature_algorithm": "RSA-SHA256",
        "key_id": key_id,
        "hash": text_hash,
        "signed_at": signed_at,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _signature_image_config_from_form(key_id):
    image_file = request.files.get("signature_image")
    data_url = None
    if image_file and image_file.filename:
        data_url = _image_file_to_data_url(image_file)
    else:
        saved_image_path = key_manager.get_signature_image_path(key_id)
        if saved_image_path:
            metadata = key_manager.get_metadata(key_id)
            image_type = metadata.get("signature_image_type", "image/png")
            data_url = _image_path_to_data_url(saved_image_path, image_type)

    if not data_url:
        return None

    return {
        "data_url": data_url,
        "position": request.form.get("signature_position", "right"),
        "offset_x": _int_from_form("signature_offset_x", 0, -240, 240),
        "offset_y": _int_from_form("signature_offset_y", 0, -240, 240),
        "width": _int_from_form("signature_width", 180, 80, 360),
    }


def _image_file_to_data_url(image_file):
    suffix = Path(image_file.filename).suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    if suffix not in mime_types:
        raise ValueError("Ảnh chữ ký chỉ hỗ trợ PNG, JPG hoặc JPEG.")

    image_bytes = image_file.read()
    if not image_bytes:
        raise ValueError("Ảnh chữ ký không được để trống.")

    return f"data:{mime_types[suffix]};base64,{base64.b64encode(image_bytes).decode('ascii')}"


def _image_path_to_data_url(path, image_type):
    return f"data:{image_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _int_from_form(field_name, default, min_value, max_value):
    try:
        value = int(request.form.get(field_name, default))
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(value, max_value))


def _save_signed_document_file(content, source_file_name, sign_metadata, image_config):
    source_stem = Path(source_file_name or "document.txt").stem or "document"
    safe_stem = "".join(ch for ch in source_stem if ch.isalnum() or ch in ("-", "_")) or "document"
    file_name = f"signed_{safe_stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    path = signed_document_dir / file_name

    signature_block = json.dumps(
        {
            "note": "Ảnh chữ ký chỉ dùng để hiển thị. Chữ ký số RSA mới dùng để xác thực.",
            "signature": sign_metadata["signature"],
            "hash": sign_metadata["hash"],
            "hash_algorithm": "SHA-256",
            "signature_algorithm": sign_metadata["algorithm"],
            "key_id": sign_metadata["key_id"],
            "owner_name": sign_metadata["owner_name"],
            "signed_at": sign_metadata["signed_at"],
        },
        ensure_ascii=False,
        indent=2,
    )
    document_html = html.escape(content)
    signature_visual = ""
    position_class = "signature-right"
    if image_config:
        position = image_config["position"]
        if position not in {"left", "center", "right"}:
            position = "right"
        position_class = f"signature-{position}"
        signature_visual = (
            f'<img class="signature-image" src="{image_config["data_url"]}" alt="Ảnh chữ ký" '
            f'style="width:{image_config["width"]}px; '
            f'transform: translate({image_config["offset_x"]}px, {image_config["offset_y"]}px);">'
        )

    rendered = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <title>Tài liệu đã ký - {html.escape(source_file_name or "document.txt")}</title>
  <style>
    body {{ margin: 0; background: #eef3f8; color: #142033; font-family: Arial, sans-serif; }}
    main {{ width: min(860px, calc(100% - 32px)); margin: 32px auto; background: #fff; border: 1px solid #d9e3ef; box-shadow: 0 16px 42px rgba(20, 32, 51, 0.12); }}
    .document {{ min-height: 760px; padding: 48px; white-space: pre-wrap; line-height: 1.7; }}
    .signature-area {{ display: flex; padding: 8px 48px 42px; min-height: 150px; align-items: center; }}
    .signature-left {{ justify-content: flex-start; }}
    .signature-center {{ justify-content: center; }}
    .signature-right {{ justify-content: flex-end; }}
    .signature-image {{ display: block; max-width: 100%; object-fit: contain; }}
    .metadata {{ border-top: 1px solid #d9e3ef; padding: 18px 48px 32px; background: #f8fbff; }}
    .metadata h2 {{ margin: 0 0 10px; font-size: 16px; }}
    .metadata pre {{ overflow: auto; padding: 14px; border: 1px solid #d9e3ef; border-radius: 8px; background: #fff; font-size: 12px; }}
  </style>
</head>
<body>
  <main>
    <section class="document">{document_html}</section>
    <section class="signature-area {position_class}">{signature_visual}</section>
    <section class="metadata">
      <h2>Metadata chữ ký số RSA</h2>
      <pre>{html.escape(signature_block)}</pre>
    </section>
  </main>
</body>
</html>
"""
    path.write_text(rendered, encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    app.run(debug=True)
