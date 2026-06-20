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


# NHOM 1 - DIEU HUONG GIAO DIEN VA QUAN LY KHOA
# Cac route trong nhom nay hien thi trang chu, tao/xoa khoa va xem lich su.
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
    """NHOM 2 - Ky noi dung text hoac PDF bang khoa rieng RSA."""
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
                return render_template(
                    "sign_result.html",
                    result=result,
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
            document_name = source_file_name or "Văn bản nhập trực tiếp"
            signature_path = _save_signed_text_package(
                normalized,
                document_name,
                selected_key,
                metadata.get("owner_name", ""),
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
                "document_name": document_name,
                "signature_path": signature_path,
                "signed_document_path": signed_document_path,
            }
            history_service.save_sign_history(
                {
                    "document_name": document_name,
                    "owner_name": metadata.get("owner_name", ""),
                    "key_id": selected_key,
                    "signed_at": signed_at,
                    "hash": sign_result["hash"],
                    "signature_path": signature_path,
                }
            )
            return render_template(
                "sign_result.html",
                result=result,
                method=method,
            )
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
    """NHOM 3 - Xac thuc chu ky va thong bao kha nang noi dung bi sua."""
    result = None
    selected_key = ""
    method = request.args.get("method", "")

    if request.method == "POST" and not method:
        method = request.form.get("processing_method", "")
        if method not in {"text", "pdf"}:
            flash("Vui lòng chọn phương thức xử lý", "error")
        else:
            return redirect(url_for("verify", method=method))

    if method not in {"", "text", "pdf"}:
        return redirect(url_for("verify"))

    if request.method == "POST" and method:
        selected_key = request.form.get("key_id", "")
        try:
            if method == "pdf":
                if not selected_key:
                    raise ValueError("Vui lòng chọn khóa công khai để xác thực.")
                uploaded_file = request.files.get("document_file")
                if not uploaded_file or not uploaded_file.filename:
                    raise ValueError("Vui lòng tải lên tệp PDF cần xác thực.")
                if Path(uploaded_file.filename).suffix.lower() != ".pdf":
                    raise ValueError("Chỉ hỗ trợ xác thực tệp PDF.")

                public_key = key_manager.load_public_key(selected_key)
                result = PdfSignatureService.verify_pdf(uploaded_file.read(), public_key)
                history_service.save_verify_history(
                    {
                        "document_name": Path(uploaded_file.filename).name,
                        "key_id": selected_key,
                        "verified_at": result["verified_at"],
                        "result": "Hợp lệ" if result["valid"] else "Không hợp lệ",
                        "message": result["message"],
                        "hash": result["hash"],
                    }
                )
                return render_template(
                    "verify_result.html",
                    result=result,
                    selected_key=selected_key,
                )

            package = _signed_text_package_from_form()
            selected_key = package["key_id"]
            normalized = document_service.normalize_text(package["content"])
            document_service.validate_text(normalized)

            public_key = key_manager.load_public_key(selected_key)
            signature_valid = SignatureService.verify_text(
                normalized,
                package["signature"],
                public_key,
            )
            verified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text_hash = HashService.hash_text(normalized)
            hash_valid = HashService.compare_hash(text_hash, package["hash"])
            valid = signature_valid and hash_valid
            if valid:
                message = "Chữ ký hợp lệ. Văn bản chưa bị sửa đổi."
            elif not hash_valid:
                message = "Nội dung trong gói văn bản đã bị sửa đổi sau khi ký."
            else:
                message = "Chữ ký không hợp lệ hoặc không khớp với khóa công khai."

            result = {
                "valid": valid,
                "message": message,
                "hash": text_hash,
                "verified_at": verified_at,
            }
            history_service.save_verify_history(
                {
                    "document_name": package["document_name"],
                    "key_id": selected_key,
                    "verified_at": verified_at,
                    "result": "Hợp lệ" if valid else "Không hợp lệ",
                    "message": message,
                    "hash": text_hash,
                }
            )
            return render_template(
                "verify_result.html",
                result=result,
                selected_key=selected_key,
            )
        except Exception as exc:
            flash(str(exc), "error")

    return render_template(
        "verify.html",
        keys=key_manager.list_keys(),
        result=result,
        selected_key=selected_key,
        method=method,
    )


@app.route("/history")
def history():
    """NHOM 4 - Hien thi nhat ky ky va xac thuc."""
    return render_template(
        "history.html",
        sign_history=history_service.get_sign_history(),
        verify_history=history_service.get_verify_history(),
    )


@app.route("/download/public/<key_id>")
def download_public_key(key_id):
    """NHOM 5 - Tai cac ket qua do he thong tao ra."""
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
        flash("Không tìm thấy tệp chữ ký.", "error")
        return redirect(url_for("sign"))
    return send_file(target, as_attachment=True)


@app.route("/download/signed-document")
def download_signed_document():
    path = request.args.get("path", "")
    target = Path(path)
    if not target.exists() or signed_document_dir.resolve() not in target.resolve().parents:
        flash("Không tìm thấy tệp đã ký.", "error")
        return redirect(url_for("sign"))
    return send_file(target, as_attachment=True)


def _content_from_form(method):
    """NHOM 6 - Doc va chuan hoa du lieu dau vao tu bieu mau."""
    if method == "file":
        uploaded_file = request.files.get("document_file")
        if not uploaded_file or not uploaded_file.filename:
            raise ValueError("Vui lòng tải lên tệp cần xử lý.")
        return document_service.read_text_file(uploaded_file), Path(uploaded_file.filename).name
    return request.form.get("content", ""), ""


def _signed_text_package_from_form():
    """Doc va kiem tra cau truc goi van ban da ky do nguoi dung tai len."""
    package_file = request.files.get("signed_text_package")
    if not package_file or not package_file.filename:
        raise ValueError("Vui lòng tải lên gói văn bản đã ký.")
    if Path(package_file.filename).suffix.lower() != ".json":
        raise ValueError("Gói văn bản đã ký phải là tệp JSON.")

    package_bytes = package_file.read(5 * 1024 * 1024 + 1)
    if len(package_bytes) > 5 * 1024 * 1024:
        raise ValueError("Gói văn bản đã ký không được vượt quá 5 MB.")

    try:
        package = json.loads(package_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Gói văn bản đã ký không phải JSON UTF-8 hợp lệ.") from exc

    if not isinstance(package, dict):
        raise ValueError("Cấu trúc gói văn bản đã ký không hợp lệ.")
    if package.get("format") != "RSA_SIGNED_TEXT" or package.get("version") != 1:
        raise ValueError("Định dạng hoặc phiên bản gói văn bản không được hỗ trợ.")
    if package.get("hash_algorithm") != "SHA-256":
        raise ValueError("Gói văn bản không sử dụng thuật toán băm SHA-256.")
    if package.get("signature_algorithm") != "RSA-SHA256":
        raise ValueError("Gói văn bản không sử dụng thuật toán chữ ký RSA-SHA256.")

    required_text_fields = ("content", "key_id", "hash", "signature")
    for field_name in required_text_fields:
        value = package.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Gói văn bản thiếu trường bắt buộc: {field_name}.")

    document_name = package.get("document_name")
    package["document_name"] = (
        document_name.strip()
        if isinstance(document_name, str) and document_name.strip()
        else "Văn bản đã ký"
    )
    return package


def _sign_pdf_from_form(selected_key):
    """Dieu phoi viec ky PDF, dong tem va luu file ket qua."""
    if not selected_key:
        raise ValueError("Vui lòng chọn khóa riêng tư để ký.")

    uploaded_file = request.files.get("document_file")
    if not uploaded_file or not uploaded_file.filename:
        raise ValueError("Vui lòng tải lên tệp PDF cần ký.")
    if Path(uploaded_file.filename).suffix.lower() != ".pdf":
        raise ValueError("Chỉ hỗ trợ ký tệp PDF.")

    pdf_bytes = uploaded_file.read()
    if not pdf_bytes:
        raise ValueError("Tệp PDF không được để trống.")

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
    """Lay toa do tem PDF va gioi han gia tri trong pham vi hop le."""
    return {
        "x": _int_from_form("x", 160, 0, 10000),
        "y": _int_from_form("y", 120, 0, 10000),
        "w": _int_from_form("w", 220, 50, 10000),
        "h": _int_from_form("h", 90, 30, 10000),
        "page": _int_from_form("page", 1, 1, 10000),
    }


def _pdf_signature_image_source_from_form(key_id):
    """Lay anh chu ky moi, hoac anh da luu cung cap khoa."""
    image_file = request.files.get("signature_image")
    if image_file and image_file.filename:
        suffix = Path(image_file.filename).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise ValueError("Ảnh chữ ký chỉ hỗ trợ PNG, JPG hoặc JPEG.")
        image_bytes = image_file.read()
        if not image_bytes:
            raise ValueError("Ảnh chữ ký không được để trống.")
        return io.BytesIO(image_bytes)

    return key_manager.get_signature_image_path(key_id)


def _save_signed_text_package(
    content,
    document_name,
    key_id,
    owner_name,
    signature,
    text_hash,
    signed_at,
):
    """Luu noi dung va chu ky text trong mot goi JSON co the xac thuc lai."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"signed_text_{key_id}_{timestamp}.json"
    path = signature_dir / file_name
    payload = {
        "format": "RSA_SIGNED_TEXT",
        "version": 1,
        "document_name": document_name,
        "content": content,
        "owner_name": owner_name,
        "key_id": key_id,
        "signed_at": signed_at,
        "hash": text_hash,
        "hash_algorithm": "SHA-256",
        "signature_algorithm": "RSA-SHA256",
        "signature": signature,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _signature_image_config_from_form(key_id):
    """NHOM 7 - Ho tro anh chu ky hien thi (khong phai chu ky so RSA)."""
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
    """Chuyen mot truong bieu mau sang so nguyen co gioi han."""
    try:
        value = int(request.form.get(field_name, default))
    except (TypeError, ValueError):
        value = default
    return max(min_value, min(value, max_value))


def _save_signed_document_file(content, source_file_name, sign_metadata, image_config):
    """Tao ban HTML co noi dung, anh hien thi va metadata chu ky.

    Ham nay hien khong duoc route ky hien tai goi; duoc giu lai nhu ma ho tro
    cho dinh dang tai lieu HTML cu.
    """
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
