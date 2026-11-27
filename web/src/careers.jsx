import React, { useEffect, useState } from "react";
import { pageUrl } from "./state.js";

export function CareersPage({grade}) {
  const [data,setData]=useState(null);
  const [selected,setSelected]=useState(null);
  const [step,setStep]=useState(0);
  const [scores,setScores]=useState({});
  const [complete,setComplete]=useState(false);
  useEffect(()=>{fetch("/data/careers.json").then(r=>r.json()).then(setData).catch(()=>setData({categories:{},directions:[],questions:[]}));},[]);
  if(!data)return <section className="loading-card"><h1>Відкриваємо професії</h1><p>Підбираємо цікаві напрями.</p></section>;
  const categories=data.categories||{};const directions=data.directions||[];const questions=data.questions||[];
  function choose(category){const next=Object.assign({},scores);next[category]=(next[category]||0)+1;setScores(next);if(step+1>=questions.length)setComplete(true);else setStep(step+1);}
  const results=Object.entries(scores).sort((a,b)=>b[1]-a[1]).slice(0,3);
  function restart(){setStep(0);setScores({});setComplete(false);}
  return <section className="page-wrap careers-page"><nav className="crumb"><a href={pageUrl("/",grade)}>Предмети</a><span> / </span><span>Профорієнтація</span></nav>
    <header className="career-hero"><p className="eyebrow">ЗНАЙОМСЯ З МОЖЛИВОСТЯМИ</p><h1>Професії — це різні способи змінювати світ</h1><p>Подивись, чим займаються фахівці, та спробуй короткі завдання. Тут немає єдиного правильного вибору.</p><a className="button button-primary" href="#career-test">Пройти тест інтересів ↓</a><div className="career-hero-orb" aria-hidden="true">✦</div></header>
    <div className="section-heading"><div><p className="eyebrow">ОБЕРИ НАПРЯМ</p><h2>Що тобі цікаво досліджувати?</h2></div><p>{directions.length} напрямів · професії у 3D-картках</p></div>
    <div className="career-grid">{directions.map((direction,index)=><article className="career-card" key={direction.slug}><button className="career-art" style={{"--scene-index":index}} onClick={()=>setSelected(direction)} aria-label={"Відкрити напрям "+direction.name}><span className="career-3d-orb">{direction.icon||"✦"}</span><span className="career-art-label">3D · НАПРЯМ</span></button><p className="eyebrow">{(categories[direction.parent]||{}).name||"НАПРЯМ"}</p><h3>{direction.name}</h3><p>{direction.summary}</p><button className="text-button" onClick={()=>setSelected(direction)}>Дізнатися більше →</button></article>)}</div>
    <section id="career-test" className="career-test-panel"><div className="section-heading"><div><p className="eyebrow">ТЕСТ ІНТЕРЕСІВ · {questions.length} КРОКІВ</p><h2>Що тобі подобається робити?</h2></div><p>Це підказка для роздумів, а не оцінка здібностей.</p></div>
      {!complete&&questions.length>0?<div className="career-question"><div className="quiz-count">Запитання {step+1} з {questions.length}</div><div className="quiz-progress"><span style={{width:((step+1)/questions.length*100)+"%"}}/></div><h3>{questions[step].prompt}</h3><div className="career-options">{(questions[step].choices||[]).map(([key,text])=><button key={key} onClick={()=>choose(key)}>{text}<span>→</span></button>)}</div></div>
      :complete?<div className="career-results"><h3>Ось напрями, які можуть тобі відгукнутися</h3><p>Це лише відображення твоїх виборів. Спробуй гурток або невеликий проєкт, щоб дослідити сферу.</p><div className="career-result-grid">{results.map(([key,count])=><article key={key}><small>{count} твоїх виборів</small><h4>{(categories[key]||{}).name||key}</h4><p><strong>Приклади професій:</strong> {(categories[key]||{}).professions}</p><p><strong>Можуть знадобитися:</strong> {(categories[key]||{}).skills}</p><p><strong>Наступний крок:</strong> {(categories[key]||{}).after9}</p></article>)}</div><button className="button button-outline" onClick={restart}>Пройти тест знову ↺</button></div>:<p>Тест готується.</p>}
    </section>
    <aside className="career-note"><span>ℹ️</span><p>Тест досліджує інтереси й не визначає майбутнє. Навчальні шляхи та правила вступу змінюються — перевіряй їх у закладі освіти й на офіційних сайтах.</p></aside>
    {selected&&<div className="modal-backdrop" role="presentation" onClick={()=>setSelected(null)}><section className="career-modal" role="dialog" aria-modal="true" aria-labelledby="career-title" onClick={event=>event.stopPropagation()}><button className="modal-close" onClick={()=>setSelected(null)} aria-label="Закрити">×</button><p className="eyebrow">{selected.icon||"✦"} · 3D ПРЕЗЕНТАЦІЯ</p><div className="career-modal-stage"><span className="career-3d-orb">{selected.icon||"✦"}</span></div><h2 id="career-title">{selected.name}</h2><p className="career-summary">{selected.summary}</p><div className="profession-cards">{(selected.professions||[]).map(profession=><article key={profession.title}><span className="profession-icon">{profession.icon}</span><h3>{profession.title}</h3><p><strong>Що робить:</strong> {profession.day}</p><p><strong>Кому допомагає:</strong> {profession.impact}</p><p><strong>Цікавий факт:</strong> {profession.fact}</p><p><strong>Спробуй:</strong> {profession.try}</p></article>)}</div><div className="career-pathways"><div><small>ПІСЛЯ 9 КЛАСУ</small><p>{(categories[selected.parent]||{}).after9}</p></div><div><small>ПІСЛЯ 12 КЛАСУ</small><p>{(categories[selected.parent]||{}).after12}</p></div></div></section></div>}
  </section>;
}
