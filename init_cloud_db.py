import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv(override=True)

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    charset="utf8mb4"
)
cur = conn.cursor()

tables = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        full_name VARCHAR(100) NOT NULL,
        email VARCHAR(100) NOT NULL UNIQUE,
        student_id VARCHAR(20) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role ENUM('member', 'admin') DEFAULT 'member',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS shift_registrations (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        shift_date DATE NOT NULL,
        shift_type ENUM('morning', 'afternoon') NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_user_shift (user_id, shift_date, shift_type),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS duty_schedules (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        duty_date DATE NOT NULL,
        shift_type ENUM('morning', 'afternoon') NOT NULL,
        task_desc VARCHAR(255) DEFAULT 'Dọn dẹp bàn kỹ thuật & Quét dọn phòng lab',
        proof_url TEXT NULL,
        is_approved TINYINT(1) DEFAULT 0,
        submitted_at DATETIME NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS weekly_reports (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        week_number INT NOT NULL,
        year INT NOT NULL,
        file_name VARCHAR(255) NOT NULL,
        file_url TEXT NOT NULL,
        note TEXT,
        score FLOAT NULL,
        feedback TEXT NULL,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS equipment (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(30) NOT NULL UNIQUE,
        name VARCHAR(150) NOT NULL,
        total_qty INT NOT NULL DEFAULT 1,
        available_qty INT NOT NULL DEFAULT 1,
        status ENUM('ready', 'maintenance') DEFAULT 'ready'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS borrow_requests (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        equipment_id INT NOT NULL,
        quantity INT NOT NULL DEFAULT 1,
        borrow_date DATE NOT NULL,
        due_date DATE NOT NULL,
        return_date DATE NULL,
        status ENUM('pending', 'borrowing', 'returned') DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NULL,
        message VARCHAR(255) NOT NULL,
        is_read TINYINT(1) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
]

for sql in tables:
    cur.execute(sql)

# Thêm 4 thiết bị mẫu nếu bảng equipment đang trống
cur.execute("SELECT COUNT(*) FROM equipment")
if cur.fetchone()[0] == 0:
    cur.executemany(
        "INSERT INTO equipment (code, name, total_qty, available_qty, status) VALUES (%s, %s, %s, %s, %s)",
        [
            ("EQ-OSC-01", "Máy hiện sóng Oscilloscope Tektronix", 5, 3, "ready"),
            ("EQ-PWR-04", "Bộ nguồn DC đa năng Korad", 8, 6, "ready"),
            ("EQ-SIG-02", "Máy phát hàm Signal Generator", 4, 0, "maintenance"),
            ("EQ-SOL-09", "Mỏ hàn nhiệt Weller WESD51", 12, 10, "ready")
        ]
    )

# Tạo tài khoản Admin mặc định nếu chưa có
cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
if not cur.fetchone():
    cur.execute(
        "INSERT INTO users (full_name, email, student_id, password_hash, role) VALUES (%s, %s, %s, %s, 'admin')",
        ("Quản Trị Viên Lab", "admin@labtrack.edu.vn", "ADMIN001", generate_password_hash("admin123"))
    )

conn.commit()
cur.close()
conn.close()
print("Đã khởi tạo đầy đủ 7 bảng và dữ liệu mẫu trên Aiven Cloud thành công!")