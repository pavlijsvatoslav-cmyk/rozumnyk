import React, { useEffect, useState } from "react";
import { NOTES_KEY, readNotes, topicKey } from "./state.js";

export default function LessonNotes({ grade, slug, lessonId }) {
  const key = topicKey(grade, slug, lessonId);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("Зберігається тільки в цьому браузері.");

  useEffect(() => setNote(String(readNotes()[key] || "")), [key]);
  useEffect(() => {
    const timer = window.setTimeout(() => {
      const notes = readNotes();
      if (note.trim()) notes[key] = note;
      else delete notes[key];
      try {
        localStorage.setItem(NOTES_KEY, JSON.stringify(notes));
        setStatus("Нотатку збережено на цьому пристрої.");
      } catch {
        setStatus("Не вдалося зберегти нотатку. Перевір вільне місце у браузері.");
      }
    }, 350);
    return () => window.clearTimeout(timer);
  }, [note, key]);

  return <section className="lesson-note-panel">
    <p className="eyebrow">ТВОЇ ДУМКИ</p>
    <h2>📝 Моя нотатка до теми</h2>
    <textarea className="lesson-note-input" value={note} onChange={(event) => { setNote(event.target.value); setStatus("Зберігаємо нотатку…"); }} maxLength={4000} placeholder="Запиши важливе правило, запитання або те, що хочеш повторити…" aria-label="Моя нотатка до теми" />
    <p className="note-storage-hint" aria-live="polite">{status} Не записуй тут паролі, адресу електронної пошти чи інші особисті дані.</p>
  </section>;
}
