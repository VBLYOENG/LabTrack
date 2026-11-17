import os
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import urllib.request
from io import BytesIO
from flask import send_file
from werkzeug.utils import secure_filename
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "labtrack_secret_2026")

# Cấu hình Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

MAX_SHIFT_CAPACITY = 10  # Sức chứa tối đa mỗi ca làm việc


def get_db():
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4"
    )
    cur = conn.cursor()
    cur.execute("SET NAMES utf8mb4")
    cur.execute("SET time_zone = '+07:00'")
    cur.close()
    return conn
def init_default_admin():
    """Tạo sẵn 1 tài khoản Admin mặc định nếu chưa có trong DB"""
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
        if not cur.fetchone():
            pw_hash = generate_password_hash("admin123")
            cur.execute(
                "INSERT INTO users (full_name, email, student_id, password_hash, role) VALUES (%s, %s, %s, %s, 'admin')",
                ("Quản Trị Viên Lab", "admin@labtrack.edu.vn", "ADMIN001", pw_hash)
            )
            conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("DB Init Warning:", e)


def push_notification(cur, user_id, message):
    """Lưu thông báo mới để hiển thị ở Chuông thông báo & trang Tổng quan"""
    cur.execute(
        "INSERT INTO notifications (user_id, message) VALUES (%s, %s)",
        (user_id, message)
    )


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE id = %s", (session["user_id"],))
        exists = cur.fetchone()
        cur.close()
        conn.close()
        if not exists:
            session.clear()
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Bạn không có quyền thực hiện thao tác quản trị!", "error")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated


@app.context_processor
def inject_global_data():
    """Tự động truyền thông tin User & Thông báo vào mọi trang HTML"""
    if "user_id" not in session:
        return {}
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    current_user = cur.fetchone()

    if current_user and current_user["role"] == "admin":
        cur.execute("SELECT * FROM notifications ORDER BY created_at DESC LIMIT 8")
    else:
        cur.execute(
            "SELECT * FROM notifications WHERE user_id = %s OR user_id IS NULL ORDER BY created_at DESC LIMIT 8",
            (session["user_id"],)
        )
    notifications = cur.fetchall()
    unread_count = sum(1 for n in notifications if not n["is_read"])
    cur.close()
    conn.close()
    return {
        "current_user": current_user,
        "notifications": notifications,
        "unread_count": unread_count
    }


# ==================== PHẦN 1: ĐĂNG NHẬP & ĐĂNG KÝ ====================

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "")

        if not all([full_name, email, student_id, password]):
            flash("Vui lòng nhập đầy đủ 4 thông tin đăng ký!", "error")
            return render_template("register.html")

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM users WHERE email = %s OR student_id = %s", (email, student_id))
        if cur.fetchone():
            flash("Email hoặc Mã số sinh viên đã tồn tại!", "error")
            cur.close()
            conn.close()
            return render_template("register.html")

        pw_hash = generate_password_hash(password)
        # Tự động phân quyền là member khi đăng ký
        cur.execute(
            "INSERT INTO users (full_name, email, student_id, password_hash, role) VALUES (%s, %s, %s, %s, 'member')",
            (full_name, email, student_id, pw_hash)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Đăng ký thành công! Vui lòng đăng nhập.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        flash("Sai email hoặc mật khẩu!", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/notifications/read", methods=["POST"])
@login_required
def mark_notifications_read():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read = 1 WHERE user_id = %s OR user_id IS NULL", (session["user_id"],))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "ok"})


# ==================== PHẦN 2: TỔNG QUAN (DASHBOARD) ====================

@app.route("/")
@login_required
def dashboard():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    uid = session["user_id"]
    today = date.today()
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=6)
    current_week = today.isocalendar()[1]
    current_year = today.isocalendar()[0]

    # 1. Ca làm việc tuần này của user
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM shift_registrations WHERE user_id = %s AND shift_date BETWEEN %s AND %s",
        (uid, start_week, end_week)
    )
    weekly_shifts_count = cur.fetchone()["cnt"]

    # 2. Trực nhật sắp tới / hôm nay
    cur.execute(
        "SELECT * FROM duty_schedules WHERE user_id = %s AND duty_date >= %s ORDER BY duty_date ASC, shift_type ASC LIMIT 1",
        (uid, today)
    )
    upcoming_duty = cur.fetchone()

    # 3. Báo cáo tuần hiện tại
    cur.execute(
        "SELECT * FROM weekly_reports WHERE user_id = %s AND week_number = %s AND year = %s LIMIT 1",
        (uid, current_week, current_year)
    )
    current_report = cur.fetchone()

    # 4. Dụng cụ đang giữ (đang mượn hoặc quá hạn)
    cur.execute("""
        SELECT br.*, eq.name AS equipment_name
        FROM borrow_requests br
        JOIN equipment eq ON br.equipment_id = eq.id
        WHERE br.user_id = %s AND br.status = 'borrowing'
        ORDER BY br.due_date ASC
    """, (uid,))
    borrowed_items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        today=today,
        current_week=current_week,
        weekly_shifts_count=weekly_shifts_count,
        upcoming_duty=upcoming_duty,
        current_report=current_report,
        borrowed_items=borrowed_items
    )


