# LabTrack

Hệ thống web quản lý hoạt động phòng thí nghiệm (Lab), hỗ trợ đăng ký ca làm việc, điểm danh trực nhật bằng hình ảnh, nộp/chấm điểm báo cáo tuần và quản lý mượn trả thiết bị theo thời gian thực.

## Description

**LabTrack** được xây dựng nhằm số hóa và đồng bộ hóa toàn bộ quy trình vận hành tại phòng thí nghiệm cho cả Thành viên (`Member`) và Quản trị viên (`Admin`). Hệ thống sử dụng **Python Flask** cho backend, **Aiven Cloud MySQL** để đồng bộ dữ liệu tập trung trên nhiều thiết bị theo múi giờ Việt Nam (`UTC+7`), và **Cloudinary API** để lưu trữ hình ảnh minh chứng trực nhật cũng như tệp báo cáo (`.PDF`, `.DOCX`, `.ZIP`) mà vẫn giữ nguyên định dạng gốc khi tải về. Ngoài ra, hệ thống còn tích hợp phân quyền trực tiếp trên giao diện web giúp Ban quản trị dễ dàng cấp hoặc thu hồi quyền điều hành mà không cần can thiệp vào mã nguồn.

## Getting Started

### Dependencies

* Hệ điều hành: Windows 10/11, macOS hoặc Linux (có kết nối Internet).
* Python 3.10 trở lên.
* Tài khoản dịch vụ **Aiven Cloud MySQL** (đang ở trạng thái `Running`).
* Tài khoản **Cloudinary** (Cloud Name, API Key, API Secret).
* Các thư viện Python (liệt kê trong `requirements.txt`): `Flask`, `mysql-connector-python`, `cloudinary`, `python-dotenv`, `gunicorn`, `Werkzeug`.

### Installing

* Clone mã nguồn dự án từ GitHub về máy hoặc giải nén thư mục dự án:
```bash
git clone https://github.com/VBLYOENG/LabTrack
cd <your-repo>
```
* Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```
* Tạo tệp `.env` tại thư mục gốc của dự án (cùng cấp với `app.py`) và điền các thông số kết nối thực tế:
```env
SECRET_KEY=labtrack_super_secret_key_2026
# Dùng tài khoản Cloudaiven
DB_HOST=your-service.aivencloud.com
DB_PORT=
DB_USER=
DB_PASSWORD=your_aiven_password
DB_NAME=
# Dùng tài khoản Cloundinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

### Executing program

* **Bước 1:** Khởi tạo cấu trúc 7 bảng cơ sở dữ liệu, thiết bị mẫu và tài khoản Admin mặc định trên Aiven Cloud (chỉ chạy **1 lần duy nhất** khi thiết lập database mới):
```bash
python init_cloud_db.py
```
* **Bước 2:** Khởi chạy máy chủ web Flask:
```bash
python app.py
```
* **Bước 3:** Mở trình duyệt và truy cập địa chỉ `http://127.0.0.1:5000`.

## Help

Một số lỗi thường gặp và cách xử lý nhanh:

* **Sửa tệp `.env` nhưng ứng dụng chưa nhận cấu hình mới:** Tắt hoàn toàn server bằng `Ctrl + C` trong Terminal và chạy lại lệnh `python app.py`.
* **Lỗi `UndefinedError: 'None' has no attribute 'full_name'` sau khi đổi cơ sở dữ liệu:** Trình duyệt còn lưu phiên đăng nhập cũ; truy cập đường dẫn `/logout` để xóa session và đăng nhập lại.
* **Kiểm tra nhanh kết nối và biến môi trường từ tệp `.env`:**
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(override=True); print('DB_HOST:', os.getenv('DB_HOST'))"
```

## Acknowledgments

* [Flask Documentation](https://flask.palletsprojects.com/)
* [TailwindCSS](https://tailwindcss.com/)
* [Cloudinary Python SDK](https://cloudinary.com/documentation/django_integration)
* [Aiven Cloud MySQL](https://aiven.io/mysql)
* [DomPizzie README Template](https://gist.github.com/DomPizzie/7a5ff55ffa9081f2de27c315f5018afc)
