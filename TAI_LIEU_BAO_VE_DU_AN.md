# TÀI LIỆU GIẢI THÍCH VÀ BẢO VỆ DỰ ÁN

## ỨNG DỤNG CHỮ KÝ SỐ RSA ĐỂ XÁC THỰC NỘI DUNG VĂN BẢN - CÓ KIỂM TRA SỬA ĐỔI

Tài liệu được lập theo phiên bản mã nguồn hiện tại ngày 20/06/2026.

Mục tiêu: giúp người trình bày hiểu nghiệp vụ, thuật toán, luồng gọi hàm, dữ liệu đầu vào/đầu ra, giới hạn kỹ thuật và có thể trả lời câu hỏi của giảng viên.

> Lưu ý quan trọng: tài liệu mô tả đúng chương trình hiện tại. Luồng text phát hiện sửa đổi đúng bằng RSA-SHA256. Luồng PDF hiện còn hạn chế về kiểm tra nội dung sau khi ký; chi tiết nằm tại mục 9.

<!-- PAGE BREAK -->

# 1. TỔNG QUAN ĐỀ TÀI

## 1.1. Bài toán cần giải quyết

Khi nhận một văn bản điện tử, người nhận cần trả lời ba câu hỏi:

- Nội dung hiện tại có đúng là nội dung đã được ký hay không?
- Chữ ký có được tạo bởi khóa riêng tương ứng với khóa công khai đang kiểm tra hay không?
- Nội dung có bị sửa đổi sau thời điểm ký hay không?

Ứng dụng sử dụng:

- **RSA 2048-bit** để tạo cặp khóa và ký/xác thực.
- **SHA-256** để tạo giá trị đại diện cố định cho nội dung.
- **Base64** để chuyển chữ ký nhị phân thành chuỗi có thể lưu trong JSON hoặc metadata.
- **Flask** để xây dựng giao diện và điều phối nghiệp vụ.
- **cryptography** để thực hiện phép ký và xác thực RSA.
- **pypdf/PyPDF2 và reportlab** để đọc, ghi, đóng tem PDF.

## 1.2. Ba thuộc tính bảo mật liên quan

- **Tính toàn vẹn:** nội dung thay đổi thì chữ ký cũ không còn hợp lệ.
- **Tính xác thực:** chữ ký hợp lệ với khóa công khai chứng minh nó được tạo bởi khóa riêng tương ứng.
- **Khả năng chống chối bỏ:** chỉ có ý nghĩa mạnh khi khóa riêng được bảo vệ và khóa công khai gắn với danh tính qua chứng thư số/PKI. Dự án hiện chưa có PKI nên chỉ minh họa nguyên lý, chưa đạt mức pháp lý hoàn chỉnh.

## 1.3. Chữ ký số không phải mã hóa

Chữ ký số không làm bí mật nội dung. Người khác vẫn đọc được văn bản. Chữ ký số bảo vệ nguồn gốc và tính toàn vẹn. Nếu cần bí mật phải dùng thêm mã hóa dữ liệu.

## 1.4. Chữ ký số và ảnh chữ ký khác nhau

| Thành phần | Mục đích | Có dùng để xác thực mật mã không? |
| --- | --- | --- |
| Chữ ký số RSA | Kết quả toán học tạo từ nội dung và khóa riêng | Có |
| Ảnh chữ ký PNG/JPG | Hiển thị trực quan trên tem PDF | Không |
| SHA-256 | Đại diện nội dung để phát hiện thay đổi | Có, là đầu vào của quy trình chữ ký |

Nếu xóa hoặc thay ảnh chữ ký nhưng chữ ký RSA và nội dung không đổi thì về nguyên lý mật mã, ảnh không quyết định tính hợp lệ. Trong dự án, ảnh chỉ là phần trình bày.

# 2. KIẾN TRÚC VÀ TRÁCH NHIỆM CÁC TỆP

| Tệp/thư mục | Trách nhiệm |
| --- | --- |
| `app.py` | Điểm vào Flask; nhận request, kiểm tra form, gọi service, ghi lịch sử và render kết quả. |
| `services/key_manager.py` | Tạo, đọc, liệt kê, xuất và xóa cặp khóa RSA. |
| `services/signature_service.py` | Ký và xác thực nội dung text bằng RSA PKCS#1 v1.5/SHA-256. |
| `services/hash_service.py` | Tính SHA-256 cho text/tệp và so sánh hai hash. |
| `services/document_service.py` | Chuẩn hóa, kiểm tra, đọc và lưu văn bản text. |
| `services/pdf_signature_service.py` | Băm/ký PDF, tạo tem, nhúng metadata và xác thực metadata RSA. |
| `services/history_service.py` | Lưu và đọc lịch sử ký/xác thực trong JSON. |
| `templates/*.html` | Giao diện Jinja2. |
| `static/js/main.js` | Chọn phương thức, xem trước ảnh/PDF, kéo thả và đổi kích thước tem. |
| `static/css/style.css` | Trình bày giao diện. |
| `storage/keys` | Khóa riêng, khóa công khai, metadata và ảnh chữ ký. |
| `storage/signatures` | Gói văn bản text đã ký dạng JSON. |
| `storage/signed_documents` | PDF đã đóng tem và nhúng metadata. |
| `storage/histories` | Lịch sử ký và xác thực. |

## 2.1. Mô hình phân lớp

1. **Presentation:** template HTML, CSS, JavaScript.
2. **Controller:** các route trong `app.py`.
3. **Service:** các lớp trong `services`.
4. **Storage:** các tệp PEM, JSON, PDF và ảnh trong `storage`.

