import React, { useEffect, useState } from "react";
import { CareersPage } from "./careers.jsx";
import { NmtPage } from "./nmt.jsx";
import QuizCard from "./quiz.jsx";
import LessonNotes from "./LessonNotes.jsx";
import { MISTAKES_KEY, pageUrl, PROGRESS_KEY, readMistakes, readNotes, readProgress, topicKey } from "./state.js";

const PLANETS = [
  ["Меркурій", "#b8a8ff", "24", "Найменша планета Сонячної системи. Її поверхня вкрита кратерами.", "88 днів"],
  ["Венера", "#ffc37e", "31", "Густа атмосфера утримує тепло, тому Венера гарячіша за Меркурій.", "225 днів"],
  ["Земля", "#56c9ef", "37", "Рідка вода вкриває більшу частину поверхні Землі.", "365 днів"],
  ["Марс", "#ef836d", "29", "На Марсі є найбільший відомий вулкан Сонячної системи — гора Олімп.", "687 днів"],
  ["Юпітер", "#e8b981", "58", "Велика червона пляма — велетенський шторм, який спостерігають століттями.", "11,9 року"],
  ["Сатурн", "#e9d192", "51", "Його кільця складаються переважно з частинок льоду й каміння.", "29,4 року"],
  ["Уран", "#78e2dc", "42", "Уран обертається навколо своєї осі майже «лежачи на боці».", "84 роки"],
  ["Нептун", "#668df4", "40", "На Нептуні зафіксували надзвичайно швидкі вітри.", "165 років"],
];

