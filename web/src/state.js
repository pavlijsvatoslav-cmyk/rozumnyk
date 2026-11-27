export const PROGRESS_KEY = "rozumnyk-progress-v3";
export const NOTES_KEY = "rozumnyk-notes-v1";
export const MISTAKES_KEY = "rozumnyk-mistakes-v1";

export function gradeFromUrl() {
  const grade = Number(new URLSearchParams(location.search).get("grade") || 5);
  return Number.isInteger(grade) && grade >= 5 && grade <= 11 ? grade : 5;
}

export function pageUrl(path, grade) {
  return path + (path.includes("?") ? "&" : "?") + "grade=" + grade;
}

export function readProgress() {
  try { return JSON.parse(localStorage.getItem(PROGRESS_KEY) || "{}"); }
  catch { return {}; }
}

export function topicKey(grade, slug, id) {
  return grade + ":" + slug + ":" + id;
}

export function readNotes() {
  try {
    const value = JSON.parse(localStorage.getItem(NOTES_KEY) || "{}");
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  } catch { return {}; }
}

export function readMistakes() {
  try {
    const value = JSON.parse(localStorage.getItem(MISTAKES_KEY) || "[]");
    return Array.isArray(value) ? value : [];
  } catch { return []; }
}

export function recordMistakes(grade, questions, result) {
  try {
    const ids = new Set(questions.map((item) => `${grade}:${item.subjectSlug}:${item.lessonId}:${item.questionIndex}`));
    const remaining = readMistakes().filter((item) => !ids.has(item.id));
    questions.forEach((item, index) => {
      const review = result.review[index];
      if (!review || review.correct) return;
      const question = item.questionData || {};
      remaining.push({
        id: `${grade}:${item.subjectSlug}:${item.lessonId}:${item.questionIndex}`,
        grade,
        subjectSlug: item.subjectSlug,
        lessonId: item.lessonId,
        questionIndex: item.questionIndex,
        question: question.question || "Запитання до теми",
        options: Array.isArray(question.options) ? question.options : [],
        correctIndex: review.correctOption,
      });
    });
    localStorage.setItem(MISTAKES_KEY, JSON.stringify(remaining));
  } catch { /* Quiz results still work if local storage is unavailable. */ }
}
