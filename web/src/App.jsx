import React, { useEffect, useMemo, useState } from "react";
import { CareersPage, DiscoveryPage, HomePage, LessonPage, NmtPage, ProgressPage, SubjectPage } from "./pages.jsx";
import { gradeFromUrl, pageUrl } from "./state.js";

function App() {
  const grade = gradeFromUrl();
  const [catalog, setCatalog] = useState(null);
  const [catalogError, setCatalogError] = useState(false);
  const [progressTick, setProgressTick] = useState(0);
  const pathname = location.pathname.replace(/\/+$/, "") || "/";
  const route = useMemo(() => {
    const subject = pathname.match(/^\/subject\/([a-z0-9-]+)$/);
    const lesson = pathname.match(/^\/lesson\/([a-z0-9-]+)\/(\d+)$/);
    return { subject: subject && subject[1], lesson: lesson && lesson[1], lessonId: lesson && Number(lesson[2]) };
  }, [pathname]);

  useEffect(() => {
    fetch("/data/catalog.json").then((r) => { if (!r.ok) throw new Error("catalog"); return r.json(); })
      .then(setCatalog).catch(() => setCatalogError(true));
  }, []);
  useEffect(() => {
    const refresh = () => setProgressTick((value) => value + 1);
    window.addEventListener("storage", refresh);
    window.addEventListener("rozumnyk-progress", refresh);
    return () => {
      window.removeEventListener("storage", refresh);
      window.removeEventListener("rozumnyk-progress", refresh);
    };
  }, []);

  let page;
  if (!catalog) {
    page = <section className="loading-card" role="status"><span className="loading-star">✦</span><h1>{catalogError ? "Не вдалося відкрити матеріали" : "Готуємо сторінку"}</h1><p>{catalogError ? "Онови сторінку трохи пізніше." : "Навчальні матеріали завантажуються."}</p>{catalogError && <button className="button button-primary" onClick={() => location.reload()}>Спробувати ще раз</button>}</section>;
  } else if (route.lesson) {
    page = <LessonPage grade={grade} slug={route.lesson} lessonId={route.lessonId} />;
  } else if (route.subject) {
    page = <SubjectPage grade={grade} slug={route.subject} progressTick={progressTick} />;
  } else if (pathname === "/career-guide") {
    page = <CareersPage grade={grade} />;
  } else if (pathname === "/nmt/simulation") {
    page = <NmtPage grade={grade} catalog={catalog} />;
  } else if (pathname === "/progress") {
    page = <ProgressPage grade={grade} catalog={catalog} progressTick={progressTick} />;
  } else if (pathname === "/missions" || pathname === "/laboratories" || pathname === "/daily-practice") {
    page = <DiscoveryPage grade={grade} catalog={catalog} kind={pathname.slice(1)} />;
  } else {
    page = <HomePage grade={grade} catalog={catalog} progressTick={progressTick} />;
  }

  return <div className="app-shell"><div className="space-grain" aria-hidden="true" /><Header grade={grade} catalog={catalog} /><main>{page}</main><Footer grade={grade} /></div>;
}

function Header({ grade, catalog }) {
  return <header className="topbar">
    <a className="brand" href={pageUrl("/", grade)} aria-label="Розумник — на головну"><span className="brand-mark">R</span><span>РОЗУМНИК<small>ЗРОЗУМІЛЕ НАВЧАННЯ</small></span></a>
    <nav className="header-links" aria-label="Головна навігація"><a href={pageUrl("/", grade) + "#subjects"}>Предмети</a><a href={pageUrl("/career-guide", grade)}>Професії</a>{grade === 11 && <a href={pageUrl("/nmt/simulation", grade)}>НМТ</a>}</nav>
    <label className="grade-picker"><span className="sr-only">Обрати клас</span><select value={grade} onChange={(event) => { location.href = pageUrl("/", Number(event.target.value)); }}>{Object.keys(catalog || {}).map((value) => <option key={value} value={value}>{value} клас</option>)}</select></label>
  </header>;
}

function Footer({ grade }) {
  return <footer className="site-footer"><span>РОЗУМНИК · Навчайся у своєму темпі</span><nav aria-label="Додаткові сторінки"><a href={pageUrl("/progress", grade)}>Мій поступ</a><a href={pageUrl("/career-guide", grade)}>Професії</a><a href={pageUrl("/", grade) + "#subjects"}>Предмети</a></nav></footer>;
}

export default App;
