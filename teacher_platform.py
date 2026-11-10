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
import io
import os
import re
import secrets
import shutil
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

from flask import (Blueprint, abort, flash, g, redirect, request, send_file,
                   session, url_for, Response)
from werkzeug.security import check_password_hash, generate_password_hash

bp = Blueprint("tp", __name__)

ALLOWED_EXT = {
    "pdf": b"%PDF", "pptx": b"PK\x03\x04", "docx": b"PK\x03\x04", "xlsx": b"PK\x03\x04",
    "png": b"\x89PNG", "jpg": b"\xff\xd8\xff", "jpeg": b"\xff\xd8\xff",
}
INLINE_EXT = {"pdf", "png", "jpg", "jpeg"}
MAX_UPLOAD = 15 * 1024 * 1024
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

SCHEMA = """
CREATE TABLE IF NOT EXISTS teachers(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, pw TEXT NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE, name TEXT NOT NULL, grade INTEGER NOT NULL, code TEXT UNIQUE NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, nick TEXT NOT NULL, pin TEXT NOT NULL, created TEXT NOT NULL, UNIQUE(class_id, nick));
CREATE TABLE IF NOT EXISTS materials(id INTEGER PRIMARY KEY, teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, url TEXT, stored TEXT, orig TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE, kind TEXT NOT NULL, title TEXT NOT NULL, grade INTEGER, subject_slug TEXT, lesson_id INTEGER, material_id INTEGER REFERENCES materials(id) ON DELETE SET NULL, description TEXT NOT NULL DEFAULT '', due TEXT, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, grade INTEGER NOT NULL, subject_slug TEXT NOT NULL, lesson_id INTEGER NOT NULL, score INTEGER NOT NULL, total INTEGER NOT NULL, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY, assignment_id INTEGER NOT NULL REFERENCES assignments(id) ON DELETE CASCADE, student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE, url TEXT, stored TEXT, orig TEXT, note TEXT NOT NULL DEFAULT '', created TEXT NOT NULL, UNIQUE(assignment_id, student_id));
CREATE INDEX IF NOT EXISTS idx_results_student ON results(student_id);
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


def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]


def page(title, template, **values):
    values.setdefault("robots_noindex", True)
    values["css"] = PCSS
    return CTX["show_page"](title, "{{ css|safe }}" + template, **values)


_attempts = {}


def throttled(key, limit=8, window=600):
    stamp = time.time()
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
.tp{max-width:980px;margin:0 auto}.tp h1{font-size:clamp(30px,5vw,44px);letter-spacing:-.04em;line-height:1.1;margin:8px 0 14px}.tp h2{font-size:22px;letter-spacing:-.02em;margin:34px 0 12px}.tp h3{margin:0 0 6px;font-size:16px}
.tp .lead{font-size:17px;color:#4a5866;max-width:700px}.tp-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
.tp-card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px 20px}.tp-card p{margin:4px 0;color:#566471;font-size:14px}
.tp-btn{display:inline-block;background:var(--green);color:#fff;text-decoration:none;border:0;border-radius:11px;padding:10px 17px;font:700 14px inherit;cursor:pointer}.tp-btn:hover{background:var(--green-dark)}
.tp-btn.ghost{background:#fff;color:var(--green);border:1px solid var(--green)}.tp-btn.danger{background:#fff;color:#a23b2a;border:1px solid #e3b4aa}.tp-btn.small{padding:6px 11px;font-size:12px}
.tp form.stack{display:grid;gap:11px;max-width:520px}.tp label{display:grid;gap:4px;font-size:13px;font-weight:700;color:#33424f}
.tp input,.tp select,.tp textarea{font:inherit;font-size:15px;padding:9px 11px;border:1px solid #cfd6cc;border-radius:10px;background:#fff;width:100%}.tp textarea{min-height:80px}
.tp .hint{font-size:12px;color:var(--muted);font-weight:400}.tp .flash{background:#fff4dc;border:1px solid #f0dfae;border-radius:12px;padding:11px 15px;margin:10px 0;font-size:14px}
.tp .code{font:800 34px/1 ui-monospace,Consolas,monospace;letter-spacing:.18em;background:#e4eee5;border-radius:12px;padding:12px 18px;display:inline-block}
.tp table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13px}.tp th,.tp td{padding:9px 11px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}.tp th{background:#f1f4ee;font-size:12px}
.tp .ok{color:#28633d;font-weight:800}.tp .warn{color:#96573f;font-weight:700}.tp .muted{color:var(--muted)}.tp .scroll{overflow-x:auto}.tp .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.tp iframe{width:100%;aspect-ratio:16/9;border:1px solid var(--line);border-radius:14px;background:#fff}.tp .pdf{aspect-ratio:auto;height:75vh}
.tp .pill{display:inline-block;font-size:11px;font-weight:800;border-radius:99px;padding:2px 9px;background:#e4eee5;color:var(--green-dark)}.tp details{margin:8px 0}.tp summary{cursor:pointer;font-weight:700}
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
        <label>Електронна пошта<input type="email" name="email" required autocomplete="username"></label>
        <label>Пароль<input type="password" name="password" required autocomplete="current-password"></label>
        <button class="tp-btn" type="submit">Увійти</button></form></div>
    <div class="tp-card"><h2 style="margin-top:0">Зареєструватися</h2>
      <form class="stack" method="post" action="{{ url_for('tp.teacher_register') }}">""" + CSRF + """
        <label>Ім’я та по батькові<input name="name" required maxlength="80" autocomplete="name"></label>
        <label>Електронна пошта<input type="email" name="email" required autocomplete="username"></label>
        <label>Пароль<input type="password" name="password" required minlength="8" autocomplete="new-password"><span class="hint">Щонайменше 8 символів</span></label>
        {% if invite %}<label>Код запрошення<input name="invite" required><span class="hint">Отримайте його в автора проєкту</span></label>{% endif %}
        <button class="tp-btn" type="submit">Створити кабінет</button></form></div>
  </div>
  <p class="muted" style="margin-top:20px;font-size:13px">Учні вказують лише ім’я або псевдонім. Докладніше — на сторінці <a href="{{ url_for('tp.platform_privacy') }}">«Приватність у класах»</a>.</p>
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
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) or len(password) < 8:
        flash("Перевірте ім’я, пошту й пароль (мінімум 8 символів).")
        return redirect(url_for("tp.teacher_home"))
    if db().execute("SELECT 1 FROM teachers WHERE email=?", (email,)).fetchone():
        flash("Користувач із такою поштою вже існує. Спробуйте увійти.")
        return redirect(url_for("tp.teacher_home"))
    cur = db().execute("INSERT INTO teachers(email,name,pw,created) VALUES(?,?,?,?)",
                       (email, name, generate_password_hash(password), now()))
    db().commit()
    session.clear()
    session["teacher_id"] = cur.lastrowid
    return redirect(url_for("tp.dashboard"))


@bp.post("/teacher/login")
def teacher_login():
    email = clean(request.form.get("email"), 120).lower()
    if throttled(f"login:{request.remote_addr}:{email}", limit=8):
        abort(400, "Забагато спроб входу. Спробуйте за кілька хвилин.")
    row = db().execute("SELECT * FROM teachers WHERE email=?", (email,)).fetchone()
    if not row or not check_password_hash(row["pw"], request.form.get("password", "")):
        flash("Невірна пошта або пароль.")
        return redirect(url_for("tp.teacher_home"))
    session.clear()
    session["teacher_id"] = row["id"]
    return redirect(url_for("tp.dashboard"))


@bp.post("/teacher/logout")
def teacher_logout():
    session.clear()
    return redirect(url_for("tp.teacher_home"))


DASH_T = FLASH + """
<section class="tp">
  <p class="eyebrow">КАБІНЕТ ВЧИТЕЛЯ</p>
  <div class="row" style="justify-content:space-between"><h1>Вітаємо, {{ teacher.name }}</h1>
    <form method="post" action="{{ url_for('tp.teacher_logout') }}">""" + CSRF + """<button class="tp-btn ghost small">Вийти</button></form></div>
  <h2>Мої класи</h2>
  {% if classes %}<div class="tp-grid">{% for c in classes %}
    <a class="tp-card" style="text-decoration:none;color:inherit" href="{{ url_for('tp.class_page', class_id=c.id) }}">
      <h3>{{ c.name }}</h3><p>{{ c.grade }} клас · учнів: {{ c.n }}</p><p>Код: <strong>{{ c.code }}</strong></p></a>{% endfor %}</div>
  {% else %}<p class="muted">Класів ще немає. Створіть перший — і отримаєте код для учнів.</p>{% endif %}
  <h2>Створити клас</h2>
  <form class="stack" method="post" action="{{ url_for('tp.class_create') }}">""" + CSRF + """
    <label>Назва класу<input name="name" required maxlength="60" placeholder="Наприклад, 9-А"></label>
    <label>Клас навчання<select name="grade">{% for g in grades %}<option value="{{ g }}" {{ 'selected' if g == 9 }}>{{ g }} клас</option>{% endfor %}</select></label>
    <button class="tp-btn" type="submit">Створити клас</button></form>
  <h2>Мої матеріали</h2>
  <p>Презентації, проєкти й посилання, які ви можете призначати класам. <a href="{{ url_for('tp.materials') }}">Відкрити бібліотеку →</a> (матеріалів: {{ n_materials }})</p>
