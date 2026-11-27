import answerBank from "../data/answers.json";

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store",
  "X-Content-Type-Options": "nosniff",
};

function respond(payload, status = 200) {
  return new Response(JSON.stringify(payload), { status, headers: JSON_HEADERS });
}

export async function onRequestPost({ request }) {
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) {
    return respond({ error: "Запит відхилено." }, 403);
  }

  const contentType = request.headers.get("Content-Type") || "";
  const lengthHeader = request.headers.get("Content-Length");
  const size = lengthHeader === null ? 0 : Number(lengthHeader);
  if (!contentType.toLowerCase().includes("application/json") ||
      !Number.isFinite(size) || size < 0 || size > 24_000) {
    return respond({ error: "Некоректний формат відповіді." }, 400);
  }

  let body;
  try {
    const reader = request.body?.getReader();
    if (!reader) return respond({ error: "Не вдалося прочитати відповіді." }, 400);
    const chunks = [];
    let total = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > 24_000) {
        await reader.cancel();
        return respond({ error: "Відповідь завелика." }, 413);
      }
      chunks.push(value);
    }
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    body = JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    return respond({ error: "Не вдалося прочитати відповіді." }, 400);
  }

  const grade = Number(body?.grade);
  const items = body?.items;
  if (!Number.isInteger(grade) || grade < 5 || grade > 11 ||
      !Array.isArray(items) || items.length < 1 || items.length > 120) {
    return respond({ error: "У тесті є некоректні дані." }, 400);
  }

  const gradeBank = answerBank[String(grade)];
  if (!gradeBank) return respond({ error: "Для цього класу тест недоступний." }, 404);

  const review = [];
  for (let index = 0; index < items.length; index += 1) {
    const item = items[index];
    const slug = typeof item?.subjectSlug === "string" ? item.subjectSlug : "";
    const lessonId = Number(item?.lessonId);
    const questionIndex = Number(item?.questionIndex);
    const choiceIndex = Number(item?.choiceIndex);
    if (!/^[a-z0-9-]{1,80}$/.test(slug) ||
        !Number.isInteger(lessonId) || lessonId < 1 ||
        !Number.isInteger(questionIndex) || questionIndex < 0 ||
        !Number.isInteger(choiceIndex) || choiceIndex < -1 || choiceIndex > 5) {
      return respond({ error: "Одна з відповідей має некоректний формат." }, 400);
    }

    const lesson = gradeBank[slug]?.[lessonId - 1];
    const correctOption = lesson?.control?.[questionIndex];
    if (!Number.isInteger(correctOption)) {
      return respond({ error: "Для одного із запитань немає ключа перевірки." }, 400);
    }
    review.push({
      index,
      correct: choiceIndex >= 0 && choiceIndex === correctOption,
      correctOption,
    });
  }

  const score = review.filter((item) => item.correct).length;
  const gradeThreshold = grade >= 8 ? 0.75 : 0.8;
  const required = Math.ceil(items.length * gradeThreshold);
  return respond({
    score,
    total: items.length,
    required,
    passed: score >= required,
    review,
  });
}

export function onRequestGet() {
  return respond({ error: "Використай кнопку завершення тесту." }, 405);
}