export function HomePage({ grade, catalog, progressTick }) {
  const subjects = catalog[String(grade)] || [];
  const [query, setQuery] = useState("");
  const [planetIndex, setPlanetIndex] = useState(2);
  const progress = readProgress();
  const completed = Object.entries(progress).filter(([key, item]) => key.startsWith(grade + ":") && item && item.passed).length;
  const total = subjects.reduce((sum, subject) => sum + subject.lesson_count, 0);
  const visibleSubjects = subjects.filter((item) => item.name.toLocaleLowerCase("uk").includes(query.toLocaleLowerCase("uk")));
  const planet = PLANETS[planetIndex];
  return <>
    <section className="hero cosmic-hero">
      <div className="hero-copy"><p className="eyebrow">ТВОЄ НАВЧАННЯ · ТВОЄ ВІДКРИТТЯ</p><h1>Зрозуміло.<br/><em>Крок за кроком.</em></h1><p className="hero-intro">Предмети, теми, приклади й тести для учнів 5–11 класів. Обирай напрям і вчися у своєму темпі.</p><div className="hero-actions"><a className="button button-primary" href="#subjects">Почати навчання <span>↓</span></a>{grade === 11 && <a className="button button-outline" href={pageUrl("/nmt/simulation", grade)}>Тренувальний НМТ ↗</a>}</div><div className="hero-stats"><div><strong>{subjects.length}</strong><span>предметів у {grade} класі</span></div><div><strong>{total.toLocaleString("uk")}</strong><span>тем для відкриття</span></div><div><strong>{completed}</strong><span>вже пройдено</span></div></div></div>
      <div className="solar-showcase" aria-label="Інтерактивна Сонячна система"><div className="solar-core" aria-hidden="true"><span>☼</span></div><div className="solar-orbit orbit-a"/><div className="solar-orbit orbit-b"/><div className="solar-orbit orbit-c"/>{PLANETS.map((item, index) => <button key={item[0]} className={"orbit-planet planet-" + index + (planetIndex === index ? " is-selected" : "")} style={{"--planet-color":item[1],"--planet-size":item[2]+"px"}} aria-label={"Дізнатися про планету "+item[0]} onClick={() => setPlanetIndex(index)}><span className="planet-ball"/></button>)}<aside className="planet-fact-card" aria-live="polite"><p className="eyebrow">ДОСЛІДЖУЙ КОСМОС</p><h2>{planet[0]}</h2><p>{planet[3]}</p><small>Рік на планеті · {planet[4]}</small></aside></div>
    </section>
    {grade === 11 && <NmtBanner grade={grade} subjects={subjects}/>}
    <section className="continue-card"><div><p className="eyebrow">НАВЧАННЯ У ТВОЄМУ БРАУЗЕРІ</p><h2>{completed ? "Продовжуй відкривати нові теми" : "Почни з теми, яка тебе цікавить"}</h2><p>Після тесту наступна тема відкриється автоматично.</p></div><a className="button button-soft" href="#subjects">Обрати предмет →</a></section>
    <section className="facts-section"><div className="section-heading"><div><p className="eyebrow">НЕОЧІКУВАНО, АЛЕ ПРАВДА</p><h2>Світ цікавіший, ніж здається</h2></div><p>Факти, після яких хочеться запитати: «А чому так?»</p></div><div className="facts-grid"><Fact icon="☀️" tag="КОСМОС" title="Світло теж має час у дорозі" text="Промінь від Сонця летить до Землі приблизно 8 хвилин. Ми бачимо Сонце таким, яким воно було кілька хвилин тому."/><Fact icon="🌊" tag="ОКЕАН" title="Морська сіль — величезний запас" text="Якби сіль з океанів рівномірно розсипати по суші, утворився б шар завтовшки з десятки поверхів."/><Fact icon="📜" tag="ІСТОРІЯ" title="Документ Пилипа Орлика мав дві версії" text="У 1710 році уклали документ із 16 статей. Він мав українську й латинську версії та з’явився в еміграції."/></div></section>
    <section id="subjects" className="subjects-section"><div className="section-heading"><div><p className="eyebrow">ОБИРАЙ, ЩО ЦІКАВО</p><h2>Предмети · {grade} клас</h2></div><p>{subjects.length} напрямів навчання</p></div><label className="search-box"><span aria-hidden="true">⌕</span><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Знайти предмет…" aria-label="Пошук предмета"/></label><div className="subject-grid">{visibleSubjects.map((subject,index)=>{const count=Object.entries(progress).filter(([key,item])=>key.startsWith(grade+":"+subject.slug+":")&&item&&item.passed).length;return <a className="subject-card" style={{"--card-index":index}} key={subject.slug} href={pageUrl("/subject/"+subject.slug,grade)}><div className="subject-card-top"><span className="subject-icon">{subject.icon}</span><span className="card-arrow">↗</span></div><p className="subject-area">{subject.area||"НАВЧАЛЬНИЙ ПРЕДМЕТ"}</p><h3>{subject.name}</h3><p className="subject-description">{subject.description}</p>{grade===11&&subject.nmt_role&&<span className="nmt-tag">НМТ · {subject.nmt_role}</span>}<div className="subject-meta"><span>{subject.lesson_count.toLocaleString("uk")} тем</span><span>{count} / {subject.lesson_count.toLocaleString("uk")}</span></div></a>;})}{!visibleSubjects.length&&<p className="empty-state">Не знайшли предмета з такою назвою.</p>}</div></section>
    <section className="discover-row"><a href={pageUrl("/career-guide",grade)}><span>✦</span><div><small>ПРОФОРІЄНТАЦІЯ</small><strong>Знайди напрям, який відгукується</strong></div><b>→</b></a><a href={pageUrl("/progress",grade)}><span>↗</span><div><small>ТВОЇ ДОСЯГНЕННЯ</small><strong>Подивись, скільки вже пройдено</strong></div><b>→</b></a></section>
  </>;
}

function Fact({icon,tag,title,text}) { return <article className="fact-card"><p className="fact-tag"><span>{icon}</span>{tag}</p><h3>{title}</h3><p>{text}</p></article>; }