</section>"""


@bp.route("/teacher/dashboard")
def dashboard():
    teacher = teacher_required()
    classes = db().execute(
        "SELECT c.*, (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id) AS n "
        "FROM classes c WHERE teacher_id=? ORDER BY c.id DESC", (teacher["id"],)).fetchall()
    n_materials = db().execute("SELECT COUNT(*) FROM materials WHERE teacher_id=?", (teacher["id"],)).fetchone()[0]
    return page("Кабінет вчителя", DASH_T, teacher=teacher, classes=classes,
                grades=sorted(CTX["grades"]), n_materials=n_materials)


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
  <nav class="crumb"><a href="{{ url_for('tp.dashboard') }}">Кабінет</a>　/　{{ klass.name }}</nav>
  <h1>{{ klass.name }} <span class="pill">{{ klass.grade }} клас</span></h1>
  <div class="tp-card"><p>Код класу для учнів:</p><div class="code">{{ klass.code }}</div>
    <p style="margin-top:10px">Учні відкривають <strong>{{ join_url }}</strong>, вводять код та своє ім’я.</p>
    <div class="row"><form method="post" action="{{ url_for('tp.class_newcode', class_id=klass.id) }}">""" + CSRF + """<button class="tp-btn ghost small">Новий код</button></form>
    <a class="tp-btn ghost small" href="{{ url_for('tp.class_csv', class_id=klass.id) }}">⬇ Звіт CSV</a></div></div>

  <h2>Звіт по класу</h2>
  {% if not students %}<p class="muted">Поки немає учнів. Дайте їм код класу.</p>
  {% elif not columns %}<p class="muted">Призначте завдання нижче — і тут з’являться результати.</p>
  {% else %}<div class="scroll"><table><thead><tr><th>Учень</th>{% for a in columns %}<th title="{{ a.title }}">{{ a.title[:34] }}{{ '…' if a.title|length > 34 }}{% if a.due %}<br><span class="muted">до {{ a.due }}</span>{% endif %}</th>{% endfor %}<th>Зараховано</th></tr></thead><tbody>
    {% for row in rows %}<tr><td><strong>{{ row.student.nick }}</strong></td>{% for cell in row.cells %}<td>{{ cell|safe }}</td>{% endfor %}<td><strong>{{ row.done }}</strong> із {{ columns|length }}</td></tr>{% endfor %}
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

  <h2>Додати матеріал або проєктне завдання</h2>
  <div class="tp-grid">
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

  <h2>Завдання класу</h2>
  {% if assignments %}<table><tbody>{% for a in assignments %}<tr><td><span class="pill">{{ {'lesson':'тема','material':'матеріал','project':'проєкт'}[a.kind] }}</span> {{ a.title }}{% if a.due %} <span class="muted">· до {{ a.due }}</span>{% endif %}
    {% if a.kind == 'project' %}<br><span class="muted">Здано: {{ subs.get(a.id, 0) }}</span> {% for sb in sublist.get(a.id, []) %}<br>· {{ sb.nick }}: {% if sb.url %}<a href="{{ sb.url }}" target="_blank" rel="noopener noreferrer nofollow">посилання</a>{% endif %}{% if sb.stored %} <a href="{{ url_for('tp.submission_file', sub_id=sb.id) }}">файл ({{ sb.orig }})</a>{% endif %}{% if sb.note %} — {{ sb.note }}{% endif %}{% endfor %}{% endif %}</td>
    <td style="width:90px"><form method="post" action="{{ url_for('tp.assignment_delete', class_id=klass.id, aid=a.id) }}" onsubmit="return confirm('Видалити завдання?')">""" + CSRF + """<button class="tp-btn danger small">Видалити</button></form></td></tr>{% endfor %}</tbody></table>
  {% else %}<p class="muted">Завдань ще немає.</p>{% endif %}

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
    students = d.execute("SELECT * FROM students WHERE class_id=? ORDER BY nick COLLATE NOCASE", (klass["id"],)).fetchall()
    columns = d.execute("SELECT * FROM assignments WHERE class_id=? AND kind IN ('lesson','project') ORDER BY id", (klass["id"],)).fetchall()
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
                cells.append("<span class='ok'>здано ✓</span>" if sb else "<span class='muted'>—</span>")
                plain.append("здано" if sb else "")
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
    catalog = [{"slug": s["slug"], "name": s["name"], "lessons": [l["title"] for l in s["lessons"]]}
               for s in CTX["grades"][klass["grade"]]]
    materials = d.execute("SELECT id,title FROM materials WHERE teacher_id=? ORDER BY id DESC", (teacher["id"],)).fetchall()
    return page(f"Клас {klass['name']}", CLASS_T, klass=klass, students=students, columns=columns, rows=rows,
                assignments=assignments, subs={k: len(v) for k, v in sublist.items()}, sublist=sublist,
                catalog=catalog, materials=materials, join_url=url_for("tp.join", _external=True))


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
    for sb in db().execute("SELECT stored FROM submissions WHERE assignment_id=?", (aid,)):
        remove_file(sb["stored"])
    db().execute("DELETE FROM assignments WHERE id=? AND class_id=?", (aid, klass["id"]))
    db().commit()
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/student/<int:sid>/pin")
def student_pin(class_id, sid):
    _, klass = owned_class(class_id)
    st = db().execute("SELECT * FROM students WHERE id=? AND class_id=?", (sid, klass["id"])).fetchone()
    if not st:
        abort(404)
    pin = f"{secrets.randbelow(10000):04d}"
    db().execute("UPDATE students SET pin=? WHERE id=?", (generate_password_hash(pin), sid))
    db().commit()
    flash(f"Новий PIN для «{st['nick']}»: {pin}. Передайте його учневі — повторно його не буде показано.")
    return redirect(url_for("tp.class_page", class_id=class_id))


@bp.post("/teacher/class/<int:class_id>/student/<int:sid>/delete")
def student_delete(class_id, sid):
    _, klass = owned_class(class_id)
    for sb in db().execute("SELECT stored FROM submissions WHERE student_id=?", (sid,)):
        remove_file(sb["stored"])
    db().execute("DELETE FROM students WHERE id=? AND class_id=?", (sid, klass["id"]))
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
    row = db().execute("SELECT sb.*, c.teacher_id FROM submissions sb JOIN students s ON s.id=sb.student_id "
                       "JOIN classes c ON c.id=s.class_id WHERE sb.id=?", (sub_id,)).fetchone()
    if not row or not row["stored"]:
        abort(404)
    teacher, student = current_teacher(), current_student()
    if (teacher and teacher["id"] == row["teacher_id"]) or (student and student["id"] == row["student_id"]):
        return serve_file(row["stored"], row["orig"])
    abort(404)


# ───────────────────────── учні ─────────────────────────
JOIN_T = FLASH + """
<section class="tp"><p class="eyebrow">ДЛЯ УЧНІВ</p><h1>Приєднатися до класу</h1>
  <p class="lead">Введи код, який дав учитель, і своє ім’я. Електронна пошта не потрібна.</p>
  <form class="stack" method="post" action="{{ url_for('tp.join') }}">""" + CSRF + """
    <label>Код класу<input name="code" required maxlength="6" autocomplete="off" style="text-transform:uppercase;letter-spacing:.2em" value="{{ code or '' }}"></label>
    <label>Ім’я або псевдонім<input name="nick" required maxlength="30" autocomplete="off"><span class="hint">Домовся з учителем, як підписуватися. Прізвище й контакти вказувати не треба.</span></label>
    <label>PIN (лише якщо вже заходив раніше)<input name="pin" inputmode="numeric" maxlength="4" autocomplete="off"></label>
    <button class="tp-btn" type="submit">Далі</button></form>
  <p class="muted" style="margin-top:14px;font-size:13px"><a href="{{ url_for('tp.platform_privacy') }}">Приватність у класах</a></p></section>"""

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
        flash("Перевір код класу та ім’я (щонайменше 2 символи).")
        return redirect(url_for("tp.join"))
    existing = next((s for s in db().execute("SELECT * FROM students WHERE class_id=?", (klass["id"],))
                     if s["nick"].casefold() == nick.casefold()), None)
    if existing:
        if not pin or not check_password_hash(existing["pin"], pin):
            flash("Таке ім’я вже є в класі. Якщо це ти — введи свій PIN. Якщо ні — додай до імені літеру чи цифру.")
            return redirect(url_for("tp.join"))
        session.clear()
        session["student_id"] = existing["id"]
        return redirect(url_for("tp.my_class"))
    count = db().execute("SELECT COUNT(*) FROM students WHERE class_id=?", (klass["id"],)).fetchone()[0]
    if count >= 60:
        flash("У цьому класі вже максимальна кількість учнів.")
        return redirect(url_for("tp.join"))
    new_pin = f"{secrets.randbelow(10000):04d}"
    cur = db().execute("INSERT INTO students(class_id,nick,pin,created) VALUES(?,?,?,?)",
                       (klass["id"], nick, generate_password_hash(new_pin), now()))
    db().commit()
    session.clear()
    session["student_id"] = cur.lastrowid
    return page("Твій PIN", PIN_T, nick=nick, pin=new_pin)


MY_T = FLASH + """
<section class="tp"><p class="eyebrow">МІЙ КЛАС</p><h1>{{ st.class_name }}</h1>
  <p class="lead">Привіт, {{ st.nick }}! Тут завдання від вчителя.</p>
  {% if not items %}<p class="muted">Завдань поки немає.</p>{% endif %}
  <div style="display:grid;gap:12px">{% for it in items %}<div class="tp-card">
    <span class="pill">{{ {'lesson':'тема','material':'матеріал','project':'проєкт'}[it.a.kind] }}</span>
    {% if it.late %}<span class="pill" style="background:#fff0e8;color:#96573f">термін минув</span>{% endif %}
    <h3 style="margin-top:8px">{{ it.a.title }}</h3>{% if it.a.due %}<p>Термін: {{ it.a.due }}</p>{% endif %}
    {% if it.a.kind == 'lesson' %}
      <p>{{ it.status|safe }}</p><a class="tp-btn small" href="{{ url_for('lesson_page', subject_slug=it.a.subject_slug, lesson_id=it.a.lesson_id, grade=it.a.grade) }}">Відкрити тему →</a>
    {% elif it.a.kind == 'material' %}<a class="tp-btn small" href="{{ url_for('tp.material_view', mid=it.a.material_id) }}">Відкрити матеріал →</a>
    {% else %}{% if it.a.description %}<p>{{ it.a.description }}</p>{% endif %}
      {% if it.sub %}<p class="ok">Здано ✓ {% if it.sub.url %}<a href="{{ it.sub.url }}" target="_blank" rel="noopener noreferrer nofollow">твоє посилання</a>{% endif %}{% if it.sub.stored %} <a href="{{ url_for('tp.submission_file', sub_id=it.sub.id) }}">{{ it.sub.orig }}</a>{% endif %}</p>{% endif %}
      <details {{ '' if it.sub else 'open' }}><summary>{{ 'Здати ще раз' if it.sub else 'Здати проєкт' }}</summary>
        <form class="stack" method="post" enctype="multipart/form-data" action="{{ url_for('tp.submit_project', aid=it.a.id) }}" style="margin-top:8px">""" + CSRF + """
          <label>Посилання на роботу<input type="url" name="url" placeholder="https://…"></label>
          <label>…або файл (PDF, PPTX, DOCX, PNG, JPG — до 15 МБ)<input type="file" name="file" accept=".pdf,.pptx,.docx,.xlsx,.png,.jpg,.jpeg"></label>
          <label>Коментар для вчителя<input name="note" maxlength="200"></label>
          <button class="tp-btn small" type="submit">Надіслати вчителю</button></form></details>
    {% endif %}</div>{% endfor %}</div>
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
        elif a["kind"] == "project":
            done = a["id"] in subs
        items.append({"a": a, "status": status, "sub": subs.get(a["id"]),
                      "late": bool(a["due"] and a["due"] < today and not done and a["kind"] != "material")})
    return page("Мій клас", MY_T, st=st, items=items)


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
    db().execute("INSERT INTO submissions(assignment_id,student_id,url,stored,orig,note,created) VALUES(?,?,?,?,?,?,?) "
                 "ON CONFLICT(assignment_id,student_id) DO UPDATE SET url=excluded.url, stored=excluded.stored, orig=excluded.orig, note=excluded.note, created=excluded.created",
                 (aid, st["id"], url, stored, orig, clean(request.form.get("note"), 200), now()))
    db().commit()
    flash("Роботу надіслано вчителю.")
    return redirect(url_for("tp.my_class"))


