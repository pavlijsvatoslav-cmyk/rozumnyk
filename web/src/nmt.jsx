import React, { useEffect, useRef, useState } from "react";
import { pageUrl } from "./state.js";
import { checkAnswers } from "./quiz.jsx";
import { recordMistakes } from "./state.js";

const CORE = ["ukr-mova","algebra","history-ukraine"];

export function NmtPage({grade,catalog}) {
  const [optional,setOptional]=useState("");
  const [started,setStarted]=useState(false);
  const [questions,setQuestions]=useState([]);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState("");
  const subjects=catalog["11"]||[];
  const electives=subjects.filter(subject=>!CORE.includes(subject.slug));
  async function start() {
    if(!optional)return;
    setLoading(true);setError("");
    try {
      const list=await Promise.all(CORE.concat(optional).map(async slug=>{
        const response=await fetch("/data/subjects/11/"+encodeURIComponent(slug)+".json");
        if(!response.ok)throw new Error("Не вдалося завантажити теми обраного предмета.");
        return response.json();
      }));
      const picked=[];
      list.forEach(subject=>{
        const bank=[];
        (subject.lessons||[]).forEach((lesson,index)=>(lesson.control_work||[]).forEach((question,qindex)=>bank.push({subjectSlug:subject.slug,lessonId:index+1,questionIndex:qindex,question,subjectName:subject.name})));
        for(let i=0;i<5&&bank.length;i++){const n=Math.floor(Math.random()*bank.length);picked.push(bank.splice(n,1)[0]);}
      });
      if(picked.length<4)throw new Error("Для цих предметів поки недостатньо запитань.");
      setQuestions(picked);setStarted(true);
    } catch(failure) {setError(failure.message||"Не вдалося підготувати тест.");}
    finally {setLoading(false);}
  }
  if(grade!==11)return <section className="locked-card"><p className="eyebrow">ПІДГОТОВКА ДО НМТ</p><h1>Тренувальний варіант доступний у 11 класі</h1><p>Перейди до 11 класу, щоб відкрити симулятор.</p><a className="button button-primary" href={pageUrl("/",11)}>Перейти до 11 класу →</a></section>;
  return <section className="page-wrap nmt-page"><nav className="crumb"><a href={pageUrl("/",grade)}>Предмети</a><span> / </span><span>Тренувальний НМТ</span></nav>{!started?<><header className="nmt-hero"><p className="eyebrow">ТРЕНУВАЛЬНИЙ ІСПИТ · 120 ХВИЛИН</p><h1>Спробуй формат НМТ у своєму темпі</h1><p>Навчальний варіант бере запитання з тем 11 класу. Це тренування, а не офіційний демонстраційний тест.</p></header><div className="nmt-subject-pick"><h2>Обери предмет на вибір</h2><p>Українська мова, математика та історія України вже входять до тренувального набору.</p><label><span>Предмет на вибір</span><select value={optional} onChange={event=>setOptional(event.target.value)}><option value="">Обери предмет…</option>{electives.map(subject=><option value={subject.slug} key={subject.slug}>{subject.name}</option>)}</select></label><button className="button button-primary" disabled={!optional||loading} onClick={start}>{loading?"Готуємо запитання…":"Почати тренування · 120 хв →"}</button>{error&&<p className="quiz-error" role="alert">{error}</p>}</div></>:<NmtQuiz questions={questions} onRestart={()=>{setStarted(false);setQuestions([]);}}/>}</section>;
}

function NmtQuiz({questions,onRestart}) {
  const [step,setStep]=useState(0);
  const [answers,setAnswers]=useState([]);
  const [result,setResult]=useState(null);
  const [seconds,setSeconds]=useState(7200);
  const [submitting,setSubmitting]=useState(false);
  const [error,setError]=useState("");
  const timedOut=useRef(false);
  useEffect(()=>{
    if(result||submitting)return undefined;
    const timer=window.setInterval(()=>setSeconds(value=>Math.max(0,value-1)),1000);
    return()=>window.clearInterval(timer);
  },[result,submitting]);
  const time=String(Math.floor(seconds/3600)).padStart(2,"0")+":"+String(Math.floor((seconds%3600)/60)).padStart(2,"0")+":"+String(seconds%60).padStart(2,"0");
  async function finish(finalAnswers) {
    if(submitting||result)return;
    setSubmitting(true);setError("");
    try {
      const full=questions.map((_,index)=>finalAnswers[index]===undefined?-1:finalAnswers[index]);
      const items=full.map((choiceIndex,index)=>({subjectSlug:questions[index].subjectSlug,lessonId:questions[index].lessonId,questionIndex:questions[index].questionIndex,choiceIndex}));
      const data=await checkAnswers(11,items);
      recordMistakes(11,questions.map(item=>({subjectSlug:item.subjectSlug,lessonId:item.lessonId,questionIndex:item.questionIndex,questionData:item.question})),data);
      setResult(data);
    } catch(failure) {setError(failure.message||"Не вдалося перевірити результат.");}
    finally {setSubmitting(false);}
  }
  useEffect(()=>{if(seconds===0&&!result&&!submitting&&!timedOut.current){timedOut.current=true;finish(answers);}},[seconds,result,submitting,answers]);
  function choose(index) {
    if(answers[step]!==undefined||result||submitting)return;
    const next=answers.slice();next[step]=index;setAnswers(next);
    window.setTimeout(()=>{if(step+1<questions.length)setStep(value=>value+1);else finish(next);},260);
  }
  if(result)return <div className="nmt-result"><p className="eyebrow">ТРЕНУВАЛЬНИЙ ВАРІАНТ ЗАВЕРШЕНО</p><h2>Твій результат · {result.score} із {result.total}</h2><p>Помилки показані нижче. Це підказка, які теми повторити, а не прогноз офіційного бала НМТ.</p><div className="answer-review">{result.review.map((item,index)=>!item.correct&&<article key={index}><strong>{index+1}. {questions[index].question.question}</strong><small>{questions[index].subjectName}</small><span>Твоя відповідь: {answers[index]===undefined?"Без відповіді":questions[index].question.options[answers[index]]}</span><span>Виправлення: {questions[index].question.options[item.correctOption]}</span></article>)}</div><button className="button button-primary" onClick={onRestart}>Завершити й обрати предмет знову</button></div>;
  const current=questions[step];
  if(!current)return <div className="locked-card"><h2>Не вдалося зібрати запитання.</h2><button className="button" onClick={onRestart}>Назад</button></div>;
  return <div className="nmt-test"><header><div><p className="eyebrow">ЗАПИТАННЯ {step+1} З {questions.length} · {current.subjectName}</p><h2>Тренувальний варіант</h2></div><div className={"exam-clock "+(seconds<600?"clock-warning":"")} aria-label="Час, що залишився">◷ {time}</div></header><div className="quiz-progress"><span style={{width:((step+1)/questions.length*100)+"%"}}/></div><fieldset className="quiz-question" disabled={answers[step]!==undefined}><legend>{current.question.question}</legend><div className="quiz-options">{current.question.options.map((option,index)=><label className={answers[step]===index?"selected":""} key={index}><input type="radio" name="nmt-answer" checked={answers[step]===index} onChange={()=>choose(index)}/><span>{option}</span></label>)}</div></fieldset>{submitting&&<p className="quiz-wait">Перевіряємо результат…</p>}{error&&<div className="quiz-error" role="alert"><p>{error}</p><button className="button button-small" onClick={()=>finish(answers)}>Повторити перевірку</button></div>}</div>;
}
