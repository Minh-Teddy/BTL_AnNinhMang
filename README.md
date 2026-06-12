# Ứng dụng chữ ký số RSA

Demo Flask cho đề tài "Ứng dụng chữ ký số RSA để xác thực nội dung văn bản - có kiểm tra sửa đổi".

## Chức năng

- Tạo, xem, tải và xóa cặp khóa RSA.
- Ký văn bản nhập trực tiếp hoặc file `.txt`.
- Sinh mã băm SHA-256 và chữ ký Base64.
- Xác thực chữ ký bằng khóa công khai.
- Phát hiện văn bản bị sửa đổi, dùng sai khóa hoặc sai chữ ký.
- Lưu khóa, chữ ký và lịch sử bằng file JSON/PEM.

## Cấu trúc

```text
services/         Module xử lý nghiệp vụ
templates/        Giao diện HTML
static/css/       File giao diện, font, màu nền
static/js/        File JavaScript
storage/          Khóa, văn bản, chữ ký, lịch sử
app.py            Flask app
```

## Chạy dự án

```bash
pip install -r requirements.txt
python app.py
```

Sau đó mở `http://127.0.0.1:5000`.

## Luồng demo nhanh

1. Vào `Khóa RSA`, tạo `Key_Minh`.
2. Vào `Ký văn bản`, nhập nội dung và ký bằng `Key_Minh`.
3. Sao chép chữ ký Base64.
4. Vào `Xác thực`, nhập lại văn bản gốc, dán chữ ký và chọn `Key_Minh`.
5. Sửa một ký tự trong văn bản rồi xác thực lại để thấy kết quả không hợp lệ.