@bp.post("/my-class/leave")
def leave():
    session.clear()
    return redirect(url_for("tp.join"))


PRIV_T = """
<section class="tp"><h1>Приватність у класах</h1>
  <p class="lead">Основна частина «Розумника» працює без облікових записів. Ця сторінка стосується лише класів — вона діє, якщо вчитель створив клас, а учень приєднався за кодом.</p>
  <h2>Що зберігається на сервері</h2>
  <ul><li><strong>Учні:</strong> ім’я чи псевдонім, який учень ввів сам, хеш PIN, клас, до якого він приєднався.</li>
  <li><strong>Результати:</strong> оцінки за контрольні (бали), якщо учень увійшов у клас; дата проходження.</li>
  <li><strong>Роботи:</strong> посилання чи файли, які учень здав у проєктному завданні; їх бачить лише вчитель класу й сам учень.</li>
  <li><strong>Вчителі:</strong> ім’я, електронна пошта, хеш пароля, створені класи й матеріали.</li></ul>
  <h2>Чого ми не збираємо</h2>
  <p>Електронної пошти, телефону, адреси чи прізвища учнів. Просимо вчителів та учнів не вказувати зайвих персональних даних у іменах, нотатках і файлах.</p>
  <h2>Видалення</h2>
  <p>Вчитель може видалити окремого учня (разом з результатами та роботами) або весь клас. Видалення остаточне.</p>
  <h2>Хто що бачить</h2>
  <p>Результати учня бачить лише вчитель, який створив клас. Інші учні класу чужих результатів не бачать.</p>
  <p class="muted" style="font-size:13px">Ця сторінка — пояснення для користувачів, а не юридичний висновок. Перш ніж запроваджувати платформу у школі, узгодьте умови обробки даних зі школою.</p>
</section>"""


