# Ban do chuc nang du an chu ky so RSA

## 1. Diem vao va giao dien

| Tep | Chuc nang |
| --- | --- |
| `app.py` | Diem vao Flask, nhan request, goi cac service va tra ve giao dien. |
| `templates/index.html` | Trang tong quan va cac loi tat. |
| `templates/keys.html` | Tao, liet ke, xem, tai va xoa khoa. |
| `templates/sign.html` | Chon cach ky text/PDF, nhap du lieu va hien thi ket qua. |
| `templates/verify.html` | Xac thuc text nhap truc tiep hoac PDF. |
| `templates/history.html` | Xem lich su ky va xac thuc. |
| `templates/base.html` | Khung giao dien, menu, thong bao va tai tai nguyen chung. |
| `static/js/main.js` | Xem truoc anh, chon phuong thuc, dat/doi kich thuoc tem PDF. |
| `static/css/style.css` | Trinh bay giao dien. |

## 2. Cac service nghiep vu

| Tep | Ham/chuc nang chinh | Phan loai |
| --- | --- | --- |
| `services/key_manager.py` | `create_key`, `load_private_key`, `load_public_key`, `list_keys`, `delete_key` | Quan ly cap khoa RSA 2048-bit. |
| `services/signature_service.py` | `sign_text`, `verify_text` | Ky/xac thuc text bang RSA PKCS#1 v1.5 va SHA-256. |
| `services/hash_service.py` | `hash_text`, `hash_file`, `compare_hash` | Bam va so sanh SHA-256. |
| `services/document_service.py` | `read_text_file`, `validate_text`, `normalize_text` | Doc va chuan hoa van ban TXT UTF-8. |
| `services/pdf_signature_service.py` | `sign_pdf`, `verify_pdf`, `_create_signature_stamp` | Dong tem, luu metadata va xac thuc chu ky PDF. |
| `services/history_service.py` | `save_*_history`, `get_*_history`, `delete_records_for_key` | Quan ly lich su JSON. |

## 3. Luong chuc nang

### Tao khoa

`POST /keys` -> `KeyManager.create_key()` -> luu `private_key.pem`,
`public_key.pem`, `metadata.json` va anh chu ky tuy chon trong `storage/keys`.

### Ky van ban text

`POST /sign?method=text` -> chuan hoa text -> nap khoa rieng ->
`SignatureService.sign_text()` -> luu mot goi JSON gom noi dung, chu ky,
hash, khoa va thong tin nguoi ky -> ghi lich su.

### Xac thuc text

`POST /verify?method=text` -> tai goi JSON da ky -> tu dong doc noi dung, chu ky
va `key_id` -> tinh lai SHA-256 -> nap khoa cong khai ->
`SignatureService.verify_text()` -> thong bao hop le/khong hop le -> ghi lich su.
Nguoi dung khong phai nhap lai noi dung, dan Base64 hoac chon khoa thu cong.

### Ky PDF

`POST /sign?method=pdf` -> bam PDF goc -> ky hash -> dong tem len trang da chon ->
nhung chu ky/hash/thong tin nguoi ky vao metadata -> luu PDF da ky.

### Xac thuc PDF

`POST /verify?method=pdf` -> doc chu ky va hash trong metadata -> dung khoa cong
khai de xac thuc chu ky cua hash do.

## 4. Danh gia muc do dap ung de tai

### Da co

- Tao va quan ly cap khoa RSA 2048-bit.
- Ky noi dung text bang khoa rieng; xac thuc bang khoa cong khai.
- Su dung SHA-256 va hien thi hash de minh hoa tinh toan ven.
- Phat hien text bi sua, chu ky sai hoac chon sai khoa.
- Ho tro text nhap truc tiep, PDF, anh chu ky hien thi va lich su thao tac.
- Co the demo day du luong: tao khoa -> ky -> sua text -> xac thuc that bai.

### Chua day du hoac can sua

1. **Kiem tra sua doi PDF chua dung.** `verify_pdf()` chi xac thuc hash lay tu
   metadata, khong tinh lai hash tu noi dung PDF hien tai. Neu trang PDF bi sua ma
   metadata van con, he thong van co the bao hop le.
2. **Khoa rieng luu khong ma hoa.** `private_key.pem` dung `NoEncryption()` va
   ung dung khong co dang nhap/phan quyen. Phu hop demo cuc bo, khong phu hop
   trien khai thuc te.
3. **Chua co chung thu so/PKI.** Ten nguoi ky la metadata tu khai; he thong chi
   chung minh chu ky khop voi khoa duoc chon, chua chung minh danh tinh phap ly.
4. **Thuat toan ky dang dung PKCS#1 v1.5.** Hoat dong dung cho demo, nhung RSA-PSS
   la lua chon nen uu tien cho thiet ke moi.
5. **Chua co kiem thu tu dong.** Can test cho ky/xac thuc dung, sua noi dung, sai
   khoa, chu ky Base64 hong, PDF bi sua va metadata bi sua.
6. **Bao mat web con o muc demo.** `SECRET_KEY` hard-code, khong CSRF, khong gioi
   han kich thuoc upload va du lieu JSON khong co co che khoa khi ghi dong thoi.
7. **Mot so ma chua duoc su dung.** `_save_signed_document_file()`, cac helper anh
   HTML, `DocumentService.save_text_file()`, `HashService.hash_file()` va
   `compare_hash()` khong nam trong luong giao dien hien tai.

## 5. Ket luan

Du an **du de trinh bay nguyen ly chu ky so RSA va demo phat hien sua doi doi voi
text/TXT**. Du an **chua day du neu bao cao khang dinh phat hien sua doi cho ca
PDF**, va chua du tieu chuan de trien khai thuc te. Uu tien cao nhat la thiet ke
lai dinh dang ky PDF de verifier co the tinh lai mot gia tri dai dien cho noi dung
hien tai, sau do so sanh/xac thuc gia tri nay bang chu ky RSA.