Controller không tự cài đặt phép RSA. Nó gọi `SignatureService`, `PdfSignatureService` và `KeyManager`. Cách tách này giúp nghiệp vụ dễ kiểm thử và tránh đặt toàn bộ logic vào route.

<!-- PAGE BREAK -->

# 3. NỀN TẢNG THUẬT TOÁN

## 3.1. SHA-256

SHA-256 nhận dữ liệu có độ dài bất kỳ và tạo ra digest 256 bit, thường hiển thị bằng 64 ký tự hexadecimal.

Đặc điểm cần nhớ:

- Cùng đầu vào thì cùng hash.
- Thay đổi rất nhỏ ở đầu vào tạo hash rất khác.
- Không thể suy ngược nội dung gốc từ hash theo cách thực tế.
- Khả năng tìm hai nội dung có cùng hash là cực kỳ thấp với SHA-256.

Trong code text, `HashService.hash_text()` thực hiện:

```text
text -> UTF-8 bytes -> hashlib.sha256(...) -> chuỗi hex 64 ký tự
```

## 3.2. Cặp khóa RSA

- **Khóa riêng:** chỉ người ký giữ, dùng để tạo chữ ký.
- **Khóa công khai:** có thể chia sẻ, dùng để xác thực.
- Hai khóa liên hệ toán học nhưng không thể thực tế suy ra khóa riêng từ khóa công khai khi kích thước khóa đủ lớn.

Dự án tạo RSA 2048-bit với số mũ công khai `65537` trong `KeyManager.create_key()`.

## 3.3. RSA-SHA256 trong dự án

Text sử dụng:

```text
signature = RSA-PKCS1-v1_5-SIGN(private_key, SHA-256(UTF8(text)))
```

Code truyền bytes text cùng `hashes.SHA256()` vào `private_key.sign()`. Thư viện `cryptography` thực hiện bước băm SHA-256 bên trong trước khi tạo chữ ký.

Xác thực thực hiện phép ngược bằng khóa công khai. Nếu nội dung, chữ ký hoặc khóa không khớp, thư viện phát sinh `InvalidSignature` và hàm trả về `False`.

## 3.4. Vì sao dùng Base64

Chữ ký RSA là bytes nhị phân. JSON và metadata thuận tiện hơn với chuỗi văn bản, nên chương trình dùng Base64:

```text
signature bytes -> Base64 string -> lưu JSON/metadata
Base64 string -> signature bytes -> xác thực
```

Base64 không phải mã hóa bảo mật; nó chỉ là cách biểu diễn dữ liệu.

## 3.5. Chuẩn hóa xuống dòng

`DocumentService.normalize_text()` đổi `CRLF` và `CR` thành `LF`:

```text
\r\n -> \n
\r   -> \n
```

Mục đích là tránh cùng một văn bản bị coi là khác chỉ vì Windows và Linux dùng ký tự xuống dòng khác nhau. Nội dung sau chuẩn hóa mới được ký và lưu trong gói JSON.

# 4. NGHIỆP VỤ QUẢN LÝ KHÓA

## 4.1. Tạo cặp khóa

**Giao diện:** `templates/keys.html`.

**Route:** `keys()` tại `app.py:38`.

**Service chính:** `KeyManager.create_key()` tại `services/key_manager.py:24`.

Luồng xử lý:

1. Người dùng nhập tên khóa, tên chủ sở hữu và có thể chọn ảnh chữ ký.
2. Route lấy `key_name`, `owner_name`, `signature_image` từ form.
3. `_normalize_key_id()` bỏ ký tự không an toàn, đổi khoảng trắng thành `_`.
4. Kiểm tra tên khóa/chủ sở hữu không rỗng và khóa chưa tồn tại.
5. `rsa.generate_private_key(public_exponent=65537, key_size=2048)` sinh khóa riêng.
6. `private_key.public_key()` lấy khóa công khai tương ứng.
7. Khóa riêng được serialize theo PEM/PKCS8.
8. Khóa công khai được serialize theo PEM/SubjectPublicKeyInfo.
9. Ghi `private_key.pem`, `public_key.pem`, `metadata.json`.
10. Nếu có ảnh, `save_signature_image()` kiểm tra PNG/JPG/JPEG và lưu cùng thư mục khóa.

Đầu ra mẫu:

```text
storage/keys/Key_Minh/
  private_key.pem
  public_key.pem
  metadata.json
  signature_image.png
```

## 4.2. Điểm cần trả lời khi bảo vệ

- Khóa riêng hiện dùng `NoEncryption()`, tức PEM chưa có mật khẩu.
- Đây là lựa chọn đơn giản cho demo cục bộ, không phù hợp production.
- Ứng dụng chưa có đăng nhập/phân quyền nên người truy cập ứng dụng có thể dùng khóa đang lưu.
- Ảnh chữ ký không nằm trong phép ký RSA.

<!-- PAGE BREAK -->

# 5. NGHIỆP VỤ KÝ VĂN BẢN TRỰC TIẾP

## 5.1. Đầu vào và đầu ra

**Đầu vào:** nội dung text và khóa riêng được chọn.

**Đầu ra:** một gói JSON duy nhất chứa nội dung đã chuẩn hóa, chữ ký, hash, mã khóa, chủ sở hữu, thời gian và thuật toán.

**Giao diện:** `templates/sign.html`.

**Route điều phối:** `sign()` tại `app.py:85`.

**Hàm mật mã:** `SignatureService.sign_text()` tại `services/signature_service.py:13`.

**Hàm lưu gói:** `_save_signed_text_package()` tại `app.py:458`.

## 5.2. Luồng từng bước