# ==================== PHẦN 3: ĐĂNG KÝ LỊCH LÊN LAB ====================

@app.route("/shifts")
@login_required
def shifts():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    today = date.today()
    start_week = today - timedelta(days=today.weekday())
    end_week = start_week + timedelta(days=5)  # Thứ 2 -> Thứ 7
    week_num = today.isocalendar()[1]

    cur.execute(
        "SELECT shift_date, shift_type, user_id FROM shift_registrations WHERE shift_date BETWEEN %s AND %s",
        (start_week, end_week)
    )
    regs = cur.fetchall()
    cur.close()
    conn.close()

    # Tổng hợp dữ liệu từng ca (Sáng: 07:00-11:45, Chiều: 13:00-16:50)
    days_vn = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"]
    shift_cards = []
    for i in range(6):
        d = start_week + timedelta(days=i)
        for stype, label, time_range in [
            ("morning", "Sáng", "07:00 - 11:45"),
            ("afternoon", "Chiều", "13:00 - 16:50")
        ]:
            matched = [r for r in regs if r["shift_date"] == d and r["shift_type"] == stype]
            count = len(matched)
            is_registered = any(r["user_id"] == session["user_id"] for r in matched)
            shift_cards.append({
                "date_str": d.strftime("%Y-%m-%d"),
                "day_name": days_vn[i],
                "shift_type": stype,
                "label": label,
                "time_range": time_range,
                "count": count,
                "max": MAX_SHIFT_CAPACITY,
                "is_registered": is_registered,
                "is_full": count >= MAX_SHIFT_CAPACITY
            })

    return render_template(
        "shifts.html",
        shift_cards=shift_cards,
        week_num=week_num,
        start_week=start_week.strftime("%d/%m"),
        end_week=(start_week + timedelta(days=6)).strftime("%d/%m")
    )


@app.route("/api/shifts/toggle", methods=["POST"])
@login_required
def toggle_shift():
    data = request.get_json()
    shift_date = data.get("shift_date")
    shift_type = data.get("shift_type")
    uid = session["user_id"]

    conn = get_db()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        "SELECT id FROM shift_registrations WHERE user_id = %s AND shift_date = %s AND shift_type = %s",
        (uid, shift_date, shift_type)
    )
    existing = cur.fetchone()

    shift_label = "Sáng (07:00-11:45)" if shift_type == "morning" else "Chiều (13:00-16:50)"

    if existing:
        # Hủy đăng ký ca này
        cur.execute("DELETE FROM shift_registrations WHERE id = %s", (existing["id"],))
        push_notification(cur, uid, f"Bạn đã hủy đăng ký ca {shift_label} ngày {shift_date}.")
        action = "cancelled"
    else:
        # Kiểm tra sức chứa ca trước khi đăng ký
        cur.execute(
            "SELECT COUNT(*) AS cnt FROM shift_registrations WHERE shift_date = %s AND shift_type = %s",
            (shift_date, shift_type)
        )
        cnt = cur.fetchone()["cnt"]
        if cnt >= MAX_SHIFT_CAPACITY:
            cur.close()
            conn.close()
            return jsonify({"status": "full", "count": cnt, "max": MAX_SHIFT_CAPACITY}), 400

        cur.execute(
            "INSERT INTO shift_registrations (user_id, shift_date, shift_type) VALUES (%s, %s, %s)",
            (uid, shift_date, shift_type)
        )
        push_notification(cur, uid, f"Bạn đã đăng ký thành công ca {shift_label} ngày {shift_date}.")
        action = "registered"

    cur.execute(
        "SELECT COUNT(*) AS cnt FROM shift_registrations WHERE shift_date = %s AND shift_type = %s",
        (shift_date, shift_type)
    )
    new_count = cur.fetchone()["cnt"]
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "status": "ok",
        "action": action,
        "count": new_count,
        "max": MAX_SHIFT_CAPACITY
    })


