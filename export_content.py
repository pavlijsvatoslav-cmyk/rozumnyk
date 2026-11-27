"""Export the authored curriculum to small, static course files for Vite.

The Python application runs only while building the site. The deployed site is
served by Cloudflare Pages and does not need a Flask server.
"""
from __future__ import annotations

import json
import ast
from pathlib import Path

import curriculum
from grade9_books import apply_grade9_books
from grade9_more import apply_grade9_more


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "web" / "public" / "data"
SUBJECTS_DIR = PUBLIC / "subjects"
FUNCTION_DATA = ROOT / "functions" / "data"


def json_ready(value):
    """Convert the course's Python structures to portable JSON values."""
    if isinstance(value, dict):
        return {
            str(key): json_ready(item)
            for key, item in value.items()
            if str(key).casefold() not in {"answer", "correct_answer", "answer_index"}
        }
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def read_career_content():
    """Read the authored career constants without importing the Flask app."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        "CAREER_CATEGORIES", "CAREER_3D_DIRECTIONS",
        "CAREER_QUESTION_PROMPTS", "CAREER_OPTION_BANK", "CAREER_QUESTIONS",
    }
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    module = ast.Module(body=[node], type_ignores=[])
                    exec(compile(module, str(ROOT / "app.py"), "exec"), {"__builtins__": {"enumerate": enumerate}, **values}, values)
                    break
    missing = names.difference(values)
    if missing:
        raise RuntimeError("Career content is missing: " + ", ".join(sorted(missing)))
    return values


def main_export():
    apply_grade9_books(curriculum.GRADES, curriculum.rich_lesson)
    apply_grade9_more(curriculum.GRADES, curriculum.rich_lesson)
    curriculum.add_control_works()

    catalog = {}
    answer_bank = {}

    for grade, subjects in sorted(curriculum.GRADES.items()):
        grade_key = str(grade)
        catalog[grade_key] = []
        answer_bank[grade_key] = {}

        for subject in subjects:
            slug = subject["slug"]
            public_subject = json_ready(subject)
            catalog[grade_key].append({
                "slug": slug,
                "name": subject["name"],
                "icon": subject.get("icon", "📘"),
                "area": subject.get("area", ""),
                "description": subject.get("description", ""),
                "nmt_role": subject.get("nmt_role"),
                "reference_book": subject.get("reference_book"),
                "lesson_count": len(subject.get("lessons", [])),
            })
            write_json(
                SUBJECTS_DIR / grade_key / f"{slug}.json",
                public_subject,
            )

            # Keep only numeric keys in the Worker bundle. The question text
            # and choices are public lesson content and are served separately.
            answer_bank[grade_key][slug] = [
                {
                    "mini": lesson.get("answer"),
                    "control": [
                        question.get("answer")
                        for question in lesson.get("control_work", [])
                    ],
                }
                for lesson in subject.get("lessons", [])
            ]

    write_json(PUBLIC / "catalog.json", catalog)
    write_json(FUNCTION_DATA / "answers.json", answer_bank)

    career_content = read_career_content()
    career_data = {
        "categories": career_content["CAREER_CATEGORIES"],
        "directions": career_content["CAREER_3D_DIRECTIONS"],
        "questions": career_content["CAREER_QUESTIONS"],
    }
    write_json(PUBLIC / "careers.json", json_ready(career_data))

    subject_files = list(SUBJECTS_DIR.glob("*/*.json"))
    public_bytes = sum(path.stat().st_size for path in subject_files)
    answers_bytes = (FUNCTION_DATA / "answers.json").stat().st_size
    print(
        f"Exported {sum(len(items) for items in catalog.values())} subjects, "
        f"{sum(item['lesson_count'] for items in catalog.values() for item in items)} lessons; "
        f"{public_bytes:,} bytes of course content; {answers_bytes:,} bytes of private quiz keys."
    )


if __name__ == "__main__":
    main_export()
