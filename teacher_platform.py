"""Кабінет вчителя для «Розумника»: класи, коди приєднання, завдання, результати,
бібліотека презентацій і проєктів. Підключається двома рядками в app.py:

    from teacher_platform import init_platform
    init_platform(app, show_page, GRADES, get_subject, get_lesson)

Змінні середовища:
  SECRET_KEY          обов'язково задайте довгий випадковий рядок (інакше сесії скидаються)
  DATA_DIR            де зберігати базу й файли (за замовчуванням ./data)
  TEACHER_INVITE_CODE якщо задано — реєстрація вчителя можлива лише з цим кодом
"""
import csv
import hashlib
import io
import math
import os
import re
import secrets
import shutil
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from flask import (Blueprint, abort, flash, g, jsonify, redirect, request, send_file,
                   session, url_for, Response)
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint("tp", __name__)

ALLOWED_EXT = {
    "pdf": b"%PDF", "pptx": b"PK\x03\x04", "docx": b"PK\x03\x04", "xlsx": b"PK\x03\x04",
    "png": b"\x89PNG", "jpg": b"\xff\xd8\xff", "jpeg": b"\xff\xd8\xff",
}
INLINE_EXT = {"pdf", "png", "jpg", "jpeg"}
MAX_UPLOAD = 15 * 1024 * 1024
MAX_PERSONAL_NOTES = 100
MAX_NOTE_TITLE = 120
MAX_NOTE_BODY = 5000
PASSWORD_HASH_METHOD = "scrypt:32768:8:3"
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SCHEMA = """
CREATE TABLE IF NOT EXISTS teachers(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, pw TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE, name TEXT NOT NULL, grade INTEGER NOT NULL, code TEXT UNIQUE NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, nick TEXT NOT NULL, pin TEXT NOT NULL, created TEXT NOT NULL, UNIQUE(class_id, nick));
CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, url TEXT, stored TEXT, orig TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, kind TEXT NOT NULL, title TEXT NOT NULL, grade INTEGER, subject_slug TEXT, lesson_id INTEGER, material_id INTEGER REFERENCES materials(id) ON DELETE SET NULL, description TEXT NOT NULL DEFAULT '', due TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, grade INTEGER NOT NULL, subject_slug TEXT NOT NULL, lesson_id INTEGER NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY, assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, url TEXT, stored TEXT, orig TEXT, note TEXT NOT NULL DEFAULT '', created TEXT NOT NULL, answer TEXT NOT NULL DEFAULT '', teacher_feedback TEXT NOT NULL DEFAULT '', reviewed TEXT, showcase_requested INTEGER NOT NULL DEFAULT 0, showcase_approved INTEGER NOT NULL DEFAULT 0, showcase_name TEXT NOT NULL DEFAULT '', UNIQUE(assignment_id, student_id));
CREATE TABLE IF NOT EXISTS lesson_issue_reports(id INTEGER PRIMARY KEY, grade INTEGER NOT NULL, subject_slug TEXT NOT NULL, lesson_id INTEGER NOT NULL, category TEXT NOT NULL, message TEXT NOT NULL, created TEXT NOT NULL, reviewed TEXT);
CREATE TABLE IF NOT EXISTS grade_entries(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, subject TEXT NOT NULL, title TEXT NOT NULL, score REAL NOT NULL, max_score REAL NOT NULL, note TEXT NOT NULL DEFAULT '', created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, day TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('present','absent','late','excused')), updated TEXT NOT NULL, UNIQUE(class_id,student_id,day));
CREATE TABLE IF NOT EXISTS class_events(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, title TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', event_date TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS student_notes(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, title TEXT NOT NULL, body TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_results_student ON results(student_id);
CREATE INDEX IF NOT EXISTS idx_grade_entries_class ON grade_entries(class_id, student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_class_day ON attendance(class_id, day);
CREATE INDEX IF NOT EXISTS idx_student_notes_student ON student_notes(student_id, updated DESC);
"""

CTX = {}  # grades, show_page, get_subject, get_lesson — заповнюється в init_platform


# ───────────────────────── інфраструктура ─────────────────────────
def data_dir():
    path = os.environ.get("DATA_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(os.path.join(path, "uploads"), exist_ok=True)
    return path


def db():
    if "db" not in g:
        conn = sqlite3.connect(os.path.join(data_dir(), "rozumnyk.db"))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        g.db = conn
    return g.db


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def hash_secret(value):
    return generate_password_hash(value, method=PASSWORD_HASH_METHOD)


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]


def page(title, template, **values):
    values.setdefault("robots_noindex", True)
    values["css"] = PCSS
    return CTX["show_page"](title, "{{ css|safe }}" + template, **values)


_attempts = {}
_last_attempt_cleanup = 0


def throttled(key, limit=8, window=600):
    global _last_attempt_cleanup
    stamp = time.time()
    if stamp - _last_attempt_cleanup > 60:
        for old_key, old_hits in list(_attempts.items()):
            recent = [t for t in old_hits if stamp - t < 3600]
            if recent:
                _attempts[old_key] = recent
            else:
                _attempts.pop(old_key, None)
        _last_attempt_cleanup = stamp
    hits = [t for t in _attempts.get(key, []) if stamp - t < window]
    _attempts[key] = hits
    if len(hits) >= limit:
        return True
    hits.append(stamp)
    return False


def current_teacher():
    tid = session.get("teacher_id")
    if not tid:
        return None
    return db().execute("SELECT * FROM teachers WHERE id=?", (tid,)).fetchone()


def current_student():
    sid = session.get("student_id")
    if not sid:
        return None
    return db().execute(
        "SELECT s.*, c.name AS class_name, c.grade AS class_grade, c.code AS class_code "
        "FROM students s JOIN classes c ON c.id=s.class_id WHERE s.id=?", (sid,)).fetchone()


def teacher_required():
    teacher = current_teacher()
    if not teacher:
        flash("Увійдіть, щоб відкрити кабінет вчителя.")
        abort(redirect(url_for("tp.teacher_home")))
    return teacher


def owned_class(class_id):
    teacher = teacher_required()
    row = db().execute("SELECT * FROM classes WHERE id=? AND teacher_id=?", (class_id, teacher["id"])).fetchone()
    if not row:
        abort(404)
    return teacher, row


def passing(total):
    return 9 if total == 12 else 4


def new_code():
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not db().execute("SELECT 1 FROM classes WHERE code=?", (code,)).fetchone():
            return code


def clean(text, limit):
    return " ".join((text or "").split())[:limit]


def clean_lines(text, limit):
    lines = [" ".join(line.split()) for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)[:limit]


def safe_url(value):
    value = (value or "").strip()
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc and len(value) <= 600:
        return value
    return None