# ==================== PHẦN 4: ĐIỂM DANH TRỰC NHẬT THEO NGÀY ====================

@app.route("/duty")
@login_required
def duty():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    today = date.today()
    uid = session["user_id"]

    # Ca trực hôm nay của user hiện tại
    cur.execute(
        "SELECT * FROM duty_schedules WHERE user_id = %s AND duty_date = %s LIMIT 1",
        (uid, today)
    )
    today_duty = cur.fetchone()

    # Toàn bộ danh sách trực nhật
    cur.execute("""
        SELECT ds.*, u.full_name, u.student_id
        FROM duty_schedules ds
        JOIN users u ON ds.user_id = u.id
        ORDER BY ds.duty_date DESC, ds.id DESC
    """)
    schedules = cur.fetchall()

    # Tính trạng thái động theo quy tắc:
    # - Đã nộp minh chứng -> 'Hoàn thành'
    # - Qua ngày hôm đó chưa nộp minh chứng -> 'Bỏ trực'
    # - Chưa đến ngày / hôm nay chưa nộp -> 'Chờ làm'
    for item in schedules:
        if item["proof_url"]:
            item["computed_status"] = "completed"
        elif item["duty_date"] < today:
            item["computed_status"] = "missed"
        else:
            item["computed_status"] = "pending"

    members = []
    if session.get("role") == "admin":
        cur.execute("SELECT id, full_name, student_id FROM users ORDER BY full_name ASC")
        members = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "duty.html",
        today=today,
        today_duty=today_duty,
        schedules=schedules,
        members=members
    )


@app.route("/duty/submit", methods=["POST"])
@login_required
def submit_duty_proof():
    duty_id = request.form.get("duty_id")
    file = request.files.get("proof_image")

    if not duty_id or not file or file.filename == "":
        flash("Vui lòng chọn ảnh minh chứng vệ sinh trước khi điểm danh!", "error")
        return redirect(url_for("duty"))

    try:
        upload_res = cloudinary.uploader.upload(file, folder="labtrack/duty_proofs")
        proof_url = upload_res.get("secure_url")
    except Exception as e:
        flash(f"Lỗi tải ảnh lên Cloudinary: {e}", "error")
        return redirect(url_for("duty"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "UPDATE duty_schedules SET proof_url = %s, submitted_at = NOW() WHERE id = %s AND user_id = %s",
        (proof_url, duty_id, session["user_id"])
    )
    push_notification(cur, session["user_id"], "Bạn đã nộp ảnh minh chứng điểm danh trực nhật hôm nay.")
    conn.commit()
    cur.close()
    conn.close()

    flash("Điểm danh trực nhật thành công! Ảnh minh chứng đã lưu trên Cloudinary.", "success")
    return redirect(url_for("duty"))


@app.route("/duty/add", methods=["POST"])
@admin_required
def add_duty_schedule():
    user_id = request.form.get("user_id")
    duty_date = request.form.get("duty_date")
    shift_type = request.form.get("shift_type")

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "INSERT INTO duty_schedules (user_id, duty_date, shift_type) VALUES (%s, %s, %s)",
        (user_id, duty_date, shift_type)
    )
    shift_vn = "Sáng" if shift_type == "morning" else "Chiều"
    push_notification(cur, user_id, f"Admin đã phân công bạn trực nhật ca {shift_vn} ngày {duty_date}.")
    conn.commit()
    cur.close()
    conn.close()

    flash("Đã thêm lịch trực nhật mới!", "success")
    return redirect(url_for("duty"))