@bp.route("/classes-privacy")
def platform_privacy():
    return page("Приватність у класах", PRIV_T)


# ───────────────────────── підключення ─────────────────────────
def init_platform(app, show_page, grades, get_subject, get_lesson):
    CTX.update(show_page=show_page, grades=grades, get_subject=get_subject, get_lesson=get_lesson)
    if not app.secret_key:
        key = os.environ.get("SECRET_KEY")
        if not key:
            print("УВАГА: не задано SECRET_KEY — сесії вчителів і учнів скидатимуться після перезапуску.")
            key = secrets.token_hex(32)
        app.secret_key = key
    app.config.setdefault("MAX_CONTENT_LENGTH", MAX_UPLOAD + 1024 * 1024)
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_SECURE=os.environ.get("PUBLIC_BASE_URL", "").startswith("https"))
    app.jinja_env.globals["csrf_token"] = csrf_token
    with app.app_context():
        conn = sqlite3.connect(os.path.join(data_dir(), "rozumnyk.db"))
        conn.executescript(SCHEMA)
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
        return response

    app.register_blueprint(bp)

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


def seed_demo(app):
    """Створює демо-клас з учнями й результатами для показу (python seed_demo.py)."""
    import random
    rnd = random.Random(7)
    with app.app_context():
        d = db()
        email = "demo@rozumnyk.example"
        password = secrets.token_urlsafe(9)
        d.execute("DELETE FROM teachers WHERE email=?", (email,))
        tid = d.execute("INSERT INTO teachers(email,name,pw,created) VALUES(?,?,?,?)",
                        (email, "Демо-вчитель", generate_password_hash(password), now())).lastrowid
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
                            (cid, f"Учень {n}", generate_password_hash("0000"), now())).lastrowid
            for slug, lid in picks:
                if rnd.random() < 0.8:
                    d.execute("INSERT INTO results(student_id,grade,subject_slug,lesson_id,score,total,created) VALUES(?,?,?,?,?,?,?)",
                              (sid, 9, slug, lid, rnd.randint(5, 12), 12, now()))
            if rnd.random() < 0.5:
                d.execute("INSERT INTO submissions(assignment_id,student_id,url,note,created) VALUES(?,?,?,?,?)",
                          (aid, sid, "https://example.com/demo", "", now()))
        d.commit()
        code = d.execute("SELECT code FROM classes WHERE id=?", (cid,)).fetchone()[0]
    print(f"Демо створено. Пошта: {email}  Пароль: {password}  Код класу: {code}")


def get_subject_safe(slug):
    return CTX["get_subject"](slug, 9)
