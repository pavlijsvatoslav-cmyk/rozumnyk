"""Точка входу для хостингу: gunicorn main:app

Підключає до сайту додаткові теми й кабінет учителя.
"""
import os


def load_local_settings():
    """Read selected development settings; hosted environment variables take precedence."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    allowed = {"SECRET_KEY"}
    try:
        with open(env_path, encoding="utf-8") as env_file:
            for line in env_file:
                name, separator, value = line.partition("=")
                name = name.strip()
                if separator and name in allowed and not os.environ.get(name):
                    value = value.strip().strip('"').strip("'")
                    if value:
                        os.environ[name] = value
    except OSError:
        return


load_local_settings()

import curriculum
from grade9_books import apply_grade9_books
from grade9_more import apply_grade9_more

apply_grade9_books(curriculum.GRADES, curriculum.rich_lesson)
apply_grade9_more(curriculum.GRADES, curriculum.rich_lesson)
curriculum.add_control_works()  # контрольні для нових тем (для решти тем результат той самий)

from app import GRADES, app, get_lesson, get_subject, show_page  # noqa: E402
# Учительський кабінет тимчасово вимкнений. Його можна повернути,
# встановивши ENABLE_TEACHER_PLATFORM=1 у змінних середовища.
if os.environ.get("ENABLE_TEACHER_PLATFORM") == "1":
    from teacher_platform import data_dir, init_platform, seed_demo  # noqa: E402

    init_platform(app, show_page, GRADES, get_subject, get_lesson)

from cosmic_theme import apply_cosmic_theme  # noqa: E402

apply_cosmic_theme(app, show_page)

# Демо-клас створюється лише тоді, коли ввімкнений кабінет учителя.
if (os.environ.get("ENABLE_TEACHER_PLATFORM") == "1" and
        os.environ.get("DEMO_PASSWORD") and
        not os.path.exists(os.path.join(data_dir(), ".demo_seeded"))):
    seed_demo(app, password=os.environ["DEMO_PASSWORD"])
    open(os.path.join(data_dir(), ".demo_seeded"), "w").close()

if __name__ == "__main__":
    app.run(debug=True)