@app.route("/duty/approve/<int:duty_id>", methods=["POST"])
@admin_required
def approve_duty(duty_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, duty_date FROM duty_schedules WHERE id = %s", (duty_id,))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE duty_schedules SET is_approved = 1 WHERE id = %s", (duty_id,))
        push_notification(cur, row["user_id"], f"Admin đã duyệt minh chứng trực nhật ngày {row['duty_date']}.")
        conn.commit()
    cur.close()
    conn.close()
    flash("Đã duyệt minh chứng trực nhật!", "success")
    return redirect(url_for("duty"))


# ==================== PHẦN 5: NỘP BÁO CÁO TUẦN ====================

@app.route("/reports")
@login_required
def reports():
    today = date.today()
    curr_year, curr_week, _ = today.isocalendar()
    next_day = today + timedelta(days=7)
    next_year, next_week, _ = next_day.isocalendar()

    week_options = [
        {"week": curr_week, "year": curr_year, "label": f"Tuần {curr_week} (Hiện tại - {curr_year})"},
        {"week": next_week, "year": next_year, "label": f"Tuần {next_week} (Tuần kế tiếp - {next_year})"}
    ]

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    if session.get("role") == "admin":
        # Admin xem tất cả báo cáo của thành viên
        cur.execute("""
            SELECT wr.*, u.full_name, u.student_id
            FROM weekly_reports wr
            JOIN users u ON wr.user_id = u.id
            ORDER BY wr.submitted_at DESC
        """)
    else:
        # Member chỉ xem báo cáo của chính mình
        cur.execute("""
            SELECT wr.*, u.full_name, u.student_id
            FROM weekly_reports wr
            JOIN users u ON wr.user_id = u.id
            WHERE wr.user_id = %s
            ORDER BY wr.submitted_at DESC
        """, (session["user_id"],))
    report_list = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("reports.html", week_options=week_options, report_list=report_list)


@app.route("/reports/submit", methods=["POST"])
@login_required
def submit_report():
    week_val = request.form.get("week_select", "")
    note = request.form.get("note", "").strip()
    file = request.files.get("report_file")

    if not week_val or not file or file.filename == "":
        flash("Vui lòng chọn tuần và tệp báo cáo (.PDF, .DOCX, .ZIP)!", "error")
        return redirect(url_for("reports"))

    original_name = file.filename
    ext = os.path.splitext(original_name)[1].lower()
    if ext not in [".pdf", ".docx", ".zip"]:
        flash("Chỉ chấp nhận định dạng .PDF, .DOCX hoặc .ZIP!", "error")
        return redirect(url_for("reports"))

    week_num, year_num = map(int, week_val.split("-"))

    # Tạo public_id giữ nguyên đuôi mở rộng (.pdf / .docx / .zip) trên Cloudinary
    safe_base = secure_filename(os.path.splitext(original_name)[0]) or "report"
    custom_public_id = f"{safe_base}_{int(datetime.now().timestamp())}{ext}"

    try:
        # Dùng resource_type="raw" cho .docx/.zip để giữ nguyên định dạng gốc, "auto" cho .pdf
        res_type = "auto" if ext == ".pdf" else "raw"
        upload_res = cloudinary.uploader.upload(
            file,
            folder="labtrack/weekly_reports",
            resource_type=res_type,
            public_id=custom_public_id
        )
        file_url = upload_res.get("secure_url")
    except Exception as e:
        flash(f"Lỗi upload Cloudinary: {e}", "error")
        return redirect(url_for("reports"))

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "INSERT INTO weekly_reports (user_id, week_number, year, file_name, file_url, note) VALUES (%s, %s, %s, %s, %s, %s)",
        (session["user_id"], week_num, year_num, original_name, file_url, note)
    )
    push_notification(cur, session["user_id"], f"Bạn đã nộp báo cáo Tuần {week_num} ({original_name}).")
    conn.commit()
    cur.close()
    conn.close()

    flash("Nộp báo cáo tuần thành công!", "success")
    return redirect(url_for("reports"))