1. Người dùng mở `/sign` và chọn “Ký văn bản trực tiếp”.
2. Trình duyệt gửi phương thức `text`; route chuyển sang `/sign?method=text`.
3. Người dùng chọn khóa riêng và nhập nội dung.
4. `sign()` lấy `key_id` và nội dung từ form.
5. `_content_from_form("text")` trả nội dung nhập trực tiếp.
6. `DocumentService.normalize_text()` thống nhất xuống dòng.
7. `DocumentService.validate_text()` từ chối văn bản rỗng.
8. `KeyManager.load_private_key(key_id)` đọc `private_key.pem`.
9. `SignatureService.sign_text(normalized, private_key)` tạo chữ ký.
10. `HashService.hash_text(normalized)` tạo SHA-256 để hiển thị/lưu.
11. Chữ ký bytes được `encode_signature()` đổi sang Base64.
12. Route lấy metadata chủ sở hữu bằng `KeyManager.get_metadata()`.
13. `_save_signed_text_package()` tạo tệp `signed_text_<key>_<timestamp>.json`.
14. `HistoryService.save_sign_history()` ghi lịch sử ký.
15. Render `templates/sign_result.html` với người ký, khóa, thời gian và thuật toán.
16. Người dùng tải gói văn bản đã ký.

## 5.3. Thuật toán ký text dạng giả mã

```text
INPUT: content, key_id
normalized = normalize_line_endings(content)
if normalized is empty: reject
private_key = load_private_key(key_id)
digest = SHA256(UTF8(normalized))
signature = RSA_PKCS1_v1_5_SIGN(private_key, digest)
signature_b64 = BASE64(signature)
save package(normalized, digest, signature_b64, key_id, metadata)
OUTPUT: signed JSON package
```

## 5.4. Cấu trúc gói JSON

```json
{
  "format": "RSA_SIGNED_TEXT",
  "version": 1,
  "document_name": "Văn bản nhập trực tiếp",
  "content": "Nội dung đã được ký",
  "owner_name": "Minh",
  "key_id": "Key_Minh",
  "signed_at": "2026-06-20 09:03:09",
  "hash": "...64 ký tự hex...",
  "hash_algorithm": "SHA-256",
  "signature_algorithm": "RSA-SHA256",
  "signature": "...Base64..."
}
```

Ý nghĩa:

| Trường | Ý nghĩa | Có được tin cậy độc lập không? |
| --- | --- | --- |
| `format`, `version` | Nhận diện định dạng do hệ thống hỗ trợ | Dùng để parse |
| `content` | Nội dung được xác thực | Chỉ tin khi chữ ký hợp lệ |
| `owner_name` | Tên hiển thị | Không; có thể sửa trong JSON |
| `key_id` | Chỉ ra khóa công khai nội bộ | Dùng để tra khóa, nhưng phải xác thực RSA |
| `hash` | SHA-256 lúc ký | Phải tính lại và so sánh |
| `signature` | Chữ ký RSA Base64 | Phải xác thực bằng khóa công khai |

## 5.5. Vì sao gói JSON giảm sai sót

Người xác thực không cần nhập lại nội dung, dán chuỗi Base64 hoặc tự chọn khóa. Hệ thống tự lấy mọi thành phần từ gói, do đó tránh lỗi khoảng trắng, xuống dòng, thiếu ký tự Base64 và chọn nhầm khóa.

# 6. NGHIỆP VỤ XÁC THỰC VĂN BẢN TRỰC TIẾP

## 6.1. Đầu vào và hàm chính

**Đầu vào:** gói JSON đã tạo ở bước ký.

**Giao diện:** `templates/verify.html`.

**Route:** `verify()` tại `app.py:183`.

**Hàm đọc/kiểm tra gói:** `_signed_text_package_from_form()` tại `app.py:346`.

**Hàm xác thực:** `SignatureService.verify_text()` tại `services/signature_service.py:27`.

## 6.2. Luồng từng bước

1. Người dùng chọn “Xác thực văn bản trực tiếp”.
2. Người dùng tải gói JSON; không nhập lại nội dung, chữ ký hay khóa.
3. `_signed_text_package_from_form()` kiểm tra có tệp và phần mở rộng `.json`.
4. Chương trình đọc tối đa 5 MB để hạn chế gói quá lớn.
5. Decode UTF-8 có hỗ trợ BOM và parse bằng `json.loads()`.
6. Kiểm tra root phải là object/dictionary.
7. Kiểm tra `format == RSA_SIGNED_TEXT` và `version == 1`.
8. Kiểm tra `hash_algorithm == SHA-256`.
9. Kiểm tra `signature_algorithm == RSA-SHA256`.
10. Kiểm tra `content`, `key_id`, `hash`, `signature` là chuỗi không rỗng.
11. Route lấy `key_id` trong gói và nạp khóa công khai nội bộ.
12. Chuẩn hóa nội dung và tính `text_hash = SHA256(content)`.
13. `HashService.compare_hash(text_hash, package["hash"])` kiểm tra hash lưu trong gói.
14. `SignatureService.verify_text()` decode Base64 và gọi `public_key.verify()`.
15. Kết quả chỉ hợp lệ khi **cả hash và chữ ký RSA đều hợp lệ**.
16. Ghi lịch sử xác thực và render màn hình thành công/thất bại.

## 6.3. Thuật toán xác thực text dạng giả mã

```text
INPUT: signed_json_package
package = parse_and_validate_json()
content = normalize_line_endings(package.content)
public_key = load_public_key(package.key_id)
current_hash = SHA256(UTF8(content))
hash_valid = (current_hash == package.hash)
signature_valid = RSA_VERIFY(public_key, content, package.signature)
valid = hash_valid AND signature_valid
OUTPUT: valid/invalid, verification_time
```

