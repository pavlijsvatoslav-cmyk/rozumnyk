import React, { useState } from "react";
import { pageUrl, PROGRESS_KEY, readProgress, recordMistakes, topicKey } from "./state.js";

async function checkAnswers(grade, items) {
  const response = await fetch("/api/quiz", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grade, items }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Не вдалося перевірити відповіді.");
  return data;
}

export { checkAnswers };

export default function QuizCard({ grade, slug, lessonId, questions }) {
  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  if (!questions.length) return <aside className="quiz-card"><p className="eyebrow">ПЕРЕВІР СЕБЕ</p><h2>Тест скоро з’явиться</h2><p>Поки що повтори пояснення й приклад цієї теми.</p></aside>;

  async function finish(finalAnswers) {
    if (submitting || result) return;
    setSubmitting(true); setError("");
    const items = finalAnswers.map((choiceIndex, index) => ({ subjectSlug: slug, lessonId, questionIndex: index, choiceIndex: Number(choiceIndex) }));
    try {
      const data = await checkAnswers(grade, items);
      setResult(data);
      recordMistakes(grade, questions.map((questionData, questionIndex) => ({ subjectSlug: slug, lessonId, questionIndex, questionData })), data);
      if (data.passed) {
        const progress = readProgress();
        progress[topicKey(grade, slug, lessonId)] = { passed: true, score: data.score, total: data.total, at: Date.now() };
        localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
        window.dispatchEvent(new Event("rozumnyk-progress"));
      }
    } catch (failure) {
      setError(failure.message || "З’єднання перервалося. Спробуй перевірити тест ще раз.");
    } finally {
      setSubmitting(false);
    }
  }

  function choose(index) {
    if (result || submitting || answers[step] !== undefined) return;
    const updated = answers.slice(); updated[step] = index; setAnswers(updated);
    window.setTimeout(() => {
      if (step + 1 < questions.length) setStep((value) => value + 1);
      else finish(updated);
    }, 300);
  }

  function retry() { setStep(0); setAnswers([]); setResult(null); setError(""); }

  return <aside className="quiz-card" aria-live="polite">
    <p className="eyebrow">КОНТРОЛЬНА · {questions.length} ЗАПИТАНЬ</p>
    <h2>{result ? "Твій результат" : "Перевір, що запам’яталося"}</h2>
    {!result && <>
      <p className="quiz-intro">Обери відповідь — і перейдемо далі. Наприкінці побачиш результат і розбір помилок.</p>
      <div className="quiz-progress"><span style={{width:((step+1)/questions.length*100)+"%"}}/></div>
      <p className="quiz-count">Запитання {Math.min(step+1,questions.length)} з {questions.length}</p>
      {submitting ? <div className="quiz-wait"><span className="pulse-dot"/>Перевіряємо відповіді…</div> : <fieldset className="quiz-question" disabled={answers[step]!==undefined}><legend>{questions[step]?.question}</legend><div className="quiz-options">{(questions[step]?.options||[]).map((option,index)=><label className={answers[step]===index?"selected":""} key={index}><input type="radio" name={"quiz-"+step} checked={answers[step]===index} onChange={()=>choose(index)}/><span>{option}</span></label>)}</div></fieldset>}
    </>}
    {error && <div className="quiz-error" role="alert"><p>{error}</p><button className="button button-small" onClick={()=>finish(answers)}>Перевірити ще раз</button></div>}
    {result && <div className="quiz-result"><div className={"score-medallion "+(result.passed?"score-pass":"score-try")}><strong>{result.score}</strong><span>з {result.total}</span></div><p>{result.passed?"Чудово! Наступна тема вже відкрита.":"Потрібно щонайменше "+result.required+" правильних відповідей. Переглянь пояснення й спробуй ще раз."}</p><div className="answer-review">{result.review.map((item,index)=>!item.correct&&<article key={index}><strong>{index+1}. {questions[index]?.question}</strong><span>Правильна відповідь: {questions[index]?.options?.[item.correctOption]}</span></article>)}</div>{result.passed?<a className="button button-primary" href={pageUrl("/subject/"+slug,grade)}>Повернутися до тем →</a>:<button className="button button-primary" onClick={retry}>Пройти тест ще раз ↺</button>}</div>}
  </aside>;
}