def embed_url(url):
    """Повертає безпечну адресу для iframe лише для перевірених сервісів."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path
    if host == "docs.google.com":
        m = re.match(r"^/presentation/d/(e/)?([\w-]+)", path)
        if m:
            return f"https://docs.google.com/presentation/d/{m.group(1) or ''}{m.group(2)}/embed?start=false&loop=false"
    if host in ("youtube.com", "m.youtube.com"):
        vid = (parse_qs(parsed.query).get("v") or [""])[0]
        if re.fullmatch(r"[\w-]{11}", vid):
            return f"https://www.youtube-nocookie.com/embed/{vid}"
    if host == "youtu.be" and re.fullmatch(r"/[\w-]{11}", path):
        return f"https://www.youtube-nocookie.com/embed/{path[1:]}"
    if host == "canva.com":
        m = re.match(r"^(/design/[\w-]+/[\w-]+)/(view|watch)", path)
        if m:
            return f"https://www.canva.com{m.group(1)}/view?embed"
    if host in ("view.genially.com", "view.genial.ly") and re.fullmatch(r"/[\w/-]+", path):
        return f"https://{host}{path}"
    if host == "learningapps.org" and path == "/watch":
        vid = (parse_qs(parsed.query).get("v") or [""])[0]
        if re.fullmatch(r"\w{4,20}", vid):
            return f"https://learningapps.org/watch?v={vid}"
    return None


def save_upload(file_storage):
    """Зберігає завантажений файл. Повертає (stored, orig). Кидає ValueError з поясненням."""
    if not file_storage or not file_storage.filename:
        raise ValueError("Файл не вибрано.")
    orig = clean(os.path.basename(file_storage.filename), 120)
    ext = orig.rsplit(".", 1)[-1].lower() if "." in orig else ""
    if ext not in ALLOWED_EXT:
        raise ValueError("Дозволені формати: PDF, PPTX, DOCX, XLSX, PNG, JPG.")
    head = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    if not head.startswith(ALLOWED_EXT[ext]):
        raise ValueError("Вміст файлу не відповідає його формату.")
    stored = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(data_dir(), "uploads", stored))
    return stored, orig


def remove_file(stored):
    if stored:
        try:
            os.remove(os.path.join(data_dir(), "uploads", os.path.basename(stored)))
        except OSError:
            pass


def serve_file(stored, orig):
    path = os.path.join(data_dir(), "uploads", os.path.basename(stored))
    if not os.path.isfile(path):
        abort(404)
    ext = stored.rsplit(".", 1)[-1]
    response = send_file(path, as_attachment=ext not in INLINE_EXT, download_name=orig)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; sandbox"
    return response


def csv_cell(value):
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@bp.before_request
def protect_posts():
    if request.method == "POST":
        sent = request.form.get("_csrf", "")
        if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
            abort(400, "Сесія застаріла. Оновіть сторінку й спробуйте ще раз.")


@bp.errorhandler(400)
def bad_request(error):
    return page("Помилка запиту", "<section class='tp'><h1>Не вдалося виконати дію</h1><p>{{ msg }}</p><p><a class='tp-btn' href='javascript:history.back()'>← Назад</a></p></section>",
                msg=getattr(error, "description", "Помилка запиту.")), 400


@bp.errorhandler(413)
def too_large(_error):
    return page("Файл завеликий", "<section class='tp'><h1>Файл завеликий</h1><p>Максимальний розмір — 15 МБ.</p><p><a class='tp-btn' href='javascript:history.back()'>← Назад</a></p></section>"), 413


PCSS = """<style>
.tp{max-width:980px;margin:0 auto}.tp h1{font-size:clamp(34.2px,5.7vw,50.16px);letter-spacing:-.04em;line-height:1.1;margin:8px 0 14px}.tp h2{font-size:25.08px;letter-spacing:-.02em;margin:34px 0 12px}.tp h3{margin:0 0 6px;font-size:18.24px}
.tp .lead{font-size:19.38px;color:var(--text-2,#4a5866);max-width:700px}.tp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.tp-card{background:var(--surface,#fff);border:1px solid var(--line);border-radius:16px;padding:18px 20px}.tp-card p{margin:4px 0;color:var(--text-2,#566471);font-size:15.96px}
.tp-btn{display:inline-block;background:var(--btn-bg,var(--green));color:#fff;text-decoration:none;border:0;border-radius:11px;padding:10px 17px;font:700 15.96px inherit;cursor:pointer}.tp-btn:hover{background:var(--btn-bg,var(--green-dark))}
.tp-btn.ghost{background:var(--ghost-bg,#fff);color:var(--green);border:1px solid var(--green)}.tp-btn.danger{background:var(--ghost-bg,#fff);color:var(--danger,#a23b2a);border:1px solid var(--danger-line,#e3b4aa)}.tp-btn.small{padding:6px 11px;font-size:13.68px}
.tp form.stack{display:grid;gap:11px;max-width:520px}.tp label{display:grid;gap:4px;font-size:14.82px;font-weight:700;color:var(--text-2,#33424f)}
.tp input,.tp select,.tp textarea{font:inherit;font-size:17.1px;padding:9px 11px;border:1px solid var(--field-line,#cfd6cc);border-radius:10px;background:var(--field,#fff);color:var(--ink);width:100%}.tp textarea{min-height:80px}
.tp .hint{font-size:13.68px;color:var(--muted);font-weight:400}.tp .flash{background:var(--flash-bg,#fff4dc);color:var(--flash-fg,inherit);border:1px solid #f0dfae;border-radius:12px;padding:11px 15px;margin:10px 0;font-size:15.96px}
.tp .code{font:800 38.76px/1 ui-monospace,Consolas,monospace;letter-spacing:.18em;background:var(--surface-2,#e4eee5);border-radius:12px;padding:12px 18px;display:inline-block}
.tp table{width:100%;border-collapse:collapse;background:var(--surface,#fff);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:14.82px}.tp th,.tp td{padding:9px 11px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.tp th{background:var(--surface-2,#f1f4ee);font-size:13.68px}
.tp .ok{color:var(--ok,#28633d);font-weight:800}.tp .warn{color:#e0a07a;font-weight:700}.tp .muted{color:var(--muted)}.tp .scroll{overflow-x:auto}.tp .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.tp iframe{width:100%;aspect-ratio:16/9;border:1px solid var(--line);border-radius:14px;background:#fff}.tp .pdf{aspect-ratio:auto;height:75vh}.tp .submission-review{margin:10px 0 0;padding:11px;border:1px solid var(--line);border-radius:11px;background:var(--surface-2,#f7f8f4)}.tp .submission-review p{white-space:pre-wrap;overflow-wrap:anywhere}
.tp .pill{display:inline-block;font-size:12.54px;font-weight:800;border-radius:99px;padding:2px 9px;background:var(--pill-bg,#e4eee5);color:var(--pill-fg,var(--green-dark))}.tp details{margin:8px 0}.tp summary{cursor:pointer;font-weight:700}
.tp .status-strip{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.tp .status-strip .pill{padding:5px 10px}.tp .issue-message{white-space:pre-wrap;overflow-wrap:anywhere}
</style>"""

FLASH = "{% with msgs = get_flashed_messages() %}{% for m in msgs %}<p class='flash'>{{ m }}</p>{% endfor %}{% endwith %}"

CSRF = "<input type='hidden' name='_csrf' value='{{ csrf_token() }}'>"

# ───────────────────────── кабінет вчителя ─────────────────────────
HOME_T = FLASH + """
<section class="tp">
  <p class="eyebrow">ДЛЯ ВЧИТЕЛІВ</p>
  <h1>Кабінет вчителя «Розумника»</h1>
  <p class="lead">Створіть клас, поділіться кодом з учнями, призначайте теми й контрольні, додавайте власні презентації та проєкти — і бачте результати кожного учня.</p>
  <div class="tp-grid" style="margin:22px 0">
    <div class="tp-card"><h3>👥 Класи й коди</h3><p>Учні заходять за кодом класу — без пошти та паролів.</p></div>
    <div class="tp-card"><h3>📌 Завдання</h3><p>Призначайте теми з контрольними та проєктні завдання з терміном.</p></div>
    <div class="tp-card"><h3>🖼️ Ваші матеріали</h3><p>Завантажуйте PDF, PPTX, DOCX або вставляйте Google Slides, Canva, YouTube.</p></div>
    <div class="tp-card"><h3>📊 Звіт по класу</h3><p>Результати за темами, зараховані теми, експорт у CSV для Excel.</p></div>
  </div>
  <div class="tp-grid">
    <div class="tp-card"><h2 style="margin-top:0">Увійти</h2>
      <form class="stack" method="post" action="{{ url_for('tp.teacher_login') }}">""" + CSRF + """
        <label>Електронна пошта<input type="email" name="email" required maxlength="120" autocomplete="username"></label>
        <label>Пароль<input type="password" name="password" required maxlength="128" autocomplete="current-password"></label>
        <button class="tp-btn" type="submit">Увійти</button></form></div>
    <div class="tp-card"><h2 style="margin-top:0">Зареєструватися</h2>
      <form class="stack" method="post" action="{{ url_for('tp.teacher_register') }}">""" + CSRF + """
        <label>Ім’я та по батькові<input name="name" required maxlength="80" autocomplete="name"></label>
        <label>Електронна пошта<input type="email" name="email" required maxlength="120" autocomplete="username"></label>
        <label>Пароль<input type="password" name="password" required minlength="15" maxlength="128" autocomplete="new-password"><span class="hint">Щонайменше 15 символів. Зручний варіант — кілька слів у фразі.</span></label>
        {% if invite %}<label>Код запрошення<input name="invite" required><span class="hint">Отримайте його в автора проєкту</span></label>{% endif %}
        <button class="tp-btn" type="submit">Створити кабінет</button></form></div>
  </div>
  <p class="muted" style="margin-top:20px;font-size:14.82px">Учні вказують лише ім’я або псевдонім. Докладніше — на сторінці <a href="{{ url_for('tp.platform_privacy') }}">«Приватність у класах»</a>.</p>
</section>"""


@bp.route("/teacher")
def teacher_home():
    if current_teacher():
        return redirect(url_for("tp.dashboard"))
    return page("Кабінет вчителя", HOME_T, invite=bool(os.environ.get("TEACHER_INVITE_CODE")))


@bp.post("/teacher/register")
def teacher_register():
    if throttled("reg:" + (request.remote_addr or ""), limit=6):
        abort(400, "Забагато спроб. Спробуйте за кілька хвилин.")
    invite = os.environ.get("TEACHER_INVITE_CODE", "")
    if invite and not secrets.compare_digest(request.form.get("invite", ""), invite):
        flash("Невірний код запрошення.")
        return redirect(url_for("tp.teacher_home"))
    name = clean(request.form.get("name"), 80)
    email = clean(request.form.get("email"), 120).lower()
    password = request.form.get("password", "")
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or not 15 <= len(password) <= 128:
        flash("Перевірте ім’я, пошту й пароль (від 15 до 128 символів).")
        return redirect(url_for("tp.teacher_home"))
    if db().execute("SELECT 1 FROM teachers WHERE email=?", (email,)).fetchone():
        flash("Не вдалося створити кабінет. Перевірте дані або спробуйте увійти, якщо вже маєте акаунт.")
        return redirect(url_for("tp.teacher_home"))
    cur = db().execute("INSERT INTO teachers(email,name,pw,created) VALUES(?,?,?,?)",
                       (email, name, hash_secret(password), now()))
    db().commit()
    session.clear()
    session["teacher_id"] = cur.lastrowid
    session.permanent = True
    return redirect(url_for("tp.dashboard"))


@bp.post("/teacher/login")
def teacher_login():
    email = clean(request.form.get("email"), 120).lower()
    email_key = hashlib.sha256(email.encode("utf-8")).hexdigest()[:20]
    if throttled(f"login-ip:{request.remote_addr}", limit=30) or throttled(f"login-email:{email_key}", limit=8) or len(request.form.get("password", "")) > 128:
        abort(400, "Забагато спроб входу. Спробуйте за кілька хвилин.")
    row = db().execute("SELECT * FROM teachers WHERE email=?", (email,)).fetchone()
    if not row or not check_password_hash(row["pw"], request.form.get("password", "")):
        flash("Невірна пошта або пароль.")
        return redirect(url_for("tp.teacher_home"))
    session.clear()
    session["teacher_id"] = row["id"]
    session.permanent = True
    return redirect(url_for("tp.dashboard"))


@bp.post("/teacher/logout")
def teacher_logout():
    session.clear()
    return redirect(url_for("tp.teacher_home"))


DASH_T = FLASH + """
<section class="tp">
  <p class="eyebrow">КАБІНЕТ ВЧИТЕЛЯ</p>
  <div class="row" style="justify-content:space-between"><h1>Вітаємо, <span data-no-translate>{{ teacher.name }}</span></h1>
    <form method="post" action="{{ url_for('tp.teacher_logout') }}">""" + CSRF + """<button class="tp-btn ghost small">Вийти</button></form></div>
  <h2>Мої класи</h2>
  {% if classes %}<div class="tp-grid">{% for c in classes %}
    <a class="tp-card" style="text-decoration:none;color:inherit" href="{{ url_for('tp.class_page', class_id=c.id) }}">
      <h3 data-no-translate>{{ c.name }}</h3><p>{{ c.grade }} клас · учнів: {{ c.n }}</p><p>Домашніх робіт очікують перевірки: <strong>{{ c.pending_homework }}</strong></p><p>Код: <strong data-no-translate>{{ c.code }}</strong></p></a>{% endfor %}</div>
  {% else %}<p class="muted">Класів ще немає. Створіть перший — і отримаєте код для учнів.</p>{% endif %}
  <h2>Створити клас</h2>
  <form class="stack" method="post" action="{{ url_for('tp.class_create') }}">""" + CSRF + """
    <label>Назва класу<input name="name" required maxlength="60" placeholder="Наприклад, 9-А"></label>
    <label>Клас навчання<select name="grade">{% for g in grades %}<option value="{{ g }}" {{ 'selected' if g == 9 }}>{{ g }} клас</option>{% endfor %}</select></label>
    <button class="tp-btn" type="submit">Створити клас</button></form>
  <h2>Мої матеріали</h2>
  <p>Презентації, проєкти й посилання, які ви можете призначати класам. <a href="{{ url_for('tp.materials') }}">Відкрити бібліотеку →</a> (матеріалів: {{ n_materials }})</p>
  <h2>Повідомлення про теми</h2><p><a class="tp-btn ghost" href="{{ url_for('tp.content_reports') }}">Переглянути повідомлення про неточності · {{ open_reports }}</a></p>
</section>"""


@bp.route("/teacher/dashboard")
def dashboard():
    teacher = teacher_required()
    classes = db().execute(
        "SELECT c.*, (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n, "
        "(SELECT COUNT(*) FROM submissions sb JOIN assignments a ON a.id=sb.assignment_id "
        "WHERE a.class_id=c.id AND a.kind='homework' AND sb.reviewed IS NULL) AS pending_homework "
        "FROM classes c WHERE teacher_id=? ORDER BY c.id DESC", (teacher["id"],)).fetchall()
    n_materials = db().execute("SELECT COUNT(*) FROM materials WHERE teacher_id=?", (teacher["id"],)).fetchone()[0]
    open_reports = db().execute("SELECT COUNT(*) FROM lesson_issue_reports WHERE reviewed IS NULL").fetchone()[0]
    return page("Кабінет вчителя", DASH_T, teacher=teacher, classes=classes,
                grades=sorted(CTX["grades"]), n_materials=n_materials, open_reports=open_reports)


@bp.post("/teacher/classes")
def class_create():
    teacher = teacher_required()
    name = clean(request.form.get("name"), 60)
    try:
        grade = int(request.form.get("grade", "9"))
    except ValueError:
        grade = 9
    if not name or grade not in CTX["grades"]:
        flash("Вкажіть назву класу.")
        return redirect(url_for("tp.dashboard"))
    cur = db().execute("INSERT INTO classes(teacher_id,name,grade,code,created) VALUES(?,?,?,?,?)",
                       (teacher["id"], name, grade, new_code(), now()))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=cur.lastrowid))


CLASS_T = FLASH + """
<section class="tp">
  <nav class="crumb"><a href="{{ url_for('tp.dashboard') }}">Кабінет</a>　/　<span data-no-translate>{{ klass.name }}</span></nav>
  <h1><span data-no-translate>{{ klass.name }}</span> <span class="pill">{{ klass.grade }} клас</span></h1>
  <div class="tp-card"><p>Код класу для учнів:</p><div class="code">{{ klass.code }}</div>
    <p style="margin-top:10px">Учні відкривають <strong>{{ join_url }}</strong>, вводять код та своє ім’я.</p>
    <div class="row"><form method="post" action="{{ url_for('tp.class_newcode', class_id=klass.id) }}">""" + CSRF + """<button class="tp-btn ghost small">Новий код</button></form>
    <a class="tp-btn ghost small" href="{{ url_for('tp.class_csv', class_id=klass.id) }}">⬇ Звіт CSV</a></div></div>

  <h2>Звіт по класу</h2>
  {% if not students %}<p class="muted">Поки немає учнів. Дайте їм код класу.</p>
  {% elif not columns %}<p class="muted">Призначте завдання нижче — і тут з’являться результати.</p>
  {% else %}<div class="scroll"><table><thead><tr><th>Учень</th>{% for a in columns %}<th title="{{ a.title }}">{{ a.title[:34] }}{{ '…' if a.title|length > 34 }}{% if a.due %}<br><span class="muted">до {{ a.due }}</span>{% endif %}</th>{% endfor %}<th>Зараховано</th></tr></thead><tbody>
    {% for row in rows %}<tr><td><strong data-no-translate>{{ row.student.nick }}</strong></td>{% for cell in row.cells %}<td>{{ cell|safe }}</td>{% endfor %}<td><strong>{{ row.done }}</strong> із {{ columns|length }}</td></tr>{% endfor %}
  </tbody></table></div>{% endif %}

  <h2>Призначити теми</h2>
  <form class="stack" method="post" action="{{ url_for('tp.assign_lessons', class_id=klass.id) }}" style="max-width:640px">""" + CSRF + """
    <label>Предмет<select name="subject" id="sub">{% for s in catalog %}<option value="{{ s.slug }}">{{ s.name }}</option>{% endfor %}</select></label>
    <label>Теми (Ctrl або Shift — вибрати кілька)<select name="lessons" id="les" multiple size="9" required></select></label>
    <label>Термін виконання<input type="date" name="due"></label>
    <button class="tp-btn" type="submit">Призначити</button></form>
  <script>const CAT={{ catalog|tojson }};const sub=document.getElementById('sub'),les=document.getElementById('les');
  function fill(){const s=CAT.find(x=>x.slug===sub.value);les.innerHTML='';s.lessons.forEach((t,i)=>{const o=document.createElement('option');o.value=i+1;o.textContent=(i+1)+'. '+t;les.appendChild(o)})}
  sub.addEventListener('change',fill);fill();</script>

  <h2>Додати домашнє завдання або матеріал</h2>
  <div class="tp-grid">
    <div class="tp-card"><h3>📚 Домашнє завдання</h3>
      <form class="stack" method="post" action="{{ url_for('tp.add_homework', class_id=klass.id) }}">""" + CSRF + """
        <label>Назва<input name="title" required maxlength="120" placeholder="Наприклад, вправи 4–6"></label>
        <label>Що потрібно зробити<textarea name="description" required maxlength="800" placeholder="Опиши завдання зрозумілими кроками"></textarea></label>
        <label>Предмет і пояснення (необов’язково)<select name="subject_slug" id="homework-subject"><option value="">Без посилання на тему</option>{% for s in catalog %}<option value="{{ s.slug }}">{{ s.name }}</option>{% endfor %}</select></label>
        <label>Тема уроку<select name="lesson_id" id="homework-lesson" disabled><option value="">Спочатку обери предмет</option></select></label>
        <label>Термін<input type="date" name="due"></label>
        <button class="tp-btn small" type="submit">Задати класу</button></form>
      <p class="hint" style="margin-top:8px">Учні зможуть надіслати відповідь, а ви — залишити відгук.</p></div>
    <div class="tp-card"><h3>🖼️ Матеріал із вашої бібліотеки</h3>
      {% if materials %}<form class="stack" method="post" action="{{ url_for('tp.attach_material', class_id=klass.id) }}">""" + CSRF + """
        <label>Матеріал<select name="material_id">{% for m in materials %}<option value="{{ m.id }}">{{ m.title }}</option>{% endfor %}</select></label>
        <button class="tp-btn small" type="submit">Показати класу</button></form>
      {% else %}<p>Бібліотека порожня. <a href="{{ url_for('tp.materials') }}">Додайте перший матеріал →</a></p>{% endif %}</div>
    <div class="tp-card"><h3>📁 Проєктне завдання</h3>
      <form class="stack" method="post" action="{{ url_for('tp.add_task', class_id=klass.id) }}">""" + CSRF + """
        <label>Назва<input name="title" required maxlength="120"></label>
        <label>Опис і критерії<textarea name="description" maxlength="800"></textarea></label>
        <label>Термін<input type="date" name="due"></label>
        <button class="tp-btn small" type="submit">Створити завдання</button></form>
      <p class="hint" style="margin-top:8px">Учні здають посилання або файл; бачите їх лише ви.</p></div>
  </div>
  <script>const HOMEWORK_CATALOG={{ catalog|tojson }},homeworkSubject=document.getElementById('homework-subject'),homeworkLesson=document.getElementById('homework-lesson');
  function fillHomeworkLessons(){const selected=HOMEWORK_CATALOG.find(item=>item.slug===homeworkSubject.value);homeworkLesson.innerHTML='';if(!selected){homeworkLesson.disabled=true;homeworkLesson.add(new Option('Спочатку обери предмет',''));return}homeworkLesson.disabled=false;homeworkLesson.add(new Option('Не прив’язувати до окремої теми',''));selected.lessons.forEach((title,index)=>homeworkLesson.add(new Option((index+1)+'. '+title,String(index+1))))}
  homeworkSubject.addEventListener('change',fillHomeworkLessons);fillHomeworkLessons();</script>

  <h2>Завдання класу</h2>
  {% if assignments %}<table><tbody>{% for a in assignments %}<tr><td><span class="pill">{{ {'lesson':'тема','material':'матеріал','project':'проєкт','homework':'домашнє завдання'}[a.kind] }}</span> {{ a.title }}{% if a.due %} <span class="muted">· до {{ a.due }}</span>{% endif %}
    {% if a.kind == 'project' %}<br><span class="muted">Здано: {{ subs.get(a.id, 0) }}</span> {% for sb in sublist.get(a.id, []) %}<br>· <span data-no-translate>{{ sb.nick }}</span>: {% if sb.url %}<a href="{{ sb.url }}" target="_blank" rel="noopener noreferrer nofollow">посилання</a>{% endif %}{% if sb.stored %} <a href="{{ url_for('tp.submission_file', sub_id=sb.id) }}">файл ({{ sb.orig }})</a>{% endif %}{% if sb.note %} — <span data-no-translate>{{ sb.note }}</span>{% endif %}{% if sb.showcase_requested %}<span class="pill">{{ 'У галереї' if sb.showcase_approved else 'Просить показати класу' }}</span><form method="post" action="{{ url_for('tp.review_showcase', class_id=klass.id, sub_id=sb.id) }}" style="display:inline"><input type="hidden" name="_csrf" value="{{ csrf_token() }}"><input type="hidden" name="approve" value="{{ '0' if sb.showcase_approved else '1' }}"><button class="tp-btn ghost small" type="submit">{{ 'Прибрати з галереї' if sb.showcase_approved else 'Схвалити показ' }}</button></form>{% endif %}{% endfor %}{% elif a.kind == 'homework' %}<div class="status-strip"><span class="pill">Надіслали: {{ homework_stats[a.id].submitted }}</span><span class="pill">Очікує перевірки: {{ homework_stats[a.id].pending }}</span><span class="pill">Є відгук: {{ homework_stats[a.id].reviewed }}</span><span class="pill">Ще не здали: {{ homework_stats[a.id].missing }}</span></div>{% for sb in sublist.get(a.id, []) %}<div class="submission-review"><strong>{{ sb.nick }}</strong> <span class="pill">{{ 'Відгук надіслано' if sb.teacher_feedback else ('Переглянуто без коментаря' if sb.reviewed else 'Очікує перевірки') }}</span>{% if sb.answer %}<p>{{ sb.answer }}</p>{% else %}<p class="muted">Учень позначив виконання без текстової відповіді.</p>{% endif %}{% if sb.stored %}<p><a href="{{ url_for('tp.submission_file', sub_id=sb.id) }}">Відкрити роботу: {{ sb.orig }}</a></p>{% endif %}<form class="stack" method="post" action="{{ url_for('tp.review_homework', class_id=klass.id, aid=a.id, sid=sb.student_id) }}">""" + CSRF + """
        <label>Відгук для учня<textarea name="feedback" maxlength="1000" placeholder="Що вдалося і що варто допрацювати?">{{ sb.teacher_feedback }}</textarea></label><button class="tp-btn ghost small" type="submit">{{ 'Оновити відгук' if sb.reviewed else 'Надіслати відгук' }}</button></form></div>{% endfor %}{% endif %}</td>
    <td style="width:90px"><form method="post" action="{{ url_for('tp.assignment_delete', class_id=klass.id, aid=a.id) }}" onsubmit="return confirm('Видалити завдання?')">""" + CSRF + """<button class="tp-btn danger small">Видалити</button></form></td></tr>{% endfor %}</tbody></table>
  {% else %}<p class="muted">Завдань ще немає.</p>{% endif %}

  <h2>Календар класу</h2><div class="tp-grid"><div class="tp-card"><h3>Додати подію</h3>
    <form class="stack" method="post" action="{{ url_for('tp.add_class_event', class_id=klass.id) }}">""" + CSRF + """
      <label>Назва<input name="title" required maxlength="120" placeholder="Наприклад, консультація з математики"></label>
      <label>Дата<input type="date" name="event_date" required></label><label>Деталі<textarea name="details" maxlength="500"></textarea></label>
      <button class="tp-btn small">Додати до календаря</button></form></div><div class="tp-card"><h3>Найближчі події</h3>
      {% if events %}<ul>{% for e in events %}<li><strong>{{ e.event_date }}</strong> · {{ e.title }}{% if e.details %}<br><span class="muted">{{ e.details }}</span>{% endif %}</li>{% endfor %}</ul>{% else %}<p class="muted">Подій поки немає. Терміни домашніх завдань теж з’являються в календарі учнів.</p>{% endif %}</div></div>

  <h2>Журнал оцінок</h2><div class="tp-grid"><div class="tp-card"><h3>Додати оцінку</h3>
    {% if students %}<form class="stack" method="post" action="{{ url_for('tp.add_grade', class_id=klass.id) }}">""" + CSRF + """
      <label>Учень<select name="student_id" required data-no-translate>{% for s in students %}<option value="{{ s.id }}">{{ s.nick }}</option>{% endfor %}</select></label>
      <label>Предмет<input name="subject" required maxlength="80"></label><label>Робота<input name="title" required maxlength="120"></label>
      <div class="row"><label>Бали<input type="number" name="score" min="0" step="0.5" required></label><label>Максимум<input type="number" name="max_score" min="0.5" step="0.5" required></label></div>
      <label>Коментар (необов’язково)<input name="note" maxlength="240"></label><button class="tp-btn small">Зберегти оцінку</button></form>{% else %}<p>Спершу запросіть учнів до класу.</p>{% endif %}</div>
    <div class="tp-card"><h3>Останні оцінки</h3>{% if grade_entries %}<div class="scroll"><table><thead><tr><th>Учень</th><th>Робота</th><th>Оцінка</th></tr></thead><tbody>{% for g in grade_entries %}<tr><td>{{ g.nick }}</td><td>{{ g.subject }} · {{ g.title }}{% if g.note %}<br><span class="muted">{{ g.note }}</span>{% endif %}</td><td><strong>{{ g.score|int if g.score == g.score|int else g.score }}/{{ g.max_score|int if g.max_score == g.max_score|int else g.max_score }}</strong></td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="muted">Оцінок ще немає.</p>{% endif %}</div></div>

  <h2>Відвідуваність</h2><div class="tp-card"><form method="get" class="row" style="margin-bottom:12px"><label>Дата<input type="date" name="attendance_day" value="{{ attendance_day }}"></label><button class="tp-btn ghost small">Відкрити</button></form>
    {% if students %}<form class="stack" method="post" action="{{ url_for('tp.save_attendance', class_id=klass.id) }}">""" + CSRF + """
      <input type="hidden" name="day" value="{{ attendance_day }}"><div class="scroll"><table><thead><tr><th>Учень</th><th>Статус</th></tr></thead><tbody>{% for s in students %}<tr><td>{{ s.nick }}</td><td><select name="status_{{ s.id }}"><option value="present" {{ 'selected' if attendance.get(s.id) == 'present' }}>Присутній</option><option value="absent" {{ 'selected' if attendance.get(s.id) == 'absent' }}>Відсутній</option><option value="late" {{ 'selected' if attendance.get(s.id) == 'late' }}>Запізнився</option><option value="excused" {{ 'selected' if attendance.get(s.id) == 'excused' }}>Поважна причина</option></select></td></tr>{% endfor %}</tbody></table></div><button class="tp-btn small">Зберегти відвідуваність</button></form>{% else %}<p class="muted">Учнів ще немає.</p>{% endif %}</div>

  <h2>Учні ({{ students|length }})</h2>
  {% if students %}<table><tbody>{% for s in students %}<tr><td>{{ s.nick }}</td><td style="width:260px"><div class="row">
    <form method="post" action="{{ url_for('tp.student_pin', class_id=klass.id, sid=s.id) }}">""" + CSRF + """<button class="tp-btn ghost small">Новий PIN</button></form>
    <form method="post" action="{{ url_for('tp.student_delete', class_id=klass.id, sid=s.id) }}" onsubmit="return confirm('Видалити учня разом із результатами?')">""" + CSRF + """<button class="tp-btn danger small">Видалити</button></form></div></td></tr>{% endfor %}</tbody></table>{% endif %}

  <h2>Керування класом</h2>
  <form method="post" action="{{ url_for('tp.class_delete', class_id=klass.id) }}" onsubmit="return confirm('Видалити клас, учнів і всі результати? Дію не можна скасувати.')">""" + CSRF + """<button class="tp-btn danger">Видалити клас</button></form>
</section>"""


def class_report(klass):
    """Повертає (students, columns, rows) для звіту й CSV."""
    d = db()
    students = sorted(d.execute("SELECT * FROM students WHERE class_id=?", (klass["id"],)).fetchall(),
                      key=lambda s: [int(x) if x.isdigit() else x.casefold() for x in re.split(r"(\d+)", s["nick"])])
    columns = d.execute("SELECT * FROM assignments WHERE class_id=? AND kind IN ('lesson','project','homework') ORDER BY id", (klass["id"],)).fetchall()
    best = {}
    for r in d.execute("SELECT r.* FROM results r JOIN students s ON s.id=r.student_id WHERE s.class_id=?", (klass["id"],)):
        key = (r["student_id"], r["grade"], r["subject_slug"], r["lesson_id"])
        if key not in best or r["score"] > best[key]["score"]:
            best[key] = r
    subs = {(x["assignment_id"], x["student_id"]): x for x in d.execute(
        "SELECT sb.* FROM submissions sb JOIN students s ON s.id=sb.student_id WHERE s.class_id=?", (klass["id"],))}
    rows = []
    for st in students:
        cells, plain, done = [], [], 0
        for a in columns:
            if a["kind"] == "lesson":
                r = best.get((st["id"], a["grade"], a["subject_slug"], a["lesson_id"]))
                if r:
                    ok = r["score"] >= passing(r["total"])
                    done += ok
                    cells.append(f"<span class='{'ok' if ok else 'warn'}'>{r['score']}/{r['total']}{' ✓' if ok else ''}</span>")
                    plain.append(f"{r['score']}/{r['total']}" + (" зараховано" if ok else ""))
                else:
                    cells.append("<span class='muted'>—</span>")
                    plain.append("")
            else:
                sb = subs.get((a["id"], st["id"]))
                done += bool(sb)
                label = "виконано" if a["kind"] == "homework" else "здано"
                cells.append(f"<span class='ok'>{label} ✓</span>" if sb else "<span class='muted'>—</span>")
                plain.append(label if sb else "")
        rows.append({"student": st, "cells": cells, "plain": plain, "done": done})
    return students, columns, rows


@bp.route("/teacher/class/<int:class_id>")
def class_page(class_id):
    teacher, klass = owned_class(class_id)
    d = db()
    students, columns, rows = class_report(klass)
    assignments = d.execute("SELECT * FROM assignments WHERE class_id=? ORDER BY id DESC", (klass["id"],)).fetchall()
    sublist = {}
    for sb in d.execute("SELECT sb.*, s.nick FROM submissions sb JOIN students s ON s.id=sb.student_id WHERE s.class_id=? ORDER BY sb.id", (klass["id"],)):
        sublist.setdefault(sb["assignment_id"], []).append(sb)
    homework_stats = {}
    for a in assignments:
        if a["kind"] == "homework":
            submitted = sublist.get(a["id"], [])
            reviewed = sum(bool(sb["reviewed"]) for sb in submitted)
            pending = sum(not bool(sb["reviewed"]) for sb in submitted)
            homework_stats[a["id"]] = {"submitted": len(submitted), "reviewed": reviewed,
                                        "pending": pending,
                                        "missing": max(0, len(students) - len(submitted))}
    catalog = [{"slug": s["slug"], "name": s["name"], "lessons": [l["title"] for l in s["lessons"]]}
               for s in CTX["grades"][klass["grade"]]]
    materials = d.execute("SELECT id,title FROM materials WHERE teacher_id=? ORDER BY id DESC", (teacher["id"],)).fetchall()
    attendance_day = valid_due(request.args.get("attendance_day")) or datetime.now().strftime("%Y-%m-%d")
    attendance = {r["student_id"]: r["status"] for r in d.execute("SELECT student_id,status FROM attendance WHERE class_id=? AND day=?", (klass["id"], attendance_day))}
    grade_entries = d.execute("SELECT ge.*,s.nick FROM grade_entries ge JOIN students s ON s.id=ge.student_id WHERE ge.class_id=? ORDER BY ge.id DESC LIMIT 100", (klass["id"],)).fetchall()
    events = d.execute("SELECT * FROM class_events WHERE class_id=? ORDER BY event_date,id LIMIT 30", (klass["id"],)).fetchall()
    return page(f"Клас {klass['name']}", CLASS_T, klass=klass, students=students, columns=columns, rows=rows,
                assignments=assignments, subs={k: len(v) for k, v in sublist.items()}, sublist=sublist, homework_stats=homework_stats,
                catalog=catalog, materials=materials, join_url=url_for("tp.join", _external=True),
                attendance_day=attendance_day, attendance=attendance, grade_entries=grade_entries, events=events)


@bp.post("/teacher/class/<int:class_id>/grade")
def add_grade(class_id):
    _, klass = owned_class(class_id)
    sid = request.form.get("student_id", "")
    student = db().execute("SELECT id FROM students WHERE id=? AND class_id=?", (sid, klass["id"])).fetchone() if sid.isdigit() else None
    try:
        score, maximum = float(request.form.get("score", "")), float(request.form.get("max_score", ""))
    except (TypeError, ValueError):
        score, maximum = -1, 0
    subject, title = clean(request.form.get("subject"), 80), clean(request.form.get("title"), 120)
    if (not student or not subject or not title or not math.isfinite(score) or not math.isfinite(maximum)
            or maximum <= 0 or score < 0 or score > maximum or maximum > 1000):
        flash("Перевірте учня, назву роботи й бали.")
        return redirect(url_for("tp.class_page", class_id=class_id))
    db().execute("INSERT INTO grade_entries(class_id,student_id,subject,title,score,max_score,note,created) VALUES(?,?,?,?,?,?,?,?)",
                 (klass["id"], student["id"], subject, title, score, maximum, clean(request.form.get("note"), 240), now()))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/attendance")
def save_attendance(class_id):
    _, klass = owned_class(class_id)
    day = valid_due(request.form.get("day"))
    if not day:
        abort(400)
    allowed = {"present", "absent", "late", "excused"}
    for student in db().execute("SELECT id FROM students WHERE class_id=?", (klass["id"],)):
        status = request.form.get(f"status_{student['id']}", "present")
        if status not in allowed:
            abort(400)
        db().execute("INSERT INTO attendance(class_id,student_id,day,status,updated) VALUES(?,?,?,?,?) ON CONFLICT(class_id,student_id,day) DO UPDATE SET status=excluded.status,updated=excluded.updated",
                     (klass["id"], student["id"], day, status, now()))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id, attendance_day=day))


@bp.post("/teacher/class/<int:class_id>/calendar")
def add_class_event(class_id):
    _, klass = owned_class(class_id)
    title, day = clean(request.form.get("title"), 120), valid_due(request.form.get("event_date"))
    if not title or not day:
        flash("Вкажіть назву події та коректну дату.")
        return redirect(url_for("tp.class_page", class_id=class_id))
    db().execute("INSERT INTO class_events(class_id,title,details,event_date,created) VALUES(?,?,?,?,?)",
                 (klass["id"], title, clean_lines(request.form.get("details"), 500), day, now()))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.route("/teacher/class/<int:class_id>/report.csv")
def class_csv(class_id):
    _, klass = owned_class(class_id)
    students, columns, rows = class_report(klass)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Учень"] + [csv_cell(a["title"]) for a in columns] + ["Зараховано"])
    for row in rows:
        writer.writerow([csv_cell(row["student"]["nick"])] + row["plain"] + [row["done"]])
    body = "\ufeff" + out.getvalue()
    return Response(body, mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename=class-{klass['id']}-report.csv"})


@bp.post("/teacher/class/<int:class_id>/newcode")
def class_newcode(class_id):
    _, klass = owned_class(class_id)
    db().execute("UPDATE classes SET code=? WHERE id=?", (new_code(), klass["id"]))
    db().commit()
    flash("Код класу змінено. Старий код більше не працює.")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/delete")
def class_delete(class_id):
    _, klass = owned_class(class_id)
    for sb in db().execute("SELECT sb.stored FROM submissions sb JOIN assignments a ON a.id=sb.assignment_id WHERE a.class_id=?", (klass["id"],)):
        remove_file(sb["stored"])
    db().execute("DELETE FROM classes WHERE id=?", (klass["id"],))
    db().commit()
    return redirect(url_for("tp.dashboard"))


def valid_due(value):
    try:
        datetime.strptime(value or "", "%Y-%m-%d")
        return value
    except ValueError:
        return None


@bp.post("/teacher/class/<int:class_id>/assign")
def assign_lessons(class_id):
    _, klass = owned_class(class_id)
    subject = CTX["get_subject"](request.form.get("subject", ""), klass["grade"])
    if not subject:
        abort(404)
    due = valid_due(request.form.get("due"))
    added = 0
    for raw in request.form.getlist("lessons")[:60]:
        if not raw.isdigit() or not 1 <= int(raw) <= len(subject["lessons"]):
            continue
        lid = int(raw)
        if db().execute("SELECT 1 FROM assignments WHERE class_id=? AND kind='lesson' AND subject_slug=? AND lesson_id=? AND grade=?",
                        (klass["id"], subject["slug"], lid, klass["grade"])).fetchone():
            continue
        title = f"{subject['name']}: {subject['lessons'][lid - 1]['title']}"
        db().execute("INSERT INTO assignments(class_id,kind,title,grade,subject_slug,lesson_id,due,created) VALUES(?,?,?,?,?,?,?,?)",
                     (klass["id"], "lesson", title[:200], klass["grade"], subject["slug"], lid, due, now()))
        added += 1
    db().commit()
    flash(f"Призначено тем: {added}." if added else "Нових тем не додано (вони вже призначені або не вибрані).")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/task")
def add_task(class_id):
    _, klass = owned_class(class_id)
    title = clean(request.form.get("title"), 120)
    if not title:
        flash("Вкажіть назву завдання.")
        return redirect(url_for("tp.class_page", class_id=class_id))
    db().execute("INSERT INTO assignments(class_id,kind,title,description,due,created) VALUES(?,?,?,?,?,?)",
                 (klass["id"], "project", title, clean(request.form.get("description"), 800), valid_due(request.form.get("due")), now()))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/homework")
def add_homework(class_id):
    _, klass = owned_class(class_id)
    title = clean(request.form.get("title"), 120)
    description = clean_lines(request.form.get("description"), 800)
    if not title or not description:
        flash("Додайте назву й пояснення домашнього завдання.")
        return redirect(url_for("tp.class_page", class_id=class_id))
    subject_slug = clean(request.form.get("subject_slug"), 80)
    raw_lesson_id = request.form.get("lesson_id", "").strip()
    grade = lesson_id = None
    if subject_slug:
        subject = CTX["get_subject"](subject_slug, klass["grade"])
        if not subject:
            abort(400, "Оберіть предмет зі списку класу.")
        grade = klass["grade"]
        if raw_lesson_id:
            if not raw_lesson_id.isdigit() or not 1 <= int(raw_lesson_id) <= len(subject["lessons"]):
                abort(400, "Оберіть тему зі списку предмета.")
            lesson_id = int(raw_lesson_id)
    elif raw_lesson_id:
        abort(400, "Спочатку оберіть предмет.")
    due = request.form.get("due", "").strip()
    if due and not valid_due(due):
        abort(400, "Вкажіть коректну дату здавання.")
    db().execute(
        "INSERT INTO assignments(class_id,kind,title,grade,subject_slug,lesson_id,description,due,created) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (klass["id"], "homework", title, grade, subject_slug or None, lesson_id, description,
         valid_due(due), now()),
    )
    db().commit()
    flash("Домашнє завдання додано до класу.")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/attach")
def attach_material(class_id):
    teacher, klass = owned_class(class_id)
    raw = request.form.get("material_id", "")
    mat = db().execute("SELECT * FROM materials WHERE id=? AND teacher_id=?", (raw, teacher["id"])).fetchone() if raw.isdigit() else None
    if not mat:
        abort(404)
    db().execute("INSERT INTO assignments(class_id,kind,title,material_id,created) VALUES(?,?,?,?,?)",
                 (klass["id"], "material", mat["title"], mat["id"], now()))
    db().commit()
    flash("Матеріал додано до класу.")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/assignment/<int:aid>/delete")
def assignment_delete(class_id, aid):
    _, klass = owned_class(class_id)
    assignment = db().execute("SELECT id FROM assignments WHERE id=? AND class_id=?", (aid, klass["id"])).fetchone()
    if not assignment:
        abort(404)
    for sb in db().execute("SELECT stored FROM submissions WHERE assignment_id=?", (assignment["id"],)):
        remove_file(sb["stored"])
    db().execute("DELETE FROM assignments WHERE id=? AND class_id=?", (assignment["id"], klass["id"]))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/student/<int:sid>/pin")
def student_pin(class_id, sid):
    _, klass = owned_class(class_id)
    st = db().execute("SELECT * FROM students WHERE id=? AND class_id=?", (sid, klass["id"])).fetchone()
    if not st:
        abort(404)
    pin = f"{secrets.randbelow(1_000_000):06d}"
    db().execute("UPDATE students SET pin=? WHERE id=?", (hash_secret(pin), sid))
    db().commit()
    flash(f"Новий PIN для «{st['nick']}»: {pin}. Передайте його учневі — повторно його не буде показано.")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/student/<int:sid>/delete")
def student_delete(class_id, sid):
    _, klass = owned_class(class_id)
    student = db().execute("SELECT id FROM students WHERE id=? AND class_id=?", (sid, klass["id"])).fetchone()
    if not student:
        abort(404)
    for sb in db().execute("SELECT stored FROM submissions WHERE student_id=?", (student["id"],)):
        remove_file(sb["stored"])
    db().execute("DELETE FROM students WHERE id=? AND class_id=?", (student["id"], klass["id"]))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id))


# ───────────────────────── матеріали (презентації, проєкти) ─────────────────────────
MAT_T = FLASH + """
<section class="tp">
  <nav class="crumb"><a href="{{ url_for('tp.dashboard') }}">Кабінет</a>　/　Мої матеріали</nav>
  <h1>Мої матеріали</h1>
  <p class="lead">Додайте презентацію чи проєкт файлом або посиланням — потім покажіть їх будь-якому своєму класу.</p>
  <div class="tp-card"><form class="stack" method="post" enctype="multipart/form-data" action="{{ url_for('tp.material_add') }}">""" + CSRF + """
    <label>Назва<input name="title" required maxlength="120" placeholder="Наприклад, Презентація до теми «Вектори»"></label>
    <label>Опис (необов’язково)<textarea name="description" maxlength="600"></textarea></label>
    <label>Посилання (Google Slides, Canva, YouTube, Genially, LearningApps або будь-яке інше)<input type="url" name="url" placeholder="https://…"></label>
    <label>…або файл (PDF, PPTX, DOCX, XLSX, PNG, JPG — до 15 МБ)<input type="file" name="file" accept=".pdf,.pptx,.docx,.xlsx,.png,.jpg,.jpeg"></label>
    <p class="hint">Для Google Slides відкрийте доступ «усім, хто має посилання». Макроси й виконувані файли не приймаються.</p>
    <button class="tp-btn" type="submit">Додати матеріал</button></form></div>
  <h2>Бібліотека</h2>
  {% if items %}<div class="tp-grid">{% for m in items %}<div class="tp-card"><span class="pill">{{ {'embed':'вставка','link':'посилання','file':'файл'}[m.kind] }}</span>
    <h3 style="margin-top:8px">{{ m.title }}</h3>{% if m.description %}<p>{{ m.description }}</p>{% endif %}
    <div class="row" style="margin-top:10px"><a class="tp-btn ghost small" href="{{ url_for('tp.material_view', mid=m.id) }}">Переглянути</a>
    <form method="post" action="{{ url_for('tp.material_delete', mid=m.id) }}" onsubmit="return confirm('Видалити матеріал? Він зникне й у класах.')">""" + CSRF + """<button class="tp-btn danger small">Видалити</button></form></div></div>{% endfor %}</div>
  {% else %}<p class="muted">Матеріалів ще немає.</p>{% endif %}
</section>"""


@bp.route("/teacher/materials")
def materials():
    teacher = teacher_required()
    items = db().execute("SELECT * FROM materials WHERE teacher_id=? ORDER BY id DESC", (teacher["id"],)).fetchall()
    return page("Мої матеріали", MAT_T, items=items)


@bp.post("/teacher/materials/add")
def material_add():
    teacher = teacher_required()
    title = clean(request.form.get("title"), 120)
    description = clean(request.form.get("description"), 600)
    raw_url = request.form.get("url", "").strip()
    upload = request.files.get("file")
    has_file = bool(upload and upload.filename)
    if not title or (not raw_url and not has_file):
        flash("Вкажіть назву та додайте посилання або файл.")
        return redirect(url_for("tp.materials"))
    if raw_url and has_file:
        flash("Додайте щось одне: або посилання, або файл.")
        return redirect(url_for("tp.materials"))
    if has_file:
        try:
            stored, orig = save_upload(upload)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("tp.materials"))
        kind, url = "file", None
    else:
        url = safe_url(raw_url)
        if not url:
            flash("Посилання має починатися з http:// або https://.")
            return redirect(url_for("tp.materials"))
        stored = orig = None
        kind = "embed" if embed_url(url) else "link"
    db().execute("INSERT INTO materials(teacher_id,title,description,kind,url,stored,orig,created) VALUES(?,?,?,?,?,?,?,?)",
                 (teacher["id"], title, description, kind, url, stored, orig, now()))
    db().commit()
    flash("Матеріал додано.")
    return redirect(url_for("tp.materials"))


@bp.post("/teacher/materials/<int:mid>/delete")
def material_delete(mid):
    teacher = teacher_required()
    row = db().execute("SELECT * FROM materials WHERE id=? AND teacher_id=?", (mid, teacher["id"])).fetchone()
    if not row:
        abort(404)
    remove_file(row["stored"])
    db().execute("DELETE FROM assignments WHERE material_id=?", (mid,))
    db().execute("DELETE FROM materials WHERE id=?", (mid,))
    db().commit()
    return redirect(url_for("tp.materials"))


def material_access(mid):
    """Повертає матеріал, якщо його може бачити поточний вчитель-власник або учень класу, якому він призначений."""
    row = db().execute("SELECT * FROM materials WHERE id=?", (mid,)).fetchone()
    if not row:
        abort(404)
    teacher = current_teacher()
    if teacher and teacher["id"] == row["teacher_id"]:
        return row
    student = current_student()
    if student and db().execute("SELECT 1 FROM assignments WHERE material_id=? AND class_id=?", (mid, student["class_id"])).fetchone():
        return row
    abort(404)


VIEW_T = """
<section class="tp"><nav class="crumb"><a href="{{ back }}">← Назад</a></nav>
  <h1>{{ m.title }}</h1>{% if m.description %}<p class="lead">{{ m.description }}</p>{% endif %}
  {% if embed %}<iframe src="{{ embed }}" title="{{ m.title }}" loading="lazy" allowfullscreen referrerpolicy="no-referrer" sandbox="allow-scripts allow-same-origin allow-presentation allow-popups"></iframe>
    <p class="hint" style="margin-top:8px"><a href="{{ m.url }}" target="_blank" rel="noopener noreferrer nofollow">Відкрити в окремій вкладці ↗</a></p>
  {% elif m.kind == 'link' %}<p><a class="tp-btn" href="{{ m.url }}" target="_blank" rel="noopener noreferrer nofollow">Відкрити матеріал ↗</a></p><p class="hint">Зовнішній сайт: {{ host }}</p>
  {% elif ext == 'pdf' %}<iframe class="pdf" src="{{ url_for('tp.material_file', mid=m.id) }}" title="{{ m.title }}"></iframe>
  {% elif ext in ('png','jpg','jpeg') %}<img src="{{ url_for('tp.material_file', mid=m.id) }}" alt="{{ m.title }}" style="max-width:100%;border-radius:14px;border:1px solid var(--line)">
  {% else %}<p><a class="tp-btn" href="{{ url_for('tp.material_file', mid=m.id) }}">⬇ Завантажити {{ m.orig }}</a></p>{% endif %}
</section>"""


@bp.route("/m/<int:mid>")
def material_view(mid):
    m = material_access(mid)
    ext = m["stored"].rsplit(".", 1)[-1] if m["stored"] else ""
    embed = embed_url(m["url"]) if m["url"] else None
    back = url_for("tp.materials") if current_teacher() else url_for("tp.my_class")
    return page(m["title"], VIEW_T, m=m, ext=ext, embed=embed, back=back,
                host=urlparse(m["url"]).netloc if m["url"] else "")


@bp.route("/f/m/<int:mid>")
def material_file(mid):
    m = material_access(mid)
    if not m["stored"]:
        abort(404)
    return serve_file(m["stored"], m["orig"])


@bp.route("/f/s/<int:sub_id>")
def submission_file(sub_id):
    row = db().execute("SELECT sb.*, c.teacher_id, s.class_id, a.kind FROM submissions sb JOIN students s ON s.id=sb.student_id "
                       "JOIN classes c ON c.id=s.class_id JOIN assignments a ON a.id=sb.assignment_id WHERE sb.id=?", (sub_id,)).fetchone()
    if not row or not row["stored"]:
        abort(404)
    teacher, student = current_teacher(), current_student()
    same_class_gallery = bool(student and student["class_id"] == row["class_id"] and row["kind"] == "project"
                              and row["showcase_requested"] and row["showcase_approved"])
    if (teacher and teacher["id"] == row["teacher_id"]) or (student and student["id"] == row["student_id"]) or same_class_gallery:
        return serve_file(row["stored"], row["orig"])
    abort(404)


# ───────────────────────── учні ─────────────────────────
JOIN_T = FLASH + """
<section class="tp"><p class="eyebrow">ДЛЯ УЧНІВ</p><h1>Приєднатися до класу</h1>
  <p class="lead">Введи код, який дав учитель, і своє ім’я. Електронна пошта не потрібна.</p>
  <form class="stack" method="post" action="{{ url_for('tp.join') }}">""" + CSRF + """
    <label>Код класу<input name="code" required maxlength="6" autocomplete="off" style="text-transform:uppercase;letter-spacing:.2em" value="{{ code or '' }}"></label>
    <label>Ім’я або псевдонім<input name="nick" required maxlength="30" autocomplete="off"><span class="hint">Домовся з учителем, як підписуватися. Прізвище й контакти вказувати не треба.</span></label>
    <label>PIN (лише якщо вже заходив раніше)<input name="pin" inputmode="numeric" maxlength="6" autocomplete="off"></label>
    <button class="tp-btn" type="submit">Далі</button></form>
  <p class="muted" style="margin-top:14px;font-size:14.82px"><a href="{{ url_for('tp.platform_privacy') }}">Приватність у класах</a></p></section>"""

PIN_T = """
<section class="tp"><h1>Ласкаво просимо, {{ nick }}!</h1>
  <div class="tp-card"><p>Твій особистий PIN:</p><div class="code">{{ pin }}</div>
  <p style="margin-top:10px"><strong>Запиши його.</strong> Він потрібен, щоб зайти в клас з іншого пристрою. Повторно показати PIN неможливо — але вчитель може видати новий.</p></div>
  <p style="margin-top:18px"><a class="tp-btn" href="{{ url_for('tp.my_class') }}">Перейти до класу →</a></p></section>"""


@bp.route("/join", methods=["GET", "POST"])
def join():
    if request.method == "GET":
        return page("Приєднатися до класу", JOIN_T, code=request.args.get("code", "")[:6].upper())
    if throttled("join:" + (request.remote_addr or ""), limit=15):
        abort(400, "Забагато спроб. Спробуйте за кілька хвилин.")
    code = request.form.get("code", "").strip().upper()
    nick = clean(request.form.get("nick"), 30)
    pin = request.form.get("pin", "").strip()
    klass = db().execute("SELECT * FROM classes WHERE code=?", (code,)).fetchone()
    if not klass or len(nick) < 2:
        flash("Не вдалося приєднатися. Перевір код, ім’я або PIN.")
        return redirect(url_for("tp.join"))
    existing = next((s for s in db().execute("SELECT * FROM students WHERE class_id=?", (klass["id"],))
                     if s["nick"].casefold() == nick.casefold()), None)
    if existing:
        if not pin or not check_password_hash(existing["pin"], pin):
            flash("Не вдалося приєднатися. Перевір код, ім’я або PIN. Якщо це перший вхід, спробуй інше ім’я.")
            return redirect(url_for("tp.join"))
        session.clear()
        session["student_id"] = existing["id"]
        session.permanent = True
        return redirect(url_for("tp.my_class"))
    count = db().execute("SELECT COUNT(*) FROM students WHERE class_id=?", (klass["id"],)).fetchone()[0]
    if count >= 60:
        flash("У цьому класі вже максимальна кількість учнів.")
        return redirect(url_for("tp.join"))
    new_pin = f"{secrets.randbelow(1_000_000):06d}"
    cur = db().execute("INSERT INTO students(class_id,nick,pin,created) VALUES(?,?,?,?)",
                       (klass["id"], nick, hash_secret(new_pin), now()))
    db().commit()
    session.clear()
    session["student_id"] = cur.lastrowid
    session.permanent = True
    return page("Твій PIN", PIN_T, nick=nick, pin=new_pin)


MY_T = FLASH + """
<section class="tp"><p class="eyebrow">МІЙ КЛАС</p><h1 data-no-translate>{{ st.class_name }}</h1>
  <p class="lead">Привіт, <span data-no-translate>{{ st.nick }}</span>! Тут завдання від вчителя.</p>
  {% if not items %}<p class="muted">Завдань поки немає.</p>{% endif %}
  <div style="display:grid;gap:12px">{% for it in items %}<div class="tp-card">
    <span class="pill">{{ {'lesson':'тема','material':'матеріал','project':'проєкт','homework':'домашнє завдання'}[it.a.kind] }}</span>
    {% if it.late %}<span class="pill" style="background:#fff0e8;color:#96573f">термін минув</span>{% endif %}
    <h3 style="margin-top:8px">{{ it.a.title }}</h3>{% if it.a.due %}<p>Термін: {{ it.a.due }}</p>{% endif %}
    {% if it.a.kind == 'lesson' %}
      <p>{{ it.status|safe }}</p><a class="tp-btn small" href="{{ url_for('lesson_page', subject_slug=it.a.subject_slug, lesson_id=it.a.lesson_id, grade=it.a.grade) }}">Відкрити тему →</a>
    {% elif it.a.kind == 'material' %}<a class="tp-btn small" href="{{ url_for('tp.material_view', mid=it.a.material_id) }}">Відкрити матеріал →</a>
    {% elif it.a.kind == 'homework' %}{% if it.a.description %}<p class="homework-description">{{ it.a.description }}</p>{% endif %}
      {% if it.a.subject_slug and it.a.lesson_id %}<p><a href="{{ url_for('lesson_page', subject_slug=it.a.subject_slug, lesson_id=it.a.lesson_id, grade=it.a.grade) }}">Переглянути пояснення до теми →</a></p>{% elif it.a.subject_slug %}<p><a href="{{ url_for('subject_page', slug=it.a.subject_slug, grade=it.a.grade) }}">Відкрити предмет →</a></p>{% endif %}
      {% if it.sub %}<p class="ok">Відповідь надіслано ✓</p>{% if it.sub.stored %}<p><a href="{{ url_for('tp.submission_file', sub_id=it.sub.id) }}">Мій прикріплений файл: {{ it.sub.orig }}</a></p>{% endif %}{% if it.sub.reviewed %}<div class="tp-card" style="margin:8px 0"><strong>Відгук учителя</strong><p data-no-translate>{{ it.sub.teacher_feedback or 'Учитель переглянув відповідь.' }}</p></div>{% elif it.sub.teacher_feedback %}<p class="muted" data-no-translate>Відгук: {{ it.sub.teacher_feedback }}</p>{% endif %}{% else %}<p class="muted">Відповідь ще не надіслано</p>{% endif %}
      <details {{ 'open' if not it.sub else '' }}><summary>{{ 'Змінити відповідь' if it.sub else 'Написати відповідь' }}</summary>
        <form class="stack" method="post" enctype="multipart/form-data" action="{{ url_for('tp.submit_homework', aid=it.a.id) }}" style="margin-top:8px">""" + CSRF + """
          <label>Твоя відповідь<textarea name="answer" rows="5" maxlength="4000" placeholder="Запиши розв’язання або коротко поясни свою думку">{{ it.sub.answer if it.sub else '' }}</textarea></label>
          <label>Фото або файл роботи (необов’язково)<input type="file" name="file" accept=".pdf,.pptx,.docx,.xlsx,.png,.jpg,.jpeg"></label><span class="hint">Можна надіслати текст, файл або обидва. До 15 МБ.</span>
          <button class="tp-btn small" type="submit">{{ 'Оновити відповідь' if it.sub else 'Надіслати вчителю' }}</button></form></details>
    {% else %}{% if it.a.description %}<p>{{ it.a.description }}</p>{% endif %}
      {% if it.sub %}<p class="ok">Здано ✓ {% if it.sub.url %}<a href="{{ it.sub.url }}" target="_blank" rel="noopener noreferrer nofollow">твоє посилання</a>{% endif %}{% if it.sub.stored %} <a href="{{ url_for('tp.submission_file', sub_id=it.sub.id) }}">{{ it.sub.orig }}</a>{% endif %}</p>{% endif %}
      <details {{ '' if it.sub else 'open' }}><summary>{{ 'Здати ще раз' if it.sub else 'Здати проєкт' }}</summary>
        <form class="stack" method="post" enctype="multipart/form-data" action="{{ url_for('tp.submit_project', aid=it.a.id) }}" style="margin-top:8px">""" + CSRF + """
          <label>Посилання на роботу<input type="url" name="url" placeholder="https://…"></label>
          <label>…або файл (PDF, PPTX, DOCX, PNG, JPG — до 15 МБ)<input type="file" name="file" accept=".pdf,.pptx,.docx,.xlsx,.png,.jpg,.jpeg"></label>
          <label>Коментар для вчителя<input name="note" maxlength="200"></label>
          <label><span><input type="checkbox" name="showcase" value="1"> Попросити додати роботу до галереї класу</span></label>
          <p class="hint">Галерею побачать лише учні цього класу й учитель. Не додавай прізвище, обличчя, адресу чи контакти; учитель має схвалити показ.</p>
          <label>Псевдонім у галереї (необов’язково)<input name="showcase_name" maxlength="30" placeholder="Наприклад, Автор роботи"></label>
          <button class="tp-btn small" type="submit">Надіслати вчителю</button></form></details>
    {% endif %}</div>{% endfor %}</div>
  <section id="personal-notes" class="tp-card" style="margin-top:24px">
    <h2 style="margin-top:0">📝 Мій нотатник</h2>
    <p>Нотатки прив’язані до твого кабінету: учитель та інші учні не бачать їх у класі. Не записуй тут паролі, адресу чи особисті контакти.</p>
    <form class="stack" method="post" action="{{ url_for('tp.student_note_create') }}">""" + CSRF + """
      <label>Назва<input name="title" required maxlength="120" placeholder="Наприклад, Формули руху"></label>
      <label>Текст нотатки<textarea name="body" required maxlength="5000" rows="4" placeholder="Запиши головну думку, формулу чи запитання…"></textarea></label>
      <button class="tp-btn small" type="submit">Зберегти нотатку</button></form>
    {% if notes %}<div class="tp-grid" style="margin-top:16px">{% for note in notes %}<article class="tp-card">
      <form class="stack" method="post" action="{{ url_for('tp.student_note_update', note_id=note.id) }}">""" + CSRF + """
        <label>Назва<input name="title" required maxlength="120" value="{{ note.title }}"></label>
        <label>Текст<textarea name="body" required maxlength="5000" rows="5">{{ note.body }}</textarea></label>
        <p class="hint">Оновлено: {{ note.updated }}</p><button class="tp-btn small" type="submit">Зберегти зміни</button></form>
      <form method="post" action="{{ url_for('tp.student_note_delete', note_id=note.id) }}" style="margin-top:8px">""" + CSRF + """<button class="tp-btn danger small" type="submit">Видалити</button></form>
    </article>{% endfor %}</div>{% else %}<p class="muted">Тут з’являться твої особисті нотатки.</p>{% endif %}
  </section>
  <section class="tp-card" style="margin-top:24px"><h2 style="margin-top:0">🖼️ Галерея проєктів класу</h2>
    <p>Тут лише роботи, для яких автор попросив показ і які схвалив учитель. Галерею бачать учасники цього класу після входу.</p>
    {% if gallery %}<div class="tp-grid">{% for item in gallery %}<article class="tp-card"><p class="eyebrow">{{ item.display_name }} · {{ item.created }}</p><h3>{{ item.title }}</h3>
      {% if item.url %}<p><a href="{{ item.url }}" target="_blank" rel="noopener noreferrer nofollow">Відкрити роботу ↗</a></p>{% endif %}
      {% if item.stored %}<p><a href="{{ url_for('tp.submission_file', sub_id=item.id) }}">Відкрити файл: {{ item.orig }}</a></p>{% endif %}
    </article>{% endfor %}</div>{% else %}<p class="muted">Схвалених робіт поки немає. Твій учитель може додати першу.</p>{% endif %}
  </section>
  <h2>Мої оцінки</h2>{% if own_grades %}<div class="scroll"><table><thead><tr><th>Предмет і робота</th><th>Бали</th><th>Коментар</th></tr></thead><tbody>{% for g in own_grades %}<tr><td>{{ g.subject }} · {{ g.title }}</td><td><strong>{{ g.score }}/{{ g.max_score }}</strong></td><td>{{ g.note or '—' }}</td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="muted">Оцінок поки немає.</p>{% endif %}
  <h2>Моя відвідуваність</h2>{% if own_attendance %}<div class="scroll"><table><thead><tr><th>Дата</th><th>Статус</th></tr></thead><tbody>{% for a in own_attendance %}<tr><td>{{ a.day }}</td><td>{{ {'present':'Присутній','absent':'Відсутній','late':'Запізнився','excused':'Поважна причина'}[a.status] }}</td></tr>{% endfor %}</tbody></table></div>{% else %}<p class="muted">Записів поки немає.</p>{% endif %}
  <form method="post" action="{{ url_for('tp.leave') }}" style="margin-top:24px">""" + CSRF + """<button class="tp-btn ghost small">Вийти з класу</button></form>
</section>"""


@bp.route("/my-class")
def my_class():
    st = current_student()
    if not st:
        return redirect(url_for("tp.join"))
    d = db()
    best = {}
    for r in d.execute("SELECT * FROM results WHERE student_id=?", (st["id"],)):
        key = (r["grade"], r["subject_slug"], r["lesson_id"])
        if key not in best or r["score"] > best[key]["score"]:
            best[key] = r
    subs = {x["assignment_id"]: x for x in d.execute("SELECT * FROM submissions WHERE student_id=?", (st["id"],))}
    today = datetime.now().strftime("%Y-%m-%d")
    items = []
    for a in d.execute("SELECT * FROM assignments WHERE class_id=? ORDER BY id DESC", (st["class_id"],)):
        status, done = "<span class='muted'>Ще не виконано</span>", False
        if a["kind"] == "lesson":
            r = best.get((a["grade"], a["subject_slug"], a["lesson_id"]))
            if r:
                done = r["score"] >= passing(r["total"])
                status = (f"<span class='ok'>Зараховано: {r['score']}/{r['total']} ✓</span>" if done
                          else f"<span class='warn'>Результат {r['score']}/{r['total']} — спробуй ще раз</span>")
        elif a["kind"] in ("project", "homework"):
            done = a["id"] in subs
        items.append({"a": a, "status": status, "sub": subs.get(a["id"]),
                      "late": bool(a["due"] and a["due"] < today and not done and a["kind"] != "material")})
    gallery = d.execute(
        "SELECT sb.id,sb.url,sb.stored,sb.orig,sb.created,a.title,"
        "COALESCE(NULLIF(sb.showcase_name,''),'Учасник класу') AS display_name "
        "FROM submissions sb JOIN assignments a ON a.id=sb.assignment_id JOIN students s ON s.id=sb.student_id "
        "WHERE s.class_id=? AND a.class_id=? AND a.kind='project' "
        "AND sb.showcase_requested=1 AND sb.showcase_approved=1 ORDER BY sb.id DESC LIMIT 30",
        (st["class_id"], st["class_id"]),
    ).fetchall()
    own_grades = d.execute("SELECT subject,title,score,max_score,note,created FROM grade_entries WHERE class_id=? AND student_id=? ORDER BY id DESC LIMIT 50", (st["class_id"], st["id"])).fetchall()
    own_attendance = d.execute("SELECT day,status FROM attendance WHERE class_id=? AND student_id=? ORDER BY day DESC LIMIT 30", (st["class_id"], st["id"])).fetchall()
    notes = d.execute("SELECT id,title,body,updated FROM student_notes WHERE student_id=? ORDER BY updated DESC,id DESC LIMIT ?",
                      (st["id"], MAX_PERSONAL_NOTES)).fetchall()
    return page("Мій клас", MY_T, st=st, items=items, own_grades=own_grades, own_attendance=own_attendance, notes=notes, gallery=gallery)


def _current_student_or_redirect():
    student = current_student()
    if not student:
        return None
    return student


@bp.post("/my-class/notes")
def student_note_create():
    student = _current_student_or_redirect()
    if not student:
        return redirect(url_for("tp.join"))
    title = clean(request.form.get("title"), MAX_NOTE_TITLE)
    body = clean_lines(request.form.get("body"), MAX_NOTE_BODY)
    if not title or not body:
        flash("Додай назву й текст нотатки.")
        return redirect(url_for("tp.my_class") + "#personal-notes")
    count = db().execute("SELECT COUNT(*) FROM student_notes WHERE student_id=?", (student["id"],)).fetchone()[0]
    if count >= MAX_PERSONAL_NOTES:
        flash("У нотатнику вже 100 записів. Видали непотрібну нотатку й спробуй ще раз.")
        return redirect(url_for("tp.my_class") + "#personal-notes")
    stamp = now()
    db().execute("INSERT INTO student_notes(student_id,title,body,created,updated) VALUES(?,?,?,?,?)",
                 (student["id"], title, body, stamp, stamp))
    db().commit()
    flash("Нотатку збережено у твоєму кабінеті.")
    return redirect(url_for("tp.my_class") + "#personal-notes")


@bp.post("/my-class/notes/<int:note_id>/save")
def student_note_update(note_id):
    student = _current_student_or_redirect()
    if not student:
        return redirect(url_for("tp.join"))
    note = db().execute("SELECT id FROM student_notes WHERE id=? AND student_id=?", (note_id, student["id"])).fetchone()
    if not note:
        abort(404)
    title = clean(request.form.get("title"), MAX_NOTE_TITLE)
    body = clean_lines(request.form.get("body"), MAX_NOTE_BODY)
    if not title or not body:
        flash("Назва й текст нотатки не можуть бути порожніми.")
        return redirect(url_for("tp.my_class") + "#personal-notes")
    db().execute("UPDATE student_notes SET title=?,body=?,updated=? WHERE id=? AND student_id=?",
                 (title, body, now(), note_id, student["id"]))
    db().commit()
    flash("Зміни до нотатки збережено.")
    return redirect(url_for("tp.my_class") + "#personal-notes")


@bp.post("/my-class/notes/<int:note_id>/delete")
def student_note_delete(note_id):
    student = _current_student_or_redirect()
    if not student:
        return redirect(url_for("tp.join"))
    cursor = db().execute("DELETE FROM student_notes WHERE id=? AND student_id=?", (note_id, student["id"]))
    if not cursor.rowcount:
        abort(404)
    db().commit()
    flash("Нотатку видалено.")
    return redirect(url_for("tp.my_class") + "#personal-notes")


@bp.route("/my-class/calendar.json")
def student_calendar_items():
    """Повертає лише терміни завдань класу, до якого увійшов поточний учень."""
    student = current_student()
    if not student:
        response = jsonify([])
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Robots-Tag"] = "noindex"
        return response
    rows = db().execute(
        "SELECT id, title, due FROM assignments WHERE class_id=? AND due IS NOT NULL AND due!='' ORDER BY due, id",
        (student["class_id"],),
    ).fetchall()
    events = db().execute("SELECT id,title,event_date FROM class_events WHERE class_id=? ORDER BY event_date,id", (student["class_id"],)).fetchall()
    response = jsonify([
        {"id": f"class-{row['id']}", "title": row["title"], "date": row["due"], "class_assignment": True}
        for row in rows
    ] + [{"id": f"event-{event['id']}", "title": event["title"], "date": event["event_date"], "class_assignment": True, "event": True} for event in events])
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex"
    return response


@bp.post("/my-class/homework/<int:aid>/submit")
def submit_homework(aid):
    st = current_student()
    if not st:
        return redirect(url_for("tp.join"))
    assignment = db().execute(
        "SELECT id FROM assignments WHERE id=? AND class_id=? AND kind='homework'",
        (aid, st["class_id"]),
    ).fetchone()
    if not assignment:
        abort(404)
    answer = clean_lines(request.form.get("answer"), 4000)
    upload = request.files.get("file")
    has_file = bool(upload and upload.filename)
    d = db()
    old = d.execute(
        "SELECT stored,orig FROM submissions WHERE assignment_id=? AND student_id=?",
        (aid, st["id"]),
    ).fetchone()
    if not answer and not has_file and not (old and old["stored"]):
        flash("Напиши відповідь або прикріпи файл перед надсиланням.")
        return redirect(url_for("tp.my_class"))
    stored, orig = (old["stored"], old["orig"]) if old else (None, None)
    if has_file:
        try:
            stored, orig = save_upload(upload)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("tp.my_class"))
    d.execute(
        "INSERT INTO submissions(assignment_id,student_id,answer,stored,orig,created) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(assignment_id,student_id) DO UPDATE SET answer=excluded.answer,stored=excluded.stored,orig=excluded.orig,created=excluded.created,teacher_feedback='',reviewed=NULL",
        (aid, st["id"], answer, stored, orig, now()),
    )
    d.commit()
    if has_file and old and old["stored"]:
        remove_file(old["stored"])
    flash("Відповідь надіслано вчителю.")
    return redirect(url_for("tp.my_class"))


@bp.post("/teacher/class/<int:class_id>/homework/<int:aid>/review/<int:sid>")
def review_homework(class_id, aid, sid):
    _teacher, klass = owned_class(class_id)
    d = db()
    assignment = d.execute("SELECT id FROM assignments WHERE id=? AND class_id=? AND kind='homework'", (aid, klass["id"])).fetchone()
    submission = d.execute("SELECT sb.id FROM submissions sb JOIN students s ON s.id=sb.student_id WHERE sb.assignment_id=? AND sb.student_id=? AND s.class_id=?",
                           (aid, sid, klass["id"])).fetchone()
    if not assignment or not submission:
        abort(404)
    feedback = clean_lines(request.form.get("feedback"), 1000)
    d.execute("UPDATE submissions SET teacher_feedback=?,reviewed=? WHERE id=?",
              (feedback, now(), submission["id"]))
    d.commit()
    flash("Відгук збережено. Учень побачить його у своєму кабінеті.")
    return redirect(url_for("tp.class_page", class_id=klass["id"]))


@bp.post("/my-class/homework/<int:aid>/toggle")
def homework_toggle(aid):
    """Сумісність зі старими відкритими сторінками: попередня дія лише позначала виконання."""
    st = current_student()
    if not st:
        return redirect(url_for("tp.join"))
    assignment = db().execute("SELECT id FROM assignments WHERE id=? AND class_id=? AND kind='homework'", (aid, st["class_id"])).fetchone()
    if not assignment:
        abort(404)
    db().execute("INSERT OR IGNORE INTO submissions(assignment_id,student_id,created) VALUES(?,?,?)", (aid, st["id"], now()))
    db().commit()
    return redirect(url_for("tp.my_class"))

@bp.post("/my-class/submit/<int:aid>")
def submit_project(aid):
    st = current_student()
    if not st:
        return redirect(url_for("tp.join"))
    a = db().execute("SELECT * FROM assignments WHERE id=? AND class_id=? AND kind='project'", (aid, st["class_id"])).fetchone()
    if not a:
        abort(404)
    raw_url = request.form.get("url", "").strip()
    upload = request.files.get("file")
    has_file = bool(upload and upload.filename)
    if raw_url == "" and not has_file:
        flash("Додай посилання або файл.")
        return redirect(url_for("tp.my_class"))
    url = safe_url(raw_url) if raw_url else None
    if raw_url and not url:
        flash("Посилання має починатися з http:// або https://.")
        return redirect(url_for("tp.my_class"))
    stored = orig = None
    if has_file:
        try:
            stored, orig = save_upload(upload)
        except ValueError as error:
            flash(str(error))
            return redirect(url_for("tp.my_class"))
    old = db().execute("SELECT stored FROM submissions WHERE assignment_id=? AND student_id=?", (aid, st["id"])).fetchone()
    if old:
        remove_file(old["stored"])
    requested = 1 if request.form.get("showcase") == "1" else 0
    showcase_name = clean(request.form.get("showcase_name"), 30) if requested else ""
    db().execute("INSERT INTO submissions(assignment_id,student_id,url,stored,orig,note,created,showcase_requested,showcase_approved,showcase_name) VALUES(?,?,?,?,?,?,?,?,0,?) "
                 "ON CONFLICT(assignment_id,student_id) DO UPDATE SET url=excluded.url, stored=excluded.stored, orig=excluded.orig, note=excluded.note, created=excluded.created, showcase_requested=excluded.showcase_requested, showcase_approved=0, showcase_name=excluded.showcase_name",
                 (aid, st["id"], url, stored, orig, clean(request.form.get("note"), 200), now(), requested, showcase_name))
    db().commit()
    flash("Роботу надіслано вчителю.")
    return redirect(url_for("tp.my_class"))


@bp.post("/teacher/class/<int:class_id>/submission/<int:sub_id>/showcase")
def review_showcase(class_id, sub_id):
    _, klass = owned_class(class_id)
    row = db().execute(
        "SELECT sb.id,sb.showcase_requested FROM submissions sb "
        "JOIN assignments a ON a.id=sb.assignment_id JOIN students s ON s.id=sb.student_id "
        "WHERE sb.id=? AND a.class_id=? AND a.kind='project' AND s.class_id=?",
        (sub_id, klass["id"], klass["id"]),
    ).fetchone()
    if not row:
        abort(404)
    approve = request.form.get("approve") == "1" and bool(row["showcase_requested"])
    db().execute("UPDATE submissions SET showcase_approved=? WHERE id=?", (1 if approve else 0, sub_id))
    db().commit()
    flash("Роботу додано до галереї класу." if approve else "Показ роботи в галереї вимкнено.")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/my-class/leave")
def leave():
    session.clear()
    return redirect(url_for("tp.join"))


@bp.post("/lesson-issue")
def report_lesson_issue():
    if throttled("lesson-issue:" + (request.remote_addr or ""), limit=12, window=3600):
        abort(400, "Забагато повідомлень. Спробуйте пізніше.")
    try:
        grade = int(request.form.get("grade", ""))
        lesson_id = int(request.form.get("lesson_id", ""))
    except (TypeError, ValueError):
        abort(400, "Не вдалося визначити тему.")
    slug = clean(request.form.get("subject"), 60)
    category = request.form.get("category", "")
    message = clean_lines(request.form.get("message"), 700)
    subject = CTX["get_subject"](slug, grade) if grade in CTX["grades"] else None
    if not subject or lesson_id < 1 or lesson_id > len(subject["lessons"]) or category not in {"unclear", "error", "illustration"} or not message:
        abort(400, "Перевірте тему й повідомлення.")
    db().execute("INSERT INTO lesson_issue_reports(grade,subject_slug,lesson_id,category,message,created) VALUES(?,?,?,?,?,?)",
                 (grade, slug, lesson_id, category, message, now()))
    db().commit()
    flash("Дякуємо! Повідомлення надіслано на перевірку.")
    return redirect(url_for("lesson_page", subject_slug=slug, lesson_id=lesson_id, grade=grade) + "#report-lesson-issue")


@bp.route("/teacher/content-reports")
def content_reports():
    teacher_required()
    rows = db().execute("SELECT * FROM lesson_issue_reports ORDER BY reviewed IS NOT NULL, id DESC LIMIT 250").fetchall()
    reports = []
    for row in rows:
        item = dict(row)
        subject = CTX["get_subject"](row["subject_slug"], row["grade"])
        item["subject_name"] = subject["name"] if subject else row["subject_slug"]
        item["lesson_title"] = subject["lessons"][row["lesson_id"] - 1]["title"] if subject and 0 < row["lesson_id"] <= len(subject["lessons"]) else f"Тема {row['lesson_id']}"
        reports.append(item)
    return page("Повідомлення про теми", """
    <section class="tp"><nav class="crumb"><a href="{{ url_for('tp.dashboard') }}">Кабінет</a>　/　Повідомлення</nav>
    <h1>Повідомлення про теми</h1><p class="lead">Переглядай відмічені помилки й незрозумілі пояснення. Учні надсилають їх без імені та контактів.</p>
    {% if reports %}{% for item in reports %}<article class="tp-card" style="margin:12px 0"><div class="row"><span class="pill">{{ {'unclear':'Незрозуміле пояснення','error':'Можлива помилка','illustration':'Малюнок або приклад'}[item.category] }}</span><span class="muted">{{ item.created }} · {{ item.grade }} клас · {{ item.subject_name }} · {{ item.lesson_title }}</span>{% if item.reviewed %}<span class="pill">Переглянуто {{ item.reviewed }}</span>{% endif %}</div><p class="issue-message" data-no-translate>{{ item.message }}</p>{% if not item.reviewed %}<form method="post" action="{{ url_for('tp.content_report_review', rid=item.id) }}">""" + CSRF + """<button class="tp-btn small" type="submit">Позначити переглянутим</button></form>{% endif %}</article>{% endfor %}{% else %}<p>Повідомлень поки немає.</p>{% endif %}</section>""", reports=reports)


@bp.post("/teacher/content-reports/<int:rid>/review")
def content_report_review(rid):
    teacher_required()
    cur = db().execute("UPDATE lesson_issue_reports SET reviewed=? WHERE id=? AND reviewed IS NULL", (now(), rid))
    db().commit()
    if not cur.rowcount:
        flash("Повідомлення вже переглянуте або його не знайдено.")
    return redirect(url_for("tp.content_reports"))


PRIV_T = """
<section class="tp"><h1>Приватність у класах</h1>
  <p class="lead">Основна частина «Розумника» працює без облікових записів. Ця сторінка стосується лише класів — вона діє, якщо вчитель створив клас, а учень приєднався за кодом.</p>
  <h2>Що зберігається на сервері</h2>
  <ul><li><strong>Учні:</strong> ім’я чи псевдонім, який учень ввів сам, хеш PIN, клас, до якого він приєднався.</li>
  <li><strong>Результати:</strong> оцінки за контрольні, оцінки вчителя та відвідуваність у межах класу.</li>
  <li><strong>Завдання:</strong> текстові відповіді на домашні роботи, відгуки вчителя, а також посилання чи файли проєктів; відповідь бачить учень і вчитель його класу.</li>
  <li><strong>Особисті нотатки:</strong> назва й текст зберігаються в кабінеті відповідного учня; у кабінеті вчителя вони не показуються.</li>
  <li><strong>Вчителі:</strong> ім’я, електронна пошта, хеш пароля, створені класи й матеріали.</li></ul>
  <h2>Чого ми не збираємо</h2>
  <p>Електронної пошти, телефону, адреси чи прізвища учнів. Просимо вчителів та учнів не вказувати зайвих персональних даних у іменах, нотатках і файлах.</p>
  <h2>Видалення</h2>
  <p>Вчитель може видалити окремого учня (разом з результатами, роботами й нотатками) або весь клас. Видалення остаточне.</p>
  <h2>Хто що бачить</h2>
  <p>Учень бачить власні оцінки, відвідуваність і нотатки. Учитель бачить завдання й результати учнів лише у своєму класі; особисті нотатки йому не показуються. Інші учні не мають доступу до чужих оцінок, відвідуваності, нотаток або надісланих файлів.</p>
  <p class="muted" style="font-size:14.82px">Пароль учителя зберігається у вигляді захищеного хешу, а не відкритим текстом. Електронна пошта вчителя потрібна для входу; не використовуй той самий пароль, що й на пошті.</p>
  <p class="muted" style="font-size:14.82px">Ця сторінка — пояснення для користувачів, а не юридичний висновок. Перш ніж запроваджувати платформу у школі, узгодьте умови обробки даних зі школою.</p>
</section>"""


@bp.route("/classes-privacy")
def platform_privacy():
    return page("Приватність у класах", PRIV_T)


# ───────────────────────── підключення ─────────────────────────
def init_platform(app, show_page, grades, get_subject, get_lesson):
    if "tp" in app.blueprints:  # уже підключено (наприклад, двічі викликано)
        return
    CTX.update(show_page=show_page, grades=grades, get_subject=get_subject, get_lesson=get_lesson)
    if not app.secret_key:
        key = os.environ.get("SECRET_KEY")
        if not key:
            print("УВАГА: не задано SECRET_KEY — сесії вчителів і учнів скидатимуться після перезапуску.")
            key = secrets.token_hex(32)
        app.secret_key = key
    app.config.setdefault("MAX_CONTENT_LENGTH", MAX_UPLOAD + 1024 * 1024)
    public_url = os.environ.get("PUBLIC_BASE_URL", "") or os.environ.get("RENDER_EXTERNAL_URL", "")
    secure_cookie = public_url.lower().startswith("https://")
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=10), SESSION_REFRESH_EACH_REQUEST=False,
                      SESSION_COOKIE_SECURE=secure_cookie)
    app.jinja_env.globals["csrf_token"] = csrf_token
    with app.app_context():
        conn = sqlite3.connect(os.path.join(data_dir(), "rozumnyk.db"))
        conn.executescript(SCHEMA)
        submission_columns = {row[1] for row in conn.execute("PRAGMA table_info(submissions)")}
        for column, declaration in (("answer", "TEXT NOT NULL DEFAULT ''"),
                                    ("teacher_feedback", "TEXT NOT NULL DEFAULT ''"),
                                    ("reviewed", "TEXT"),
                                    ("showcase_requested", "INTEGER NOT NULL DEFAULT 0"),
                                    ("showcase_approved", "INTEGER NOT NULL DEFAULT 0"),
                                    ("showcase_name", "TEXT NOT NULL DEFAULT '")):
            if column not in submission_columns:
                conn.execute(f"ALTER TABLE submissions ADD COLUMN {column} {declaration}")
        conn.commit()
        conn.close()

    @app.teardown_appcontext
    def close_db(_exc):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.after_request
    def private_pages(response):
        if request.path.startswith(("/teacher", "/my-class", "/join", "/m/", "/f/")):
            response.headers["Cache-Control"] = "private, no-store"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if secure_cookie:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return response

    app.register_blueprint(bp)

    # Посилання «Вчителям» у шапці та «Вхід до класу» в підвалі — без правок app.py.
    module = sys.modules.get(getattr(show_page, "__module__", ""))
    shell = getattr(module, "SHELL", None)
    if isinstance(shell, str) and "tp.teacher_home" not in shell:
        link = '<a class="utility-link" href="{{ url_for(\'tp.teacher_home\') }}">👩‍🏫 Вчителям</a>'
        if '<a class="progress-link"' in shell:
            shell = shell.replace('<a class="progress-link"', link + '<a class="progress-link"', 1)
        if "</footer>" in shell:
            shell = shell.replace("</footer>", " · <a href=\"{{ url_for('tp.join') }}\">Вхід до класу</a></footer>", 1)
        module.SHELL = shell

    # Сторінка приватності: пояснюємо виняток для класів.
    original_privacy = app.view_functions.get("privacy_page")
    if original_privacy:
        def privacy_with_classes():
            html = original_privacy()
            marker = "<h2>Що сайт зберігає в браузері</h2>"
            note = ('<div class="privacy-callout"><p><strong>Виняток — класи.</strong> Якщо вчитель створив клас, а учень '
                    'приєднався за кодом, результати контрольних і здані роботи зберігаються на сервері й доступні вчителю. '
                    'Докладніше — <a href="/classes-privacy">«Приватність у класах»</a>.</p></div>')
            if isinstance(html, str) and marker in html:
                html = html.replace(marker, note + marker, 1)
            return html
        app.view_functions["privacy_page"] = privacy_with_classes

    original_quiz = app.view_functions["quiz"]

    def quiz_with_results(subject_slug, lesson_id):
        response = original_quiz(subject_slug, lesson_id)
        student = current_student()
        if student:
            try:
                grade = int(request.args.get("grade", "5"))
                subject = get_subject(subject_slug, grade)
                lesson = get_lesson(subject, lesson_id)
                answers = [request.form.get(f"answer_{i}", "") for i in range(len(lesson["control_work"]))]
                score = sum(a == str(q["answer"]) for a, q in zip(answers, lesson["control_work"]))
                db().execute("INSERT INTO results(student_id,grade,subject_slug,lesson_id,score,total,created) VALUES(?,?,?,?,?,?,?)",
                             (student["id"], grade, subject_slug, lesson_id, score, len(lesson["control_work"]), now()))
                db().commit()
            except Exception:  # збій запису не повинен ламати контрольну
                pass
        return response

    app.view_functions["quiz"] = quiz_with_results


def seed_demo(app, password=None):
    """Створює демо-клас з учнями й результатами для показу (python seed_demo.py)."""
    import random
    rnd = random.Random(7)
    with app.app_context():
        d = db()
        email = "demo@rozumnyk.example"
        password = password or secrets.token_urlsafe(9)
        d.execute("DELETE FROM teachers WHERE email=?", (email,))
        tid = d.execute("INSERT INTO teachers(email,name,pw,created) VALUES(?,?,?,?)",
                        (email, "Демо-вчитель", hash_secret(password), now())).lastrowid
        cid = d.execute("INSERT INTO classes(teacher_id,name,grade,code,created) VALUES(?,?,?,?,?)",
                        (tid, "9-А (демо)", 9, new_code(), now())).lastrowid
        subject = get_subject_safe("algebra")
        picks = [(subject["slug"], i) for i in (1, 2, 3, 4)]
        for slug, lid in picks:
            title = f"{subject['name']}: {subject['lessons'][lid - 1]['title']}"
            d.execute("INSERT INTO assignments(class_id,kind,title,grade,subject_slug,lesson_id,due,created) VALUES(?,?,?,?,?,?,?,?)",
                      (cid, "lesson", title, 9, slug, lid, None, now()))
        aid = d.execute("INSERT INTO assignments(class_id,kind,title,description,created) VALUES(?,?,?,?,?)",
                        (cid, "project", "Проєкт: наша спільна презентація", "Підготуйте 5 слайдів і здайте посилання.", now())).lastrowid
        for n in range(1, 13):
            sid = d.execute("INSERT INTO students(class_id,nick,pin,created) VALUES(?,?,?,?)",
                            (cid, f"Учень {n}", hash_secret("000000"), now())).lastrowid
            for slug, lid in picks:
                if rnd.random() < 0.8:
                    d.execute("INSERT INTO results(student_id,grade,subject_slug,lesson_id,score,total,created) VALUES(?,?,?,?,?,?,?)",
                              (sid, 9, slug, lid, rnd.randint(5, 12), 12, now()))
            if rnd.random() < 0.5:
                d.execute("INSERT INTO submissions(assignment_id,student_id,url,note,created) VALUES(?,?,?,?,?)",
                          (aid, sid, "https://example.com/demo", "", now()))
        d.commit()
        code = d.execute("SELECT code FROM classes WHERE id=?", (cid,)).fetchone()[0]
    print(f"Демо створено. Пошта: {email}  Код класу: {code}" + ("" if os.environ.get("DEMO_PASSWORD") else f"  Пароль: {password}"))
    return code


def get_subject_safe(slug):
    return CTX["get_subject"](slug, 9)