## 6.4. Các tình huống kết quả

| Tình huống | Hash | RSA | Kết quả |
| --- | --- | --- | --- |
| Gói nguyên vẹn, đúng khóa | Đúng | Đúng | Hợp lệ |
| Sửa `content`, giữ hash/chữ ký | Sai | Sai | Không hợp lệ |
| Sửa `content` và sửa hash, giữ chữ ký | Đúng với nội dung mới | Sai | Không hợp lệ |
| Giữ nội dung, sửa chữ ký | Đúng | Sai | Không hợp lệ |
| Giữ nội dung/chữ ký, đổi `key_id` | Đúng | Sai hoặc không tìm thấy khóa | Không hợp lệ/lỗi khóa |
| Sửa `owner_name` | Hash nội dung có thể vẫn đúng | RSA có thể vẫn đúng | Tên này không đáng tin; danh tính phải dựa vào khóa/chứng thư |

## 6.5. Vì sao vừa so sánh hash vừa xác thực RSA

RSA đã đủ phát hiện nội dung thay đổi. Việc so sánh hash riêng giúp đưa ra thông báo dễ hiểu và kiểm tra tính nhất quán của gói. Tuy nhiên hash trong JSON không phải bí mật và có thể bị sửa; quyết định tin cậy cuối cùng vẫn phải dựa vào chữ ký RSA.

<!-- PAGE BREAK -->

# 7. NGHIỆP VỤ KÝ PDF

## 7.1. Hàm và dữ liệu

**Route:** nhánh `method == "pdf"` trong `sign()`.

**Điều phối form:** `_sign_pdf_from_form()` tại `app.py:387`.

**Xử lý mật mã/PDF:** `PdfSignatureService.sign_pdf()` tại `services/pdf_signature_service.py:21`.

**Tạo tem:** `_create_signature_stamp()` tại `services/pdf_signature_service.py:120`.

**JavaScript đặt vị trí:** `static/js/main.js`, khối `[data-pdf-placement]`.

## 7.2. Luồng từng bước

1. Người dùng tải PDF và chọn khóa riêng.
2. pdf.js render trang PDF trong trình duyệt.
3. Người dùng chọn trang, kéo và đổi kích thước khung tem.
4. JavaScript chuyển tọa độ màn hình sang tọa độ PDF và ghi vào input ẩn `x`, `y`, `w`, `h`, `page`.
5. Backend kiểm tra khóa, phần mở rộng `.pdf` và dữ liệu không rỗng.
6. Đọc toàn bộ `pdf_bytes` gốc.
7. `hashlib.sha256(pdf_bytes).hexdigest()` tính hash PDF gốc.
8. Code chuyển hash hex thành 32 bytes bằng `bytes.fromhex(pdf_hash)`.
9. `private_key.sign(..., hashes.SHA256())` lại băm 32 bytes đó trước khi RSA ký.
10. Đọc PDF bằng `PdfReader`, sao chép các trang sang `PdfWriter`.
11. `_create_signature_stamp()` tạo một trang overlay chứa khung, người ký, thời gian và ảnh chữ ký.
12. `merge_page()` ghép overlay vào trang được chọn.
13. Ghi metadata `/RSA_Signature`, `/RSA_Original_SHA256`, `/RSA_KeyID`, `/RSA_Signer`, `/RSA_SignedAt`.
14. Lưu PDF mới trong `storage/signed_documents`.
15. Ghi lịch sử và hiển thị màn hình ký thành công.

## 7.3. Điểm kỹ thuật cần nói chính xác

Đoạn PDF hiện tại thực hiện một dạng **băm hai lần**:

```text
h1 = SHA256(pdf_bytes)
signature = RSA_SIGN(private_key, SHA256(h1_bytes))
```

Lý do: code tự tính `h1`, sau đó API `private_key.sign(..., hashes.SHA256())` lại băm dữ liệu đầu vào. Hai phía ký và xác thực đang làm giống nhau nên chữ ký metadata vẫn kiểm tra được, nhưng thiết kế sạch hơn nên chọn một trong hai:

- Truyền trực tiếp bytes cần ký để thư viện tự SHA-256; hoặc
- Dùng cơ chế `Prehashed` nếu đã tự tính digest.

# 8. NGHIỆP VỤ XÁC THỰC PDF HIỆN TẠI

## 8.1. Luồng đang chạy

1. Người dùng tải PDF và chọn khóa công khai.
2. Route kiểm tra tệp `.pdf`.
3. `PdfSignatureService.verify_pdf()` đọc metadata.
4. Lấy `/RSA_Signature` và `/RSA_Original_SHA256`.
5. Decode chữ ký Base64.
6. Chuyển hash hex thành bytes.
7. Gọi `public_key.verify(..., hashes.SHA256())`.
8. Nếu không phát sinh `InvalidSignature`, trả về hợp lệ.

## 8.2. Giới hạn quan trọng của PDF

Hàm hiện tại **không tính lại hash từ nội dung PDF đang được tải lên**. Nó chỉ kiểm tra rằng chữ ký RSA khớp với giá trị hash nằm trong metadata.

Hệ quả: nếu nội dung/trang PDF bị sửa nhưng kẻ sửa giữ nguyên cặp metadata hash + chữ ký, hàm có thể vẫn báo hợp lệ. Do đó không nên tuyên bố phiên bản hiện tại phát hiện chắc chắn mọi sửa đổi PDF.

Nguyên nhân thiết kế: hash được tạo từ PDF gốc trước khi đóng tem, nhưng file đầu ra đã thay đổi do thêm tem và metadata. Verifier không có quy tắc canonical hoặc `ByteRange` để tái tạo đúng bytes đã ký.

