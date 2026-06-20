import base64
import hashlib
import io
from datetime import datetime

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:  # pragma: no cover - compatibility for older installs
    from PyPDF2 import PdfReader, PdfWriter


class PdfSignatureService:
    """NHOM PDF - Dong tem hien thi, nhung metadata RSA va xac thuc metadata."""
    @staticmethod
    def sign_pdf(pdf_bytes, private_key, key_id, owner_name, placement, signature_image_source=None):
        """Bam PDF goc, ky hash, dong tem va nhung ket qua vao metadata."""
        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
        signature = private_key.sign(
            bytes.fromhex(pdf_hash),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        signed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter()
        target_page = max(1, min(int(placement["page"]), len(reader.pages)))

        for index, page in enumerate(reader.pages, start=1):
            writer.add_page(page)
            if index == target_page:
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                stamp = PdfSignatureService._create_signature_stamp(
                    owner_name=owner_name,
                    signed_at=signed_at,
                    page_width=width,
                    page_height=height,
                    center_x=placement["x"],
                    center_y=placement["y"],
                    stamp_width=placement["w"],
                    stamp_height=placement["h"],
                    signature_image_source=signature_image_source,
                )
                writer.pages[-1].merge_page(PdfReader(stamp).pages[0])

        writer.add_metadata(
            {
                "/RSA_Signature": base64.b64encode(signature).decode("ascii"),
                "/RSA_Original_SHA256": pdf_hash,
                "/RSA_Signature_Algorithm": "RSA-SHA256",
                "/RSA_KeyID": key_id,
                "/RSA_Signer": owner_name,
                "/RSA_SignedAt": signed_at,
                "/RSA_SignedPage": str(target_page),
            }
        )

        output = io.BytesIO()
        writer.write(output)
        return {
            "pdf_bytes": output.getvalue(),
            "hash": pdf_hash,
            "signature": base64.b64encode(signature).decode("ascii"),
            "algorithm": "RSA-SHA256",
            "signed_at": signed_at,
            "page": target_page,
        }

    @staticmethod
    def verify_pdf(pdf_bytes, public_key):
        """Xac thuc chu ky cua hash duoc doc tu metadata PDF.

        Luu y: phien ban hien tai chua tinh lai hash tu noi dung PDF tai len,
        nen ham nay chua the ket luan chac chan rang trang PDF khong bi sua.
        """
        reader = PdfReader(io.BytesIO(pdf_bytes))
        metadata = reader.metadata or {}
        signature = metadata.get("/RSA_Signature")
        original_hash = metadata.get("/RSA_Original_SHA256")

        if not signature or not original_hash:
            return {
                "valid": False,
                "message": "Tệp PDF không có metadata chữ ký RSA của hệ thống.",
                "hash": "",
                "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

        try:
            public_key.verify(
                base64.b64decode(signature, validate=True),
                bytes.fromhex(original_hash),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            valid = True
            message = (
                f"Chữ ký hợp lệ. Người ký: {metadata.get('/RSA_Signer', 'Không xác định')}; "
                f"thời gian: {metadata.get('/RSA_SignedAt', 'Không xác định')}."
            )
        except (InvalidSignature, ValueError, TypeError):
            valid = False
            message = "Chữ ký PDF không hợp lệ hoặc metadata đã bị sửa."

        return {
            "valid": valid,
            "message": message,
            "hash": original_hash,
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def _create_signature_stamp(
        owner_name,
        signed_at,
        page_width,
        page_height,
        center_x,
        center_y,
        stamp_width,
        stamp_height,
        signature_image_source=None,
    ):
        """Tao lop PDF trong suot chua thong tin va anh chu ky hien thi."""
        buffer = io.BytesIO()
        pdf_canvas = canvas.Canvas(buffer, pagesize=(page_width, page_height))

        x = max(0, min(center_x - stamp_width / 2, page_width - stamp_width))
        y = max(0, min(center_y - stamp_height / 2, page_height - stamp_height))

        pdf_canvas.setStrokeColorRGB(0.04, 0.27, 0.58)
        pdf_canvas.setFillColorRGB(1, 1, 1, alpha=0.92)
        pdf_canvas.setLineWidth(1.4)
        pdf_canvas.rect(x, y, stamp_width, stamp_height, stroke=1, fill=1)

        text_area_width = stamp_width * 0.58
        lines = ["DIGITALLY SIGNED", f"By: {owner_name}", f"Time: {signed_at}"]
        longest_line = max(lines, key=len)
        font_size = min(text_area_width / max(len(longest_line) * 0.55, 1), stamp_height / 5.0)
        font_size = max(4, min(font_size, 14))
        line_spacing = font_size * 1.22
        text_x = x + stamp_width * 0.04
        text_y = y + stamp_height / 2 + line_spacing

        pdf_canvas.setFillColorRGB(0.05, 0.09, 0.16)
        pdf_canvas.setFont("Helvetica-Bold", font_size)
        pdf_canvas.drawString(text_x, text_y, lines[0])
        pdf_canvas.setFont("Helvetica", font_size)
        pdf_canvas.drawString(text_x, text_y - line_spacing, lines[1])
        pdf_canvas.setFont("Helvetica", font_size * 0.85)
        pdf_canvas.drawString(text_x, text_y - line_spacing * 2, lines[2])

        if signature_image_source:
            image_reader = ImageReader(signature_image_source)
            image_width, image_height = image_reader.getSize()
            allowed_width = stamp_width * 0.36
            allowed_height = stamp_height * 0.78
            draw_width = allowed_width
            draw_height = draw_width * (image_height / float(image_width))
            if draw_height > allowed_height:
                draw_height = allowed_height
                draw_width = draw_height * (image_width / float(image_height))

            image_center_x = x + stamp_width * 0.8
            image_center_y = y + stamp_height / 2
            pdf_canvas.drawImage(
                image_reader,
                image_center_x - draw_width / 2,
                image_center_y - draw_height / 2,
                width=draw_width,
                height=draw_height,
                mask="auto",
            )

        pdf_canvas.save()
        buffer.seek(0)
        return buffer