function NmtBanner({grade,subjects}) {
  const required=[["ukr-mova","Українська мова"],["algebra","Математика"],["history-ukraine","Історія України"]];
  return <section className="nmt-banner"><p className="eyebrow">ПІДГОТОВКА ДО НМТ</p><h2>Три основи — впевненіший старт</h2><p>Обов’язкові предмети з поясненнями та тренувальним іспитом.</p><div className="nmt-links">{required.map(([slug,name])=>subjects.some(s=>s.slug===slug)&&<a key={slug} href={pageUrl("/subject/"+slug,grade)}><strong>{name}</strong><span>Теми й приклади →</span></a>)}<a href={pageUrl("/nmt/simulation",grade)}><strong>Предмет на вибір</strong><span>Тренувальний НМТ · 120 хв →</span></a></div></section>;
}

function useSubject(grade,slug) {
  const [subject,setSubject]=useState(null); const [error,setError]=useState(false);
  useEffect(()=>{let alive=true;setSubject(null);setError(false);fetch("/data/subjects/"+grade+"/"+encodeURIComponent(slug)+".json").then(r=>{if(!r.ok)throw new Error("subject");return r.json();}).then(data=>{if(alive)setSubject(data);}).catch(()=>{if(alive)setError(true);});return()=>{alive=false;};},[grade,slug]);
  return {subject,error};
}

function Crumb({grade,label,slug}) { return <nav className="crumb" aria-label="Навігаційний шлях"><a href={pageUrl("/",grade)}>Предмети</a><span> / </span>{slug?<><a href={pageUrl("/subject/"+slug,grade)}>{label}</a></>:<span>{label}</span>}</nav>; }

export function SubjectPage({grade,slug,progressTick}) {
  const {subject,error}=useSubject(grade,slug); const [shown,setShown]=useState(50); const progress=readProgress();
  if(error)return <LoadingState/>; if(!subject)return <LoadingState/>;
  const lessons=subject.lessons||[]; let next=1;while(next<=lessons.length&&progress[topicKey(grade,slug,next)]&&progress[topicKey(grade,slug,next)].passed)next++;
  const complete=next-1;
  return <section className="page-wrap"><Crumb grade={grade} label={subject.name}/><header className="subject-hero"><span className="subject-hero-icon">{subject.icon}</span><div><p className="eyebrow">{subject.area}</p><h1>{subject.name}</h1><p>{subject.description}</p>{subject.nmt_role&&<span className="nmt-tag">НМТ · {subject.nmt_role}</span>}</div></header>{subject.nmt_role&&<p className="callout">Теми допомагають повторити знання. Це тренування; звіряй формат свого року з матеріалами УЦОЯО.</p>}<div className="section-heading topic-heading"><div><p className="eyebrow">ТВОЯ НАВЧАЛЬНА МАНДРІВКА · {grade} КЛАС</p><h2>Теми й уроки</h2></div><p><strong>{complete}</strong> / {lessons.length.toLocaleString("uk")} тем пройдено</p></div><div className="route-progress"><span style={{width:(lessons.length?complete/lessons.length*100:0)+"%"}}/></div><p className="route-hint">Теми відкриваються по черзі. Пройди контрольну, щоб відкрити наступну.</p><div className="lesson-route">{lessons.slice(0,shown).map((lesson,index)=>{const id=index+1;const state=progress[topicKey(grade,slug,id)];const done=Boolean(state&&state.passed);const open=id<=next;return <a className={"topic-row "+(done?"is-done ":"")+(open?"is-open":"is-locked")} key={id} href={open?pageUrl("/lesson/"+slug+"/"+id,grade):undefined} aria-disabled={!open}><span className="topic-number">{String(id).padStart(2,"0")}</span><span className="topic-row-copy"><strong>{lesson.title}</strong><small>{done?"Пройдено · "+state.score+"/"+state.total:open?"Пояснення · приклад · вправа · тест":"Спершу пройди попередню тему"}</small></span><span className="topic-state">{done?"✓":open?"→":"🔒"}</span></a>;})}</div>{shown<lessons.length&&<button className="button button-outline load-more" onClick={()=>setShown((n)=>Math.min(n+50,lessons.length))}>Показати ще теми</button>}<p className="page-footnote">Прогрес зберігається у сховищі цього браузера на цьому пристрої.</p></section>;
}