## 8.3. Hướng sửa đúng

- Dùng chữ ký PDF chuẩn PAdES/CMS với `/ByteRange` và chứng thư X.509.
- Hoặc thiết kế định dạng detached signature: giữ PDF gốc bất biến và lưu chữ ký ở tệp riêng.
- Hoặc xác định chính xác vùng bytes được ký và loại trừ vùng chứa chữ ký theo quy tắc ổn định.

Nếu giảng viên hỏi “PDF có phát hiện sửa đổi hoàn toàn chưa?”, câu trả lời đúng là: **chưa; text làm đúng, PDF mới minh họa nhúng metadata và cần nâng cấp sang PAdES/ByteRange để kiểm tra toàn vẹn chuẩn**.

<!-- PAGE BREAK -->

# 9. DANH MỤC HÀM TRONG APP.PY

| Hàm | Dòng tham khảo | Chức năng | Gọi hàm/service chính |
| --- | --- | --- | --- |
| `index()` | 33 | Trang chủ, đếm số khóa | `key_manager.list_keys()` |
| `keys()` | 38 | Tạo khóa, lưu ảnh, xem public key | `create_key`, `save_signature_image`, `export_public_key` |
| `delete_key()` | 69 | Xóa khóa và lịch sử liên quan | `delete_key`, `delete_records_for_key` |
| `sign()` | 85 | Điều phối ký text/PDF | `SignatureService`, `PdfSignatureService`, `HistoryService` |
| `verify()` | 183 | Điều phối xác thực JSON/PDF | `verify_text`, `verify_pdf`, `HashService` |
| `history()` | 285 | Hiển thị lịch sử | `get_sign_history`, `get_verify_history` |
| `download_public_key()` | 295 | Tải khóa công khai PEM | `send_file` |
| `key_signature_image()` | 305 | Trả ảnh chữ ký của khóa | `get_signature_image_path` |
| `download_signature()` | 317 | Tải gói JSON đã ký | Kiểm tra đường dẫn trong `storage/signatures` |
| `download_signed_document()` | 327 | Tải PDF đã ký | Kiểm tra đường dẫn trong `storage/signed_documents` |
| `_content_from_form()` | 336 | Lấy text nhập trực tiếp; còn nhánh TXT cũ | `DocumentService.read_text_file` |
| `_signed_text_package_from_form()` | 346 | Parse và validate gói JSON tối đa 5 MB | `json.loads` |
| `_sign_pdf_from_form()` | 387 | Validate PDF, gọi service và lưu PDF | `PdfSignatureService.sign_pdf` |
| `_pdf_placement_from_form()` | 432 | Lấy và giới hạn tọa độ tem | `_int_from_form` |
| `_pdf_signature_image_source_from_form()` | 443 | Lấy ảnh upload hoặc ảnh đã lưu | `get_signature_image_path` |
| `_save_signed_text_package()` | 458 | Lưu nội dung + chữ ký thành JSON | `json.dumps` |
| `_int_from_form()` | 534 | Ép số nguyên và clamp min/max | `int`, `min`, `max` |

## 9.1. Các helper cũ hiện không nằm trong luồng chính

- `_signature_image_config_from_form()`.
- `_image_file_to_data_url()`.
- `_image_path_to_data_url()`.
- `_save_signed_document_file()`.
- Nhánh `method == "file"` trong `_content_from_form()`.

Các hàm này thuộc hướng tạo tài liệu HTML/TXT trước đây. Giao diện hiện chỉ ký text trực tiếp và PDF. Khi trình bày không nên nói chúng đang được người dùng sử dụng.

# 10. DANH MỤC HÀM TRONG SERVICES

## 10.1. KeyManager

| Hàm | Vai trò |
| --- | --- |
| `__init__()` | Khởi tạo thư mục lưu khóa. |
| `create_key()` | Sinh RSA 2048-bit, serialize PEM, lưu metadata. |
| `save_signature_image()` | Kiểm tra loại ảnh và lưu ảnh hiển thị. |
| `list_keys()` | Đọc toàn bộ `metadata.json`. |
| `load_private_key()` | Deserialize khóa riêng PEM để ký. |
| `load_public_key()` | Deserialize khóa công khai PEM để xác thực. |
| `export_public_key()` | Trả nội dung public PEM để hiển thị/tải. |
| `export_private_key()` | Có trong service nhưng không có route tải private key. |
| `get_metadata()` | Đọc metadata một khóa. |
| `get_signature_image_path()` | Tìm ảnh chữ ký đã lưu. |
| `delete_key()` | Xóa thư mục khóa, có kiểm tra đường dẫn. |
| `_normalize_key_id()` | Chỉ giữ chữ ASCII, số, `_`, `-`. |
| `_read_json()`, `_write_json()` | Đọc/ghi JSON UTF-8. |

## 10.2. SignatureService

| Hàm | Vai trò |
| --- | --- |
| `sign_text()` | Ký UTF-8 text bằng RSA PKCS#1 v1.5 và SHA-256. |
| `verify_text()` | Xác thực chữ ký; bắt `InvalidSignature`. |
| `encode_signature()` | bytes sang Base64 ASCII. |
| `decode_signature()` | Validate và decode Base64. |

## 10.3. HashService

| Hàm | Vai trò | Trạng thái sử dụng |
| --- | --- | --- |
| `hash_text()` | SHA-256 text UTF-8 | Đang dùng |
| `hash_file()` | SHA-256 toàn bộ bytes của đường dẫn | Chưa nằm trong route hiện tại |
| `compare_hash()` | So sánh hai chuỗi hash sau strip/lower | Đang dùng khi xác thực JSON |

