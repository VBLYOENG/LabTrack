CREATE DATABASE IF NOT EXISTS labtrack_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE labtrack_db;

-- 1. Bảng người dùng (Phân quyền member / admin)
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    student_id VARCHAR(20) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('member', 'admin') DEFAULT 'member',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Bảng đăng ký ca làm việc tại Lab (Sáng 07:00-11:45, Chiều 13:00-16:50)
CREATE TABLE shift_registrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    shift_date DATE NOT NULL,
    shift_type ENUM('morning', 'afternoon') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_shift (user_id, shift_date, shift_type),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Bảng lịch & điểm danh trực nhật theo ngày
CREATE TABLE duty_schedules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    duty_date DATE NOT NULL,
    shift_type ENUM('morning', 'afternoon') NOT NULL,
    task_desc VARCHAR(255) DEFAULT 'Dọn dẹp bàn kỹ thuật & Quét dọn phòng lab',
    proof_url TEXT NULL,
    is_approved TINYINT(1) DEFAULT 0,
    submitted_at DATETIME NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Bảng báo cáo tiến độ hàng tuần
CREATE TABLE weekly_reports (
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
);

-- 5. Bảng danh mục thiết bị trong kho
CREATE TABLE equipment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    total_qty INT NOT NULL DEFAULT 1,
    available_qty INT NOT NULL DEFAULT 1,
    status ENUM('ready', 'maintenance') DEFAULT 'ready'
);

-- 6. Bảng phiếu mượn / trả thiết bị
CREATE TABLE borrow_requests (
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
);

-- 7. Bảng thông báo hoạt động cập nhật lên Tổng quan
CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL, -- NULL nếu gửi cho toàn hệ thống/admin, hoặc ID user cụ thể
    message VARCHAR(255) NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dữ liệu mẫu thiết bị
INSERT INTO equipment (code, name, total_qty, available_qty, status) VALUES
('EQ-OSC-01', 'Máy hiện sóng Oscilloscope Tektronix', 5, 3, 'ready'),
('EQ-PWR-04', 'Bộ nguồn DC đa năng Korad', 8, 6, 'ready'),
('EQ-SIG-02', 'Máy phát hàm Signal Generator', 4, 0, 'maintenance'),
('EQ-SOL-09', 'Mỏ hàn nhiệt Weller WESD51', 12, 10, 'ready');