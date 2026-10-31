"""Quick smoke checks for the public Flask pages in every configured grade.

Run from the project folder with: py work\\route_check.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from curriculum import GRADES


client = app.test_client()
failures = []
checked = {"home": 0, "subject": 0, "lesson": 0, "quiz": 0, "tools": 0}


def check(path, *, grade, category, method="get", data=None, expected=200):
    response = getattr(client, method)(path, query_string={"grade": grade}, data=data)
    checked[category] += 1
    if response.status_code != expected:
        failures.append(
            f"grade={grade} {method.upper()} {path}: "
            f"expected {expected}, got {response.status_code}"
        )
    return response


for grade, subjects in sorted(GRADES.items()):
    check("/", grade=grade, category="home")

    for subject in subjects:
        slug = subject["slug"]
        lessons = subject["lessons"]
        check(f"/subject/{slug}", grade=grade, category="subject")

        # Check both ends of each course without rendering every generated lesson.
        sample_ids = sorted({1, len(lessons)})
        for lesson_id in sample_ids:
            check(f"/lesson/{slug}/{lesson_id}", grade=grade, category="lesson")

    # Exercise one complete quiz per grade, including the grade-specific question count.
    first_subject = subjects[0]
    first_lesson = first_subject["lessons"][0]
    question_count = len(first_lesson["control_work"])
    answers = {f"answer_{index}": "0" for index in range(question_count)}
    quiz_response = check(
        f"/quiz/{first_subject['slug']}/1",
        grade=grade,
        category="quiz",
        method="post",
        data=answers,
    )
    expected_count = "12 ЗАПИТАНЬ" if grade >= 8 else "5 ЗАПИТАНЬ"
    if expected_count.encode("utf-8") not in quiz_response.data:
        failures.append(
            f"grade={grade} quiz shows an unexpected control-work size; "
            f"expected {expected_count}"
        )

    for path in ("/progress", "/study-items", "/learning-tools", "/career-guide"):
        check(path, grade=grade, category="tools")

    check("/subject/__missing_subject__", grade=grade, category="subject", expected=404)
    check("/lesson/__missing_subject__/1", grade=grade, category="lesson", expected=404)


print("Checked pages:", ", ".join(f"{name}={count}" for name, count in checked.items()))
print("Failures:", failures)
if failures:
    raise SystemExit(1)