## 10.4. DocumentService

| Hàm | Vai trò | Trạng thái sử dụng |
| --- | --- | --- |
| `validate_text()` | Từ chối text rỗng | Đang dùng |
| `normalize_text()` | Chuẩn hóa xuống dòng | Đang dùng |
| `read_text_file()` | Đọc TXT UTF-8 BOM | Nhánh giao diện TXT đã ẩn |
| `save_text_file()` | Lưu TXT với tên không trùng | Chưa nằm trong route hiện tại |

## 10.5. PdfSignatureService

| Hàm | Vai trò |
| --- | --- |
| `sign_pdf()` | Băm PDF gốc, ký, ghép tem, ghi metadata. |
| `verify_pdf()` | Xác thực chữ ký của hash trong metadata. |
| `_create_signature_stamp()` | Tạo overlay ReportLab gồm khung, tên, thời gian, ảnh. |

## 10.6. HistoryService

| Hàm | Vai trò |
| --- | --- |
| `save_sign_history()` | Chèn bản ghi ký mới lên đầu. |
| `save_verify_history()` | Chèn bản ghi xác thực mới lên đầu. |
| `get_sign_history()`, `get_verify_history()` | Đọc danh sách JSON. |
| `delete_records_for_key()` | Xóa lịch sử liên quan khi xóa khóa. |
| `_read_records()` | Trả danh sách rỗng nếu file chưa có/JSON hỏng. |
| `_write_records()` | Ghi JSON UTF-8 có thụt lề. |

<!-- PAGE BREAK -->

# 11. GIAO DIỆN VÀ JAVASCRIPT

## 11.1. Template chính

| Template | Chức năng |
| --- | --- |
| `base.html` | Khung HTML, menu, icon, flash message, tải CSS/JS. |
| `index.html` | Trang tổng quan. |
| `keys.html` | Tạo/list/xem/tải/xóa khóa. |
| `sign.html` | Chọn ký text/PDF và nhập dữ liệu. |
| `sign_result.html` | Màn hình ký thành công và nút tải kết quả. |
| `verify.html` | Chọn xác thực JSON/PDF. |
| `verify_result.html` | Màn hình thành công/thất bại và thời gian. |
| `history.html` | Hai bảng lịch sử ký/xác thực. |

## 11.2. main.js

- Xác nhận trước thao tác xóa.
- Chỉ bật nút “Tiếp tục” khi đã chọn phương thức.
- Xem trước ảnh chữ ký từ upload hoặc ảnh gắn với khóa.
- Cấu hình pdf.js worker.
- Render trang PDF lên canvas.
- Cho phép click/drag/resize khung chữ ký.
- Chuyển tọa độ canvas sang hệ tọa độ PDF.
- Ghi `x`, `y`, `w`, `h`, `page` vào input ẩn gửi backend.

JavaScript chỉ phục vụ trải nghiệm và vị trí tem. Chữ ký RSA luôn được thực hiện ở backend, không giao khóa riêng cho trình duyệt.

# 12. DỮ LIỆU LƯU TRỮ

## 12.1. metadata khóa

Gồm `key_id`, `key_name`, `owner_name`, thời gian tạo, thuật toán, kích thước và đường dẫn PEM. Metadata là thông tin quản lý, không phải chứng thư số.

## 12.2. Lịch sử

- `sign_history.json`: tên tài liệu, người ký, khóa, thời gian, hash, đường dẫn kết quả.
- `verify_history.json`: tên tài liệu, khóa, thời gian, kết quả, message, hash.

Lịch sử hiện là JSON file, không có transaction/locking. Nhiều request ghi đồng thời có thể gây race condition trong môi trường production.

## 12.3. Vì sao không lưu khóa trong cơ sở dữ liệu

Dự án demo dùng filesystem để dễ quan sát. Production nên dùng keystore/HSM hoặc dịch vụ quản lý khóa, kiểm soát quyền truy cập và audit.

# 13. KIỂM TRA SỬA ĐỔI

## 13.1. Text

Text phát hiện sửa đổi đúng vì chữ ký RSA gắn với bytes UTF-8 sau chuẩn hóa. Sửa nội dung làm `public_key.verify()` thất bại. Kể cả kẻ sửa tính lại trường `hash`, họ không có khóa riêng để tạo chữ ký mới hợp lệ.

## 13.2. Những thay đổi được chuẩn hóa

Khác biệt `CRLF` và `LF` bị chuẩn hóa nên không được coi là sửa đổi nội dung. Khoảng trắng, chữ hoa/thường, dấu tiếng Việt và ký tự ẩn khác vẫn ảnh hưởng chữ ký.

## 13.3. PDF

Như mục 8, PDF hiện chưa tái băm nội dung đang tải lên, vì vậy chưa bảo đảm phát hiện mọi sửa đổi trang PDF.

# 14. BẢO MẬT VÀ GIỚI HẠN HIỆN TẠI

1. Khóa riêng PEM lưu không mã hóa.
2. Không có đăng nhập, phân quyền hay xác nhận người được phép ký.
3. `SECRET_KEY` Flask đang hard-code.
4. Chưa có CSRF protection.
5. Chưa giới hạn kích thước upload PDF/ảnh ở cấp Flask.
6. JSON lịch sử không có khóa ghi đồng thời.
7. Không có chứng thư X.509/CA/PKI nên danh tính chủ khóa là tự khai.
8. Chưa có thu hồi khóa, hết hạn khóa, timestamp authority.
9. Text dùng PKCS#1 v1.5; thiết kế mới thường ưu tiên RSA-PSS.
10. PDF chưa dùng PAdES/CMS/ByteRange.
11. `owner_name` trong gói JSON/metadata không tự có giá trị chứng minh danh tính.
12. Chưa có bộ test tự động trong repository.

