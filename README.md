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
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```
* Cài đặt các thư viện cần thiết:
```bash
pip install -r requirements.txt
```
* Tạo tệp `.env` tại thư mục gốc của dự án (cùng cấp với `app.py`) và điền các thông số kết nối thực tế:
```env
SECRET_KEY=labtrack_super_secret_key_2026

DB_HOST=your-service.aivencloud.com
DB_PORT=12345
DB_USER=avnadmin
DB_PASSWORD=your_aiven_password
DB_NAME=defaultdb

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
* **Bước 3:** Mở trình duyệt và truy cập địa chỉ `http://127.0.0.1:5000`. Đăng nhập bằng tài khoản Admin mặc định (`admin@labtrack.edu.vn` / `admin123`) hoặc đăng ký tài khoản Thành viên mới tại `/register`.
* *(Tùy chọn)* Khi triển khai online lên **Render.com**, cấu hình Build Command là `pip install -r requirements.txt`, Start Command là `gunicorn app:app` và nhập toàn bộ biến từ tệp `.env` vào mục **Environment Variables**.

## Help

Một số lỗi thường gặp và cách xử lý nhanh:

* **Sửa tệp `.env` nhưng ứng dụng chưa nhận cấu hình mới:** Tắt hoàn toàn server bằng `Ctrl + C` trong Terminal và chạy lại lệnh `python app.py`.
* **Lỗi `UndefinedError: 'None' has no attribute 'full_name'` sau khi đổi cơ sở dữ liệu:** Trình duyệt còn lưu phiên đăng nhập cũ; truy cập đường dẫn `/logout` để xóa session và đăng nhập lại.
* **Kiểm tra nhanh kết nối và biến môi trường từ tệp `.env`:**
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(override=True); print('DB_HOST:', os.getenv('DB_HOST'))"
```

## Authors

* **Nhóm phát triển LabTrack** — Hệ thống Quản lý Phòng Thí Nghiệm
* Email quản trị mặc định: `admin@labtrack.edu.vn`

## Version History

* 0.3
    * Tích hợp đồng bộ chuẩn mã hóa tiếng Việt (`utf8mb4`) và thiết bị mặc định trực tiếp vào `app.py`.
    * Bổ sung tính năng quản lý xóa dữ liệu sinh viên, xóa thiết bị và phân quyền `Admin`/`Member` ngay trên giao diện Dashboard.
    * Hoàn thiện cấu hình `Procfile` và `gunicorn` để triển khai trực tuyến trên Render.
* 0.2
    * Chuyển đổi cơ sở dữ liệu từ MySQL nội bộ sang **Aiven Cloud MySQL** và đồng bộ múi giờ `UTC+7`.
    * Tối ưu hóa quy trình tải lên/tải xuống tệp báo cáo (`.PDF`, `.DOCX`, `.ZIP`) trên Cloudinary bằng cơ chế proxy giữ nguyên tên gốc.
* 0.1
    * Phiên bản khởi tạo đầu tiên với đầy đủ 5 phân hệ chức năng trên nền tảng Flask + MySQL + Cloudinary.

## License

Dự án được phát hành phục vụ mục đích học tập và quản lý nội bộ phòng thí nghiệm theo giấy phép MIT License.

## Acknowledgments

* [Flask Documentation](https://flask.palletsprojects.com/)
* [TailwindCSS](https://tailwindcss.com/)
* [Cloudinary Python SDK](https://cloudinary.com/documentation/django_integration)
* [Aiven Cloud MySQL](https://aiven.io/mysql)
* [DomPizzie README Template](https://gist.github.com/DomPizzie/7a5ff55ffa9081f2de27c315f5018afc)