@app.route("/reports/download/<int:report_id>")
@login_required
def download_report(report_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT file_name, file_url FROM weekly_reports WHERE id = %s", (report_id,))
    rep = cur.fetchone()
    cur.close()
    conn.close()

    if not rep:
        flash("Không tìm thấy tệp báo cáo!", "error")
        return redirect(url_for("reports"))

    # Tải dữ liệu từ Cloudinary và trả về trình duyệt với đúng tên file & đuôi gốc
    req = urllib.request.urlopen(rep["file_url"])
    file_data = BytesIO(req.read())
    return send_file(
        file_data,
        as_attachment=True,
        download_name=rep["file_name"]
    )

@app.route("/reports/grade/<int:report_id>", methods=["POST"])
@admin_required
def grade_report(report_id):
    score = request.form.get("score")
    feedback = request.form.get("feedback", "").strip()

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT user_id, week_number FROM weekly_reports WHERE id = %s", (report_id,))
    rep = cur.fetchone()
    if rep:
        cur.execute(
            "UPDATE weekly_reports SET score = %s, feedback = %s WHERE id = %s",
            (score, feedback, report_id)
        )
        push_notification(cur, rep["user_id"], f"Admin đã chấm điểm báo cáo Tuần {rep['week_number']}: {score}/10.")
        conn.commit()
    cur.close()
    conn.close()

    flash("Đã lưu điểm và nhận xét báo cáo!", "success")
    return redirect(url_for("reports"))


# ==================== PHẦN 6: QUẢN LÝ MƯỢN / TRẢ DỤNG CỤ ====================

@app.route("/equipment")
@login_required
def equipment():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    today = date.today()

    # Danh mục thiết bị trong kho
    cur.execute("SELECT * FROM equipment ORDER BY id ASC")
    equipments = cur.fetchall()

    # Danh sách phiếu mượn/trả
    if session.get("role") == "admin":
        cur.execute("""
            SELECT br.*, u.full_name, u.student_id, eq.name AS equipment_name
            FROM borrow_requests br
            JOIN users u ON br.user_id = u.id
            JOIN equipment eq ON br.equipment_id = eq.id
            ORDER BY br.created_at DESC
        """)
    else:
        cur.execute("""
            SELECT br.*, u.full_name, u.student_id, eq.name AS equipment_name
            FROM borrow_requests br
            JOIN users u ON br.user_id = u.id
            JOIN equipment eq ON br.equipment_id = eq.id
            WHERE br.user_id = %s
            ORDER BY br.created_at DESC
        """, (session["user_id"],))
    borrows = cur.fetchall()

    for b in borrows:
        if b["status"] == "borrowing" and b["due_date"] < today:
            b["display_status"] = "overdue"  # Quá hạn
        else:
            b["display_status"] = b["status"]

    cur.close()
    conn.close()
    return render_template("equipment.html", equipments=equipments, borrows=borrows, today=today)


@app.route("/equipment/borrow", methods=["POST"])
@login_required
def borrow_equipment():
    equipment_id = request.form.get("equipment_id")
    quantity = int(request.form.get("quantity", 1))
    due_date = request.form.get("due_date")

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM equipment WHERE id = %s", (equipment_id,))
    eq = cur.fetchone()

    if not eq or eq["status"] != "ready" or eq["available_qty"] < quantity or quantity <= 0:
        flash("Thiết bị không sẵn sàng hoặc số lượng mượn vượt quá tồn kho!", "error")
        cur.close()
        conn.close()
        return redirect(url_for("equipment"))

    # Tạo phiếu mượn (Chờ duyệt) & trừ tạm số lượng sẵn có trong kho
    cur.execute(
        "INSERT INTO borrow_requests (user_id, equipment_id, quantity, borrow_date, due_date, status) VALUES (%s, %s, %s, CURDATE(), %s, 'pending')",
        (session["user_id"], equipment_id, quantity, due_date)
    )
    cur.execute(
        "UPDATE equipment SET available_qty = available_qty - %s WHERE id = %s",
        (quantity, equipment_id)
    )
    push_notification(cur, session["user_id"], f"Bạn đã gửi yêu cầu mượn {eq['name']} (x{quantity}).")
    conn.commit()
    cur.close()
    conn.close()

    flash("Đã gửi yêu cầu mượn thiết bị (Chờ Admin duyệt)!", "success")
    return redirect(url_for("equipment"))


@app.route("/equipment/approve/<int:borrow_id>", methods=["POST"])
@admin_required
def approve_borrow(borrow_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT br.*, eq.name AS equipment_name
        FROM borrow_requests br JOIN equipment eq ON br.equipment_id = eq.id
        WHERE br.id = %s
    """, (borrow_id,))
    br = cur.fetchone()
    if br and br["status"] == "pending":
        cur.execute("UPDATE borrow_requests SET status = 'borrowing' WHERE id = %s", (borrow_id,))
        push_notification(cur, br["user_id"], f"Admin đã duyệt phiếu mượn {br['equipment_name']} (x{br['quantity']}).")
        conn.commit()
    cur.close()
    conn.close()
    flash("Đã duyệt phiếu mượn thiết bị!", "success")
    return redirect(url_for("equipment"))


@app.route("/equipment/return/<int:borrow_id>", methods=["POST"])
@login_required
def return_equipment(borrow_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT br.*, eq.name AS equipment_name
        FROM borrow_requests br JOIN equipment eq ON br.equipment_id = eq.id
        WHERE br.id = %s
    """, (borrow_id,))
    br = cur.fetchone()
    if br and br["status"] == "borrowing":
        cur.execute("UPDATE borrow_requests SET status = 'returned', return_date = CURDATE() WHERE id = %s", (borrow_id,))
        cur.execute("UPDATE equipment SET available_qty = available_qty + %s WHERE id = %s", (br["quantity"], br["equipment_id"]))
        push_notification(cur, br["user_id"], f"Đã hoàn trả thiết bị {br['equipment_name']} (x{br['quantity']}) về kho.")
        conn.commit()
    cur.close()
    conn.close()
    flash("Đã xác nhận trả thiết bị!", "success")
    return redirect(url_for("equipment"))


@app.route("/equipment/add", methods=["POST"])
@admin_required
def add_equipment():
    code = request.form.get("code", "").strip().upper()
    name = request.form.get("name", "").strip()
    qty = int(request.form.get("total_qty", 1))
    status = request.form.get("status", "ready")

    if not code:
        code = f"EQ-{datetime.now().strftime('%H%M%S')}"

    conn = get_db()
    cur = conn.cursor()
    avail = qty if status == "ready" else 0
    cur.execute(
        "INSERT INTO equipment (code, name, total_qty, available_qty, status) VALUES (%s, %s, %s, %s, %s)",
        (code, name, qty, avail, status)
    )
    push_notification(cur, None, f"Kho thiết bị vừa cập nhật thiết bị mới: {name} (SL: {qty}).")
    conn.commit()
    cur.close()
    conn.close()

    flash("Đã thêm thiết bị mới vào kho!", "success")
    return redirect(url_for("equipment"))


@app.route("/equipment/edit/<int:eq_id>", methods=["POST"])
@admin_required
def edit_equipment(eq_id):
    total_qty = int(request.form.get("total_qty", 1))
    status = request.form.get("status", "ready")

    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM equipment WHERE id = %s", (eq_id,))
    eq = cur.fetchone()
    if eq:
        borrowed_out = eq["total_qty"] - eq["available_qty"]
        new_avail = max(0, total_qty - borrowed_out) if status == "ready" else 0
        cur.execute(
            "UPDATE equipment SET total_qty = %s, available_qty = %s, status = %s WHERE id = %s",
            (total_qty, new_avail, status, eq_id)
        )
        push_notification(cur, None, f"Admin đã cập nhật thiết bị {eq['name']} (SL: {total_qty}).")
        conn.commit()
    cur.close()
    conn.close()

    flash("Đã cập nhật thông tin thiết bị!", "success")
    return redirect(url_for("equipment"))

def sync_default_equipment():
    try:
        conn = get_db()
        cur = conn.cursor()
        items = [
            ("Máy hiện sóng Oscilloscope Tektronix", "EQ-OSC-01"),
            ("Bộ nguồn DC đa năng Korad", "EQ-PWR-04"),
            ("Máy phát hàm Signal Generator", "EQ-SIG-02"),
            ("Mỏ hàn nhiệt Weller WESD51", "EQ-SOL-09"),
        ]
        for name, code in items:
            cur.execute("UPDATE equipment SET name = %s WHERE code = %s", (name, code))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Bỏ qua đồng bộ thiết bị mặc định: {e}")

sync_default_equipment()
if __name__ == "__main__":
    init_default_admin()
    app.run(debug=True, port=5000)