Không nên nói “ứng dụng đã sẵn sàng triển khai thực tế”. Cách nói đúng: “ứng dụng minh họa đầy đủ nguyên lý cho text; một số phần PDF và quản trị khóa cần nâng cấp để production”.

<!-- PAGE BREAK -->

# 15. KỊCH BẢN DEMO TRƯỚC GIẢNG VIÊN

## 15.1. Demo text thành công

1. Tạo khóa `Key_Demo`, chủ sở hữu `Nguyễn Văn A`.
2. Ký nội dung: “Biên bản được thống nhất ngày 20/06/2026.”
3. Tải gói JSON.
4. Sang xác thực văn bản, tải gói vừa tạo.
5. Kết quả: xác thực thành công và có thời gian.

## 15.2. Demo phát hiện sửa đổi

1. Mở bản sao JSON bằng trình soạn thảo.
2. Sửa một chữ trong trường `content`, không thay chữ ký.
3. Tải gói đã sửa lên.
4. Kết quả: xác thực thất bại.
5. Giải thích: SHA-256 thay đổi và RSA không còn khớp; kẻ sửa không có khóa riêng để tạo chữ ký mới.

## 15.3. Demo sai khóa

1. Có thể đổi `key_id` trong bản sao JSON sang một khóa khác.
2. Xác thực thất bại do public key không khớp, hoặc báo không tìm thấy khóa.

## 15.4. Demo PDF

1. Tải PDF, chọn trang và vị trí tem.
2. Ký và tải PDF đầu ra.
3. Xác thực bằng đúng khóa.
4. Khi trình bày phải nói rõ đây là demo metadata RSA/tem; kiểm tra toàn vẹn PDF chưa theo PAdES.

# 16. CÂU HỎI GIẢNG VIÊN VÀ GỢI Ý TRẢ LỜI

## Câu 1. Chữ ký số là gì?

Là dữ liệu mật mã tạo từ nội dung và khóa riêng. Người nhận dùng khóa công khai tương ứng để kiểm tra nguồn gốc và tính toàn vẹn.

## Câu 2. Tại sao không ký trực tiếp bằng ảnh chữ ký?

Ảnh có thể sao chép và không gắn toán học với nội dung. Chữ ký RSA thay đổi theo nội dung và chỉ người có khóa riêng mới tạo được.

## Câu 3. SHA-256 dùng để làm gì?

Tạo digest 256-bit đại diện nội dung. Thay đổi nhỏ làm digest đổi mạnh, giúp phát hiện sửa đổi và cho phép ký dữ liệu kích thước cố định.

## Câu 4. Trong code text có tự băm trước khi ký không?

`private_key.sign(text.encode("utf-8"), ..., hashes.SHA256())` nhận text bytes; thư viện `cryptography` thực hiện SHA-256 bên trong. `HashService.hash_text()` tính thêm hash dạng hex để lưu/hiển thị.

## Câu 5. Tại sao cần khóa riêng và khóa công khai?

Khóa riêng tạo chữ ký và phải bí mật. Khóa công khai chỉ kiểm tra nên có thể phân phối. Đúng public key mới xác thực được chữ ký của private key tương ứng.

## Câu 6. Nếu sửa một ký tự thì sao?

Sau chuẩn hóa, bytes UTF-8 thay đổi, SHA-256 thay đổi và phép `public_key.verify()` thất bại.

## Câu 7. Nếu kẻ tấn công sửa cả nội dung và trường hash?

Họ vẫn không tạo được chữ ký RSA mới nếu không có private key. So sánh hash có thể đúng nhưng RSA sẽ sai; hệ thống yêu cầu cả hai cùng đúng.

## Câu 8. Base64 có bảo mật không?

Không. Base64 chỉ biểu diễn bytes thành text; ai cũng decode được.

## Câu 9. Tên văn bản có tham gia ký không?

Trong gói text hiện tại, phép RSA ký trường `content`, không ký toàn bộ JSON hay `document_name`. Tên dùng cho hiển thị/lịch sử, không nên coi là dữ liệu được bảo vệ độc lập.

## Câu 10. `owner_name` có chứng minh danh tính không?

Không. Nó là metadata tự khai. Muốn chứng minh danh tính pháp lý cần chứng thư X.509 do CA tin cậy cấp và kiểm tra chuỗi PKI.

## Câu 11. Tại sao chuẩn hóa xuống dòng?

Để cùng nội dung trên Windows/Linux không thất bại chỉ vì `CRLF` và `LF`. Chuẩn hóa phải giống nhau ở cả lúc ký và xác thực.

## Câu 12. Vì sao gói JSON tiện hơn nhập thủ công?

Nó đóng gói nội dung, chữ ký, key ID, hash và thuật toán. Người dùng không cần dán Base64/chọn khóa nên giảm lỗi thao tác.

## Câu 13. Có thể xác thực văn bản ký bởi hệ thống khác không?

Chưa trực tiếp. Luồng text yêu cầu định dạng `RSA_SIGNED_TEXT` và khóa công khai phải có trong kho nội bộ. Muốn hỗ trợ ngoài hệ thống cần nhận tài liệu, chữ ký detached và public key/chứng thư, đồng thời thống nhất thuật toán/encoding.

## Câu 14. Vì sao RSA 2048-bit?

Đây là kích thước phổ biến, đủ cho demo và vẫn được dùng rộng rãi. Khóa lớn hơn tăng chi phí tính toán. Chính sách thực tế phải theo tiêu chuẩn tổ chức.