export function LessonPage({grade,slug,lessonId}) {
  const {subject,error}=useSubject(grade,slug); const progress=readProgress();
  if(error)return <LoadingState/>;if(!subject)return <LoadingState/>;
  const lesson=subject.lessons&&subject.lessons[lessonId-1]; if(!lesson)return <section className="loading-card"><h1>Тему не знайдено</h1><a className="button" href={pageUrl("/subject/"+slug,grade)}>До всіх тем</a></section>;
  const previous=progress[topicKey(grade,slug,lessonId-1)];
  if(lessonId>1&&!(previous&&previous.passed))return <section className="locked-card"><p className="eyebrow">НАВЧАЛЬНИЙ МАРШРУТ</p><h1>Спершу пройди попередню тему</h1><p>Після контрольної наступна тема відкриється автоматично.</p><a className="button" href={pageUrl("/subject/"+slug,grade)}>Повернутися до маршруту</a></section>;
  return <section className="page-wrap lesson-page"><Crumb grade={grade} label={subject.name} slug={slug}/><header className="lesson-heading"><p className="eyebrow">{subject.icon} {subject.name} · ТЕМА {String(lessonId).padStart(2,"0")}</p><h1>{lesson.title}</h1><p>{subject.description}</p></header><LearningVisual subject={subject}/><div className="lesson-columns"><article className="lesson-theory"><section className="lesson-block"><p className="eyebrow">ПОЯСНЕННЯ</p><h2>Розберімося</h2><p>{lesson.explain}</p></section>{lesson.curiosity&&<aside className="curiosity-card"><span>✦</span><div><small>ЦІКАВИЙ ФАКТ</small><p>{lesson.curiosity}</p></div></aside>}{lesson.study_guide&&lesson.study_guide.length>0&&<section className="lesson-block"><p className="eyebrow">ЗАПАМ’ЯТАЙ</p><h2>Короткий конспект</h2><ul className="study-guide">{lesson.study_guide.map((item,index)=><li key={index}>{displayText(item)}</li>)}</ul></section>}<section className="example-card"><p className="eyebrow">ПРИКЛАД</p><h2>Подивись, як це працює</h2><p>{lesson.example}</p></section><section className="practice-card"><p className="eyebrow">СПРОБУЙ САМ / САМА</p><h2>Твоя вправа</h2><p>{lesson.task}</p></section><LessonNotes grade={grade} slug={slug} lessonId={lessonId}/></article><QuizCard grade={grade} slug={slug} lessonId={lessonId} questions={lesson.control_work||[]}/></div><div className="lesson-bottom-nav"><a className="button button-outline" href={pageUrl("/subject/"+slug,grade)}>← Усі теми</a>{lessonId<subject.lessons.length&&<a className="button button-primary" href={pageUrl("/lesson/"+slug+"/"+(lessonId+1),grade)}>Наступна тема →</a>}</div></section>;
}

function displayText(value){if(value==null)return "";if(typeof value==="string"||typeof value==="number")return String(value);if(Array.isArray(value))return value.map(displayText).join(" · ");if(typeof value==="object")return Object.values(value).map(displayText).join(" · ");return "";}

function LearningVisual({subject}) {
  const key=(subject.name+" "+subject.area).toLocaleLowerCase("uk");
  if(key.includes("алгеб")||key.includes("математ")||key.includes("функц"))return <div className="visual-card graph-visual"><div><p className="eyebrow">ВІЗУАЛЬНА ПІДКАЗКА</p><h2>Побач закономірність</h2><p>Графік показує, як змінюється одна величина, коли змінюється інша.</p></div><svg viewBox="0 0 420 210" role="img" aria-label="Координатна площина з графіком функції"><path className="grid-line" d="M36 20v165M91 20v165M146 20v165M201 20v165M256 20v165M311 20v165M366 20v165M26 40h370M26 75h370M26 110h370M26 145h370M26 180h370"/><path className="axis-line" d="M26 110h370M201 185V20"/><path className="graph-line" d="M42 171C90 156 122 140 160 122S221 91 254 71 318 40 380 27"/><circle className="graph-dot" cx="256" cy="71" r="6"/></svg></div>;
  if(key.includes("геометр"))return <div className="visual-card geometry-visual"><div><p className="eyebrow">ВІЗУАЛЬНА ПІДКАЗКА</p><h2>Форма розповідає</h2><p>Познач відомі сторони, кути або вершини — так правило легше застосувати.</p></div><svg viewBox="0 0 420 210" role="img" aria-label="Трикутник зі сторонами та висотою"><path className="geo-shape" d="M82 170L200 30l140 140z"/><path className="geo-height" d="M200 30v140"/><text x="128" y="115">a</text><text x="270" y="115">b</text><text x="206" y="185">c</text></svg></div>;
  if(key.includes("фізик")||key.includes("хім"))return <div className="visual-card science-visual"><div><p className="eyebrow">ВІЗУАЛЬНА ПІДКАЗКА</p><h2>Модель допомагає думати</h2><p>Спостерігай за умовами й шукай зв’язок між причиною та результатом.</p></div><div className="molecule" role="img" aria-label="Модель взаємодії частинок"><span className="mol-node mol-a">●</span><span className="mol-node mol-b">●</span><span className="mol-node mol-c">●</span><i className="mol-link mol-l1"/><i className="mol-link mol-l2"/><i className="mol-link mol-l3"/></div></div>;
  return <div className="visual-card idea-visual"><div><p className="eyebrow">ВІЗУАЛЬНА ПІДКАЗКА</p><h2>Знайди головне</h2><p>Виділи поняття, приклад і висновок — вони допоможуть пояснити тему своїми словами.</p></div><div className="idea-stack" aria-hidden="true"><span>ПОНЯТТЯ</span><i>↓</i><span>ПРИКЛАД</span><i>↓</i><span>ВИСНОВОК</span></div></div>;
}

function LoadingState(){return <section className="loading-card" role="status"><span className="loading-star">✦</span><h1>Відкриваємо навчальний матеріал</h1><p>Це може зайняти мить.</p></section>;}

export function ProgressPage({grade,catalog}) {
  const progress=readProgress();
  const subjects=catalog[String(grade)]||[];
  const total=subjects.reduce((n,s)=>n+s.lesson_count,0);
  const done=Object.entries(progress).filter(([key,value])=>key.startsWith(grade+":")&&value&&value.passed).length;
  const notes=Object.entries(readNotes()).map(([key,value])=>{const [savedGrade,slug,id]=key.split(":");return {key,value,grade:Number(savedGrade),slug,id:Number(id),subject:subjects.find(item=>item.slug===slug)};}).filter(item=>item.grade===grade&&typeof item.value==="string"&&item.value.trim());
  const mistakes=readMistakes().filter(item=>Number(item.grade)===grade);
  return <section className="page-wrap progress-page"><Crumb grade={grade} label="Мій поступ"/><header className="progress-hero"><p className="eyebrow">ТВОЯ НАВЧАЛЬНА МАНДРІВКА</p><h1>Мій поступ</h1><p>Ось теми, які ти вже пройшов або пройшла у цьому браузері.</p><div className="progress-total"><strong>{done}</strong><span>із {total.toLocaleString("uk")} тем</span></div><div className="route-progress"><span style={{width:(total?done/total*100:0)+"%"}}/></div></header><div className="progress-subjects">{subjects.map(subject=>{const count=Object.entries(progress).filter(([key,value])=>key.startsWith(grade+":"+subject.slug+":")&&value&&value.passed).length;return <article key={subject.slug}><span>{subject.icon}</span><div><h2>{subject.name}</h2><div className="route-progress"><span style={{width:(subject.lesson_count?count/subject.lesson_count*100:0)+"%"}}/></div><small>{count} із {subject.lesson_count.toLocaleString("uk")} тем</small></div><a href={pageUrl("/subject/"+subject.slug,grade)}>Відкрити</a></article>;})}</div><section className="personal-notes-panel"><div className="section-heading"><div><p className="eyebrow">ЗАПИСИ З УРОКІВ</p><h2>Мої нотатки</h2></div><span>{notes.length}</span></div>{notes.length?<div className="personal-note-list">{notes.map(item=><article key={item.key}><a href={pageUrl("/lesson/"+item.slug+"/"+item.id,grade)}>{item.subject?.name||item.slug} · тема {item.id}</a><p>{item.value}</p></article>)}</div>:<p className="empty-note">Нотаток цього класу поки немає. Залиш короткий запис на сторінці будь-якої теми.</p>}</section><MistakeReview grade={grade} items={mistakes}/><p className="page-footnote">Прогрес і нотатки зберігаються лише у цьому браузері й не прив’язані до електронної пошти.</p></section>;
}

function MistakeReview({grade,items}) {
  const [remaining,setRemaining]=useState(items);
  const [selected,setSelected]=useState({});
  const [feedback,setFeedback]=useState({});
  function check(item,event){
    event.preventDefault();
    if(Number(selected[item.id])!==item.correctIndex){setFeedback(current=>({...current,[item.id]:"Поки не збіглося. Перечитай пояснення й спробуй ще раз."}));return;}
    const next=readMistakes().filter(entry=>entry.id!==item.id);
    try{localStorage.setItem(MISTAKES_KEY,JSON.stringify(next));}catch{}
    setRemaining(current=>current.filter(entry=>entry.id!==item.id));
    setFeedback(current=>({...current,[item.id]:"Правильно! Прибрали запитання з повторення."}));
  }
  return <section className="mistake-review-panel"><div className="section-heading"><div><p className="eyebrow">ПОВЕРНИСЯ ДО СКЛАДНОГО</p><h2>Добірка повторення</h2></div><span>{remaining.length}</span></div>{remaining.length?<div className="mistake-review-list">{remaining.map(item=><article key={item.id}><p className="mistake-subject">Питання з теми</p><h3>{item.question}</h3><form onSubmit={event=>check(item,event)}><fieldset><legend>Обери відповідь</legend>{item.options.map((option,optionIndex)=><label key={optionIndex}><input type="radio" name={item.id} value={optionIndex} checked={Number(selected[item.id])===optionIndex} onChange={()=>setSelected(current=>({...current,[item.id]:optionIndex}))}/><span>{option}</span></label>)}</fieldset><button className="button button-small" type="submit" disabled={selected[item.id]===undefined}>Перевірити</button><a className="review-topic-link" href={pageUrl("/lesson/"+item.subjectSlug+"/"+item.lessonId,grade)}>Відкрити пояснення теми</a></form>{feedback[item.id]&&<p className="review-feedback" role="status">{feedback[item.id]}</p>}</article>)}</div>:<p className="empty-note">Поки немає помилок для повторення. Якщо у тесті щось буде складно, запитання з’явиться тут.</p>}</section>;
}

export function DiscoveryPage({grade,catalog,kind}) {
  const map={missions:["Навчальні місії","Застосуй знання, щоб розв’язувати задачі з життя."],laboratories:["Віртуальні лабораторії","Спостерігай, змінюй умови й пов’язуй результат із темою."],"daily-practice":["Завдання дня","Коротка практика допоможе пригадати матеріал і зробити ще один крок."]};
  const title=(map[kind]||map.missions)[0];const description=(map[kind]||map.missions)[1];const subjects=catalog[String(grade)]||[];
  return <section className="page-wrap discovery-page"><Crumb grade={grade} label={title}/><header className="discovery-hero"><p className="eyebrow">ВЧИСЯ ЧЕРЕЗ ДОСЛІДЖЕННЯ</p><h1>{title}</h1><p>{description}</p></header><div className="discovery-grid">{subjects.slice(0,18).map((subject,index)=><a key={subject.slug} href={pageUrl("/subject/"+subject.slug,grade)}><span>{["🧭","🧪","📈","✨"][index%4]}</span><small>{subject.area}</small><strong>{subject.name}</strong><p>{subject.description}</p><b>Відкрити теми →</b></a>)}</div></section>;
}

export { CareersPage, NmtPage };