## Câu 15. `65537` là gì?

Là số mũ công khai RSA thường dùng, cân bằng hiệu năng và an toàn khi triển khai đúng.

## Câu 16. PKCS#1 v1.5 và RSA-PSS khác gì?

Dự án dùng padding chữ ký PKCS#1 v1.5 để đơn giản và tương thích. RSA-PSS có tính ngẫu nhiên và thường được khuyến nghị cho thiết kế chữ ký mới.

## Câu 17. Tại sao private key không tải trên giao diện?

Khóa riêng phải được hạn chế tối đa. Dù service có hàm export, ứng dụng không cung cấp route download private key. Tuy nhiên file vẫn chưa mã hóa nên cần bảo vệ hệ điều hành.

## Câu 18. Xóa khóa có ảnh hưởng gì?

`delete_key()` xóa thư mục khóa và `delete_records_for_key()` xóa lịch sử liên quan. Các tài liệu/chữ ký cũ có thể không xác thực được nếu public key cũng bị xóa.

## Câu 19. PDF ký dữ liệu gì?

Code tính SHA-256 của bytes PDF gốc, chuyển digest thành bytes rồi API RSA-SHA256 băm thêm lần nữa để ký. Sau đó mới đóng tem và ghi metadata.

## Câu 20. PDF hiện phát hiện sửa đổi hoàn toàn không?

Không. Verifier xác thực chữ ký của hash nằm trong metadata nhưng chưa tính lại hash từ nội dung PDF hiện tại. Đây là giới hạn đã xác định; hướng đúng là PAdES/CMS với ByteRange.

## Câu 21. Tại sao không tính hash toàn bộ PDF đã ký rồi lưu vào chính PDF?

Nếu đưa chữ ký/hash vào PDF, bytes PDF lại thay đổi, tạo bài toán tự tham chiếu. Chuẩn PDF giải quyết bằng ByteRange: ký các vùng bytes xác định và loại trừ vùng chứa chữ ký.

## Câu 22. Chữ ký số có chống đọc trộm không?

Không. Cần mã hóa nếu muốn bảo mật nội dung.

## Câu 23. Lịch sử có phải bằng chứng chống sửa không?

Không. Lịch sử là JSON thường, có thể bị người có quyền filesystem sửa. Audit production cần append-only log, chữ ký log hoặc hệ thống database/audit chuyên dụng.

## Câu 24. Tại sao dùng Flask?

Flask gọn, dễ tách route/service/template, phù hợp demo học thuật. Thuật toán mật mã nằm ở service nên không phụ thuộc chặt vào giao diện.

## Câu 25. Nếu Base64 hỏng thì sao?

`decode_signature(..., validate=True)` phát hiện ký tự/định dạng sai và phát sinh thông báo chữ ký không đúng Base64.

## Câu 26. Nếu JSON lớn hoặc sai định dạng thì sao?

Hệ thống giới hạn gói text 5 MB, yêu cầu JSON UTF-8, object root, đúng format/version/algorithm và đủ trường bắt buộc.

## Câu 27. Vì sao kết quả xác thực chỉ hiển thị thời gian?

Đây là lựa chọn giao diện đơn giản sau khi người dùng yêu cầu tách màn hình kết quả. Chi tiết message/hash vẫn được lưu trong đối tượng kết quả và lịch sử.

## Câu 28. Cải tiến ưu tiên cao nhất là gì?

Thứ nhất sửa PDF theo PAdES/ByteRange. Thứ hai mã hóa/đưa private key vào keystore và thêm xác thực người dùng. Thứ ba thêm PKI/chứng thư, CSRF, giới hạn upload và test tự động.

<!-- PAGE BREAK -->

# 17. BẢNG GHI NHỚ NHANH

| Câu hỏi | Từ khóa trả lời |
| --- | --- |
| Ký bằng gì? | Private key RSA 2048, PKCS#1 v1.5, SHA-256 |
| Xác thực bằng gì? | Public key tương ứng |
| Phát hiện sửa text? | Chuẩn hóa -> SHA-256 -> RSA verify |
| Base64 là gì? | Biểu diễn bytes, không phải mã hóa |
| Ảnh chữ ký có tác dụng mật mã? | Không, chỉ hiển thị |
| JSON chứa gì? | Content, signature, hash, key ID, metadata |
| Kết quả text hợp lệ khi nào? | Hash đúng AND RSA đúng |
| Danh tính đã được CA xác nhận? | Chưa, chưa có PKI/X.509 |
| PDF đã chuẩn PAdES? | Chưa |
| Hạn chế private key? | PEM không mật khẩu, chưa phân quyền |

# 18. KẾT LUẬN MẪU KHI TRÌNH BÀY

“Dự án của em minh họa quy trình tạo cặp khóa RSA, ký văn bản bằng khóa riêng và xác thực bằng khóa công khai. Với văn bản text, hệ thống chuẩn hóa nội dung, sử dụng SHA-256 và RSA PKCS#1 v1.5, đóng gói nội dung cùng chữ ký vào JSON để giảm sai sót thao tác. Khi xác thực, hệ thống tính lại hash và kiểm tra chữ ký; sửa nội dung hoặc dùng sai khóa đều làm kết quả thất bại. Phần PDF minh họa đóng tem và nhúng metadata RSA, nhưng em đã xác định giới hạn là chưa tái băm nội dung PDF hiện tại; hướng phát triển đúng là PAdES/CMS với ByteRange và chứng thư X.509. Vì vậy phiên bản hiện tại phù hợp demo nguyên lý, đặc biệt đầy đủ ở luồng text, còn cần nâng cấp quản trị khóa, PKI và PDF trước khi triển khai thực tế.”

