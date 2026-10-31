from flask import Flask, abort, jsonify, render_template_string, request, url_for
from markupsafe import Markup
from curriculum import GRADES

app = Flask(__name__)

CAREER_CATEGORIES = {
    "stem": {
        "name": "Технології й точні науки",
        "professions": "розробник програмного забезпечення, інженер, аналітик даних, фахівець із кібербезпеки, робототехнік",
        "skills": "логічне мислення, математика, уважність до деталей, робота з цифровими інструментами й готовність постійно вчитися",
        "after9": "Придивись до STEM-профілю в академічному ліцеї або до професійного чи фахового коледжу з ІТ, електроніки, автоматизації чи технічного дизайну.",
        "after12": "Можна дослідити бакалаврські програми з комп’ютерних наук, інженерії, математики, фізики або кібербезпеки; для частини напрямів корисні власні проєкти й портфоліо.",
    },
    "health": {
        "name": "Здоров’я й природничі науки",
        "professions": "біолог, еколог, лабораторний фахівець, фармацевт, лікар, ветеринарний лікар",
        "skills": "цікавість до природи й організму людини, спостережливість, відповідальність, точність і дбайливе ставлення до людей",
        "after9": "Поглянь на природничий профіль ліцею або на програми професійного й фахового коледжу з лабораторної справи, екології чи догляду за здоров’ям; перевір конкретні умови вступу.",
        "after12": "Можна порівняти програми з біології, екології, фармації, ветеринарії та медицини. Для медичних професій потрібна відповідна тривала освіта й виконання вимог до вступу.",
    },
    "creative": {
        "name": "Творчість, дизайн і комунікації",
        "professions": "графічний або UX/UI-дизайнер, архітектор, ілюстратор, фотограф, редактор, фахівець із медіа",
        "skills": "уяву, візуальне мислення, уміння помічати деталі, пояснювати ідеї та спокійно вдосконалювати роботу після відгуків",
        "after9": "Розглянь мистецький або мовно-літературний профіль ліцею, художній чи фаховий коледж. Для творчих програм заздалегідь перевір, чи потрібен творчий конкурс або портфоліо.",
        "after12": "Можна обрати дизайн, архітектуру, медіа, журналістику, видавничу справу чи мистецтво у фаховому коледжі або закладі вищої освіти; поступово збирай портфоліо.",
    },
    "people": {
        "name": "Люди, освіта й суспільство",
        "professions": "учитель, психолог, соціальний працівник, юрист, перекладач, фахівець із комунікацій",
        "skills": "уважне слухання, грамотне мовлення, емпатію, аргументацію, повагу до правил і різних поглядів",
        "after9": "Можна обрати соціально-гуманітарний чи мовний профіль ліцею або дізнатися про програми фахового коледжу з освіти, соціальної роботи, мов і комунікацій.",
        "after12": "Порівняй програми з педагогіки, психології, права, соціальної роботи, мов або комунікацій. Для професій психолога, учителя чи юриста перевір вимоги до освіти й кваліфікації.",
    },
    "business": {
        "name": "Бізнес, економіка й організація",
        "professions": "підприємець, економіст, бухгалтер, маркетолог, логіст, проєктний менеджер",
        "skills": "планування, базову математику, відповідальність, комунікацію, уміння працювати з інформацією та командою",
        "after9": "Придивись до соціально-гуманітарного профілю, а також до програм професійного чи фахового коледжу з обліку, підприємництва, торгівлі або логістики.",
        "after12": "Можна порівняти програми з економіки, фінансів, менеджменту, маркетингу, підприємництва й логістики у фахових коледжах або університетах.",
    },
    "practical": {
        "name": "Технічні професії й майстерність",
        "professions": "електрик, механік, кухар, зварювальник, будівельник, майстер з обслуговування техніки",
        "skills": "практичну кмітливість, точність, безпечну роботу з інструментами, терпіння й уміння читати схеми або інструкції",
        "after9": "Професійний коледж або заклад професійної освіти дає змогу поєднати загальну освіту з опануванням професії. Також можна продовжити навчання в ліцеї, якщо хочеться ще дослідити інтереси.",
        "after12": "Можна здобути професійну кваліфікацію, вступити до фахового коледжу або обрати інженерну програму. Дивись на практику, обладнання майстерень і партнерства закладу з роботодавцями.",
    },
}

CAREER_QUESTION_PROMPTS = [
    "Яке завдання тобі найцікавіше взятися виконувати?",
    "Яку роль ти найчастіше обираєш у командному проєкті?",
    "Які задачі дають тобі відчуття «хочу розібратися»?",
    "Який результат роботи приносив би найбільше задоволення?",
    "Що ти охочіше робитимеш у вільний час?",
    "Який шкільний проєкт ти обрав/обрала б за власним бажанням?",
    "Який тип проблем тобі цікаво розв’язувати?",
    "Яке вміння хотілося б розвинути найбільше?",
    "У якому середовищі тобі комфортніше працювати?",
    "Що для тебе найважливіше у майбутній справі?",
    "Який результат роботи ти хотів/хотіла б побачити наприкінці дня?",
    "Який короткий пробний проєкт ти обрав/обрала б цього місяця?",
]

CAREER_OPTION_BANK = {
    "stem": [
        "Розкласти складну задачу на частини й знайти закономірність.", "Продумати, як працює застосунок, пристрій або система.", "Дослідити дані й перевірити, яке пояснення підтверджується фактами.", "Скласти алгоритм і перевірити його на різних прикладах.", "Зібрати прототип і вдосконалити його після випробування.", "Знайти технічну помилку та зрозуміти її причину.", "Побачити, як математична модель пояснює реальне явище.", "Дізнатися, як захищають інформацію та цифрові системи.", "Порівняти кілька рішень за точністю й ефективністю.", "Створити цифровий інструмент, який полегшує чиюсь роботу.", "Працювати з конструктором, кодом або електронікою.", "Дослідити, як поєднати технології та користь для людей.",
    ],
    "health": [
        "З’ясувати, чому відбувається природне явище.", "Дослідити живі організми, їхню будову й середовище.", "Зрозуміти, як турбота про здоров’я впливає на життя людини.", "Провести безпечне спостереження й точно записати результат.", "Дізнатися, як працює організм або екосистема.", "Порівняти наукові пояснення й відрізнити факти від міфів.", "Подумати, як зменшити шкоду довкіллю.", "Упорядкувати результати дослідження та зробити висновок.", "Зрозуміти, як ліки чи матеріали проходять дослідження.", "Знайти спосіб зробити громаду здоровішою та безпечнішою.", "Дослідити зв’язки між живими організмами.", "Поставити запитання й шукати на нього доказову відповідь.",
    ],
    "creative": [
        "Придумати образ, історію або візуальну ідею.", "Створити афішу, відео, комікс чи сторінку.", "Пояснити складну думку зрозумілим і красивим способом.", "Добирати кольори, форму, музику або слова для настрою.", "Вигадати назву й стиль для нового проєкту.", "Редагувати текст, щоб він звучав виразно й точно.", "Знімати фото або відео й розповідати ними історію.", "Перетворювати начерк на готовий творчий продукт.", "Досліджувати мистецькі стилі та надихатися ними.", "Створити зручний і привабливий дизайн речі чи простору.", "Показати ідею аудиторії через презентацію або виставку.", "Поєднати творчість із технологіями та новими медіа.",
    ],
    "people": [
        "Допомогти команді домовитися й почути різні думки.", "Пояснити комусь тему або підтримати під час навчання.", "Розібрати життєву ситуацію та знайти справедливе рішення.", "Поставити запитання й уважно вислухати людину.", "Захищати права й гідність людей за правилами.", "Перекладати або знаходити спільну мову між культурами.", "Організувати добру справу для школи чи громади.", "Пояснити, як історія впливає на сучасне суспільство.", "Допомогти розв’язати конфлікт спокійно й чесно.", "Ділитися знаннями й бачити, як інші зростають.", "Писати тексти, що інформують і допомагають зрозуміти подію.", "Дізнатися, як зробити послуги й правила доступнішими для всіх.",
    ],
    "business": [
        "Скласти план і довести командну справу до результату.", "Порівняти варіанти й вирішити, який дає найбільшу користь.", "Продумати корисну послугу або товар для людей.", "Спланувати бюджет і стежити, на що витрачаються кошти.", "Організувати подію, розподілити ролі й час.", "З’ясувати, що потрібно клієнтам або громаді.", "Переконливо презентувати ідею та відповісти на запитання.", "Упорядкувати документи, дані або робочі процеси.", "Продумати, як доставити потрібну річ у потрібне місце.", "Знайти, як зробити невелику справу ефективнішою.", "Працювати з цифрами й пояснювати, що вони означають.", "Створити проєкт, який має і користь, і чіткий план.",
    ],
    "practical": [
        "Зібрати або полагодити річ і перевірити, чи вона працює.", "Працювати руками з інструментами й матеріалами.", "Приготувати страву, дотримуючись послідовності та якості.", "Змонтувати деталі за схемою й правилами безпеки.", "Побачити практичну проблему й одразу спробувати її вирішити.", "Вдосконалити механізм, меблі або побутовий предмет.", "Навчитися користуватися обладнанням і доглядати за ним.", "Створити корисну річ за кресленням або власним задумом.", "Працювати в майстерні, лабораторії, кухні чи на об’єкті.", "Опанувати професійну техніку через практичні вправи.", "Перевірити якість виробу й знайти, що треба виправити.", "Бачити конкретний результат своєї роботи наприкінці дня.",
    ],
}

CAREER_QUESTIONS = [
    {"prompt": prompt, "choices": [(key, CAREER_OPTION_BANK[key][index]) for key in CAREER_CATEGORIES]}
    for index, prompt in enumerate(CAREER_QUESTION_PROMPTS)
]

SHELL = r"""<!doctype html>
<html lang="uk">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f7f7f2">
  <meta name="description" content="Розумник — зрозумілі навчальні теми, приклади, вправи й контрольні для учнів 5–11 класів.">
  <meta property="og:type" content="website">
  <meta property="og:locale" content="uk_UA">
  <meta property="og:site_name" content="Розумник">
  <meta property="og:title" content="{{ title }} · Розумник">
  <meta property="og:description" content="Навчайся у своєму темпі: уроки, приклади й перевірка знань для 5–11 класів.">
  <meta name="twitter:card" content="summary">
  <link rel="icon" type="image/svg+xml" href="{{ url_for('static', filename='favicon.svg') }}">
  <title>{{ title }} · Розумник</title>
  <style>
    :root{--ink:#1d2939;--muted:#6b7785;--paper:#f7f7f2;--white:#fff;--green:#4d7465;--green-dark:#34594c;--lime:#c7e5b1;--peach:#ffd2b7;--yellow:#f5d879;--line:#e9e9e0;--shadow:0 18px 50px #2433280c}
    *{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,"Segoe UI",Arial,sans-serif;line-height:1.6}
    a{color:inherit}.topbar{height:76px;max-width:1180px;margin:auto;padding:0 25px;display:flex;align-items:center;justify-content:space-between}.brand{display:flex;align-items:center;gap:11px;text-decoration:none;font-weight:850;font-size:20px;letter-spacing:-.7px}.brand-icon{height:39px;width:39px;border-radius:14px;background:var(--green);display:grid;place-items:center;color:#fff;font-size:21px;box-shadow:0 5px 14px #34594c33}.brand small{display:block;font-size:10px;letter-spacing:.02em;color:var(--muted);font-weight:550;margin-top:-2px}.grade{border:1px solid #e1e3d8;border-radius:30px;padding:8px 13px;background:#fff;font-size:12px;font-weight:750}.grade span{color:var(--green);margin-left:7px;font-size:10px;letter-spacing:.1em}
    .top-actions{display:flex;align-items:center;gap:12px}.progress-link{font-size:11px;text-decoration:none;color:var(--green);font-weight:800}.grade-switch{display:flex;gap:3px;padding:4px;border:1px solid #e1e3d8;border-radius:30px;background:#fff}.grade-switch a{min-width:54px;padding:6px 9px;border-radius:24px;text-align:center;text-decoration:none;color:var(--muted);font-size:11px;font-weight:750}.grade-switch a.active{background:var(--green);color:#fff}
    main{max-width:1130px;margin:auto;padding:10px 25px 75px}.hero{position:relative;isolation:isolate;min-height:350px;padding:48px 55px;border-radius:27px;overflow:hidden;background:#e4eee5;display:grid;grid-template-columns:1.15fr .85fr;align-items:center;box-shadow:var(--shadow);animation:appear .7s ease both}.hero:before,.hero:after{content:"";position:absolute;z-index:-1;border-radius:50%;filter:blur(1px);animation:drift 8s ease-in-out infinite alternate}.hero:before{width:280px;height:280px;background:#f1d88d;right:8%;top:-118px;opacity:.75}.hero:after{width:210px;height:210px;background:#b8d6c3;right:25%;bottom:-145px;animation-delay:-3s}.eyebrow{margin:0 0 12px;font-size:10px;letter-spacing:.18em;font-weight:850;color:var(--green)}h1,h2,h3,p{margin-top:0}.hero h1{font-size:clamp(38px,5.5vw,61px);line-height:1.04;letter-spacing:-.055em;margin-bottom:17px;max-width:570px}.hero h1 em{font-style:normal;color:var(--green)}.intro{font-size:15px;color:#586777;max-width:490px;margin-bottom:24px}.button{display:inline-flex;align-items:center;gap:17px;padding:12px 17px;border:0;border-radius:11px;background:var(--green);color:white;text-decoration:none;font-size:13px;font-weight:800;cursor:pointer;transition:transform .2s,background .2s,box-shadow .2s;box-shadow:0 6px 15px #34594c29}.button:hover{background:var(--green-dark);transform:translateY(-2px);box-shadow:0 9px 20px #34594c35}.hero-visual{height:235px;position:relative;display:grid;place-items:center}.orbit{position:absolute;width:220px;height:220px;border:1px dashed #7697858c;border-radius:50%;animation:spin 28s linear infinite}.planet{width:142px;height:142px;border-radius:48% 52% 55% 45%;background:linear-gradient(145deg,#668e74,#365a4f);box-shadow:inset -15px -12px 0 #274a3e33,0 22px 30px #34594c35;display:grid;place-items:center;color:#fff;font-size:55px;transform:rotate(-8deg);animation:bob 4s ease-in-out infinite}.float-chip{position:absolute;padding:10px 13px;background:#fff;border-radius:13px;box-shadow:0 10px 25px #25352b15;font-size:12px;font-weight:800;animation:bob 3.5s ease-in-out infinite}.chip-a{top:21px;right:7%;animation-delay:-1.4s}.chip-b{bottom:18px;left:2%;background:#fff2d2;animation-delay:-.6s}.chip-c{top:33px;left:5%;background:#fce4d7;animation-delay:-2.2s}.stats{display:flex;gap:27px;margin-top:23px;color:#617066;font-size:11px}.stats strong{display:block;color:var(--ink);font-size:16px}
    .section-head{display:flex;align-items:end;justify-content:space-between;margin:44px 2px 17px}.section-head h2{font-size:27px;letter-spacing:-.04em;margin:0}.section-head p{font-size:12px;color:var(--muted);margin:0 0 5px}.subject-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.subject-card{position:relative;overflow:hidden;text-decoration:none;background:var(--white);border:1px solid var(--line);border-radius:17px;padding:18px 19px 15px;min-height:187px;display:flex;flex-direction:column;box-shadow:0 4px 16px #25352b05;transition:transform .22s,box-shadow .22s,border-color .22s;animation:rise .55s both;animation-delay:calc(var(--i)*45ms)}.subject-card:hover{transform:translateY(-5px);box-shadow:0 15px 32px #25352b12;border-color:#c1d4c8}.subject-card:after{content:"";position:absolute;width:100px;height:100px;border-radius:50%;background:#eaf2e6;right:-40px;bottom:-52px;transition:transform .35s}.subject-card:hover:after{transform:scale(1.5)}.card-head{display:flex;align-items:center;justify-content:space-between;position:relative;z-index:1}.subject-icon{width:42px;height:42px;border-radius:14px;background:#edf3e8;display:grid;place-items:center;font-size:22px}.arrow{font-size:20px;color:#73917f;transition:transform .2s}.subject-card:hover .arrow{transform:translate(3px,-3px)}.subject-card h3{font-size:16px;letter-spacing:-.02em;margin:13px 0 5px;position:relative;z-index:1}.subject-card p{font-size:11.5px;line-height:1.5;color:var(--muted);margin:0 0 14px;position:relative;z-index:1}.card-meta{display:flex;align-items:center;justify-content:space-between;border-top:1px solid #f0f0eb;padding-top:10px;margin-top:auto;font-size:10px;color:var(--green);font-weight:800;position:relative;z-index:1}.mini-progress{color:#839087;font-weight:600}
    .reference-book{display:block;font-size:10px;line-height:1.4;color:#718176;position:relative;z-index:1;margin:-7px 0 10px}.subject-banner .reference-book{font-size:12px;margin:8px 0 0;color:#53675a}.note{margin-top:21px;padding:14px 17px;border-radius:13px;background:#fff4dc;color:#6c6046;font-size:11px;display:flex;gap:10px}.note p{margin:0}.crumb{font-size:11px;color:#849087;margin:17px 0 19px}.crumb a{color:var(--green);text-decoration:none}.subject-banner{border-radius:22px;background:#e5eee5;padding:30px 34px;display:flex;align-items:center;gap:20px;animation:appear .45s both}.subject-banner .subject-icon{width:58px;height:58px;font-size:29px;background:#fff}.subject-banner h1{font-size:34px;letter-spacing:-.05em;margin:0 0 4px}.subject-banner p:last-child{margin:0;color:#607166;font-size:13px}.lesson-list{background:#fff;border:1px solid var(--line);border-radius:17px;overflow:hidden}.lesson-row{display:flex;align-items:center;gap:15px;padding:14px 18px;text-decoration:none;border-bottom:1px solid #f0f0eb;transition:background .2s}.lesson-row:last-child{border-bottom:0}.lesson-row:hover{background:#f6f8f3}.lesson-no{flex:none;width:36px;height:36px;border-radius:12px;background:#edf3e8;color:var(--green);display:grid;place-items:center;font-size:11px;font-weight:850}.lesson-title{flex:1;font-weight:750;font-size:13px}.lesson-title small{display:block;font-weight:500;color:#879189;font-size:10px;margin-top:2px}.done{font-size:12px;color:var(--green);font-weight:800}
    .lesson-wrap{max-width:790px;margin:0 auto}.lesson-title-main{font-size:clamp(32px,5vw,45px);line-height:1.12;letter-spacing:-.05em;margin:8px 0 23px}.lesson-label{font-size:10px;color:var(--green);font-weight:850;letter-spacing:.16em}.lesson-panel{padding:21px 24px;background:#fff;border:1px solid var(--line);border-radius:16px;margin-bottom:12px;box-shadow:0 5px 18px #24332806;animation:rise .45s both}.lesson-panel:nth-of-type(2){animation-delay:.08s}.lesson-panel:nth-of-type(3){animation-delay:.15s}.lesson-panel h2{font-size:15px;margin:0 0 8px}.lesson-panel p{font-size:13px;color:#526170;margin:0}.lesson-panel.example{background:#eaf2e9;border-color:#dfeadd}.lesson-panel.task{background:#fff4dc;border-color:#f0e6c9}.lesson-panel.rule{background:#f0edff;border-color:#e4def8}.lesson-panel.warning{background:#fff0e8;border-color:#f4ddd0}.lesson-panel ul,.guide-list{padding-left:20px;margin:8px 0 0;color:#526170;font-size:12px}.lesson-panel li,.guide-list li{margin:5px 0}.course-guide{margin:14px 0;background:#f0edff;border:1px solid #e4def8;border-radius:14px;padding:14px 18px}.course-guide summary{font-weight:800;font-size:12px;cursor:pointer;color:#4c4970}.course-guide .guide-list{margin-bottom:0}.quiz{margin-top:19px;padding:25px;border-radius:18px;background:#263b35;color:white;box-shadow:0 15px 35px #233b3225}.quiz .eyebrow{color:#bdda9c}.quiz h2{font-size:18px;margin:2px 0 17px}.control-question{padding:14px 0;border-top:1px solid #ffffff24}.control-question h3{font-size:13px;line-height:1.5;margin:0 0 9px}.choice{display:flex;gap:10px;align-items:flex-start;background:#ffffff0d;border:1px solid #ffffff1b;padding:10px 12px;border-radius:10px;margin:7px 0;font-size:12px;line-height:1.45;cursor:pointer;transition:background .2s,border .2s}.choice:hover{background:#ffffff19;border-color:#bddaa077}.choice input{accent-color:#bdda9c;flex:none;margin-top:2px}.quiz .button{margin-top:12px;background:#c7e5b1;color:#20352d;box-shadow:none}.quiz-message{padding:11px 13px;border-radius:10px;margin-bottom:13px;font-weight:750;font-size:12px;animation:pop .35s}.quiz-message.good{background:#d8f0d7;color:#23563a}.quiz-message.try{background:#fff0df;color:#77533a}.progress-page h1{font-size:38px;letter-spacing:-.04em}.progress-class{margin:28px 0}.progress-class h2{font-size:21px}.progress-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.progress-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px}.progress-card h3{font-size:13px;margin:0 0 9px}.progress-card p{font-size:10px;color:var(--muted);margin:8px 0 0}.progress-track{height:7px;border-radius:9px;background:#edf0e9;overflow:hidden}.progress-track span{display:block;height:100%;width:0;background:linear-gradient(90deg,#82ad88,#4d7465);border-radius:inherit;transition:width .6s ease}.lesson-nav{display:flex;justify-content:space-between;margin:22px 0}.lesson-nav a{color:var(--green);font-weight:750;text-decoration:none;font-size:12px}.empty{padding:38px;background:white;border-radius:18px;text-align:center}
    footer{padding:23px;text-align:center;color:#89938d;font-size:10px;border-top:1px solid #e8e9e1}.reveal{opacity:0;transform:translateY(12px);transition:opacity .5s,transform .5s}.reveal.visible{opacity:1;transform:none}
    @keyframes appear{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}@keyframes rise{from{opacity:0;transform:translateY(13px)}to{opacity:1;transform:translateY(0)}}@keyframes bob{0%,100%{translate:0 0}50%{translate:0 -9px}}@keyframes drift{to{translate:-25px 18px;scale:1.08}}@keyframes spin{to{transform:rotate(360deg)}}@keyframes pop{from{opacity:0;transform:scale(.97)}to{opacity:1;transform:scale(1)}}
    @media(max-width:800px){.hero{grid-template-columns:1fr;padding:38px 32px}.hero-visual{height:180px}.subject-grid,.progress-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:540px){.topbar{height:67px;padding:0 12px}.top-actions{gap:6px}.progress-link{font-size:10px}.grade-switch a{min-width:37px;padding:6px 5px;font-size:10px}main{padding:8px 16px 55px}.hero{padding:30px 22px;min-height:0}.hero h1{font-size:42px}.hero-visual{height:155px}.planet{width:112px;height:112px;font-size:43px}.orbit{width:175px;height:175px}.chip-a{right:0}.chip-c{left:0}.stats{gap:16px}.section-head{margin-top:34px}.section-head h2{font-size:23px}.subject-grid,.progress-grid{grid-template-columns:1fr;gap:10px}.subject-card{min-height:158px;padding:15px 16px}.subject-banner{padding:22px 18px;gap:13px}.subject-banner h1{font-size:25px}.subject-banner .subject-icon{width:48px;height:48px;font-size:23px}.lesson-panel,.quiz{padding:19px}.lesson-row{padding:12px 11px;gap:10px}.lesson-title{font-size:12px}.lesson-nav{gap:12px}}
    .hero-visual{perspective:850px;transform-style:preserve-3d}.orbit{transform-style:preserve-3d}.orbit.orbit-tilt{transform:rotateX(68deg) rotateY(-16deg);animation:orbit3d 24s linear infinite}.planet{transform-style:preserve-3d;animation:bob 4s ease-in-out infinite,planet3d 16s ease-in-out infinite}.float-chip{transform:translateZ(22px)}.subject-card{transform-style:preserve-3d;perspective:700px}.subject-card:hover{transform:translateY(-7px) rotateX(2deg) rotateY(-2deg)}
    .nmt-banner{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:22px 0;padding:22px 25px;border-radius:18px;background:linear-gradient(120deg,#263b35,#395d50);color:white;box-shadow:0 14px 34px #233b3225;animation:appear .5s both}.nmt-banner h2{margin:0 0 7px;font-size:21px}.nmt-banner p{margin:0;color:#e1ede4;font-size:12px;line-height:1.6}.nmt-banner .eyebrow{color:#c7e5b1}.nmt-banner .button{flex:none;background:#c7e5b1;color:#20352d}.nmt-badge{display:inline-flex;margin:7px 0 0;padding:4px 8px;border-radius:20px;background:#edf3e8;color:#34594c;font-size:9px;font-weight:850;letter-spacing:.02em}.nmt-subject-note{margin:0 0 18px;padding:12px 16px;background:#eef3e9;border-left:4px solid #4d7465;border-radius:8px;color:#47594f;font-size:12px}.nmt-tip{border-color:#d8e8d3;background:linear-gradient(135deg,#f2f8ef,#fff)}.career-link{font-size:11px;text-decoration:none;color:var(--green);font-weight:800;white-space:nowrap}.career-link:hover{text-decoration:underline}
    .career-banner{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:20px 23px;margin:20px 0;border:1px solid #e2e6dc;border-radius:16px;background:linear-gradient(110deg,#f2f4eb,#f1edfb)}.career-banner h2{font-size:17px;margin:0 0 4px}.career-banner p:not(.eyebrow){font-size:12px;color:#58655d;margin:0}.career-banner .button{flex:none}
    .utility-link,.access-button{font-size:11px;text-decoration:none;color:var(--green);font-weight:800;border:0;background:none;cursor:pointer;white-space:nowrap}.access-tools{display:flex;gap:5px;align-items:center}.access-button{padding:6px 8px;border:1px solid var(--line);border-radius:9px;background:#fff}.tool-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px;margin:20px 0}.tool-card{padding:20px;background:white;border:1px solid var(--line);border-radius:16px}.tool-card h2{font-size:18px;margin:0 0 8px}.tool-card p,.tool-card label{font-size:12px;color:var(--muted);line-height:1.6}.tool-card input[type=text],.tool-card input[type=number],.tool-card textarea,.topic-search{width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--ink);font:inherit}.tool-card textarea{min-height:90px;resize:vertical}.tool-controls{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.tool-list{display:grid;gap:8px;margin-top:13px}.tool-item{padding:12px;border:1px solid var(--line);border-radius:11px;background:#fafbf8}.tool-item a{color:var(--green);font-weight:800;text-decoration:none}.topic-tools{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin:0 0 14px}.topic-tools .topic-search{flex:1;min-width:210px}.filter-select{padding:10px;border:1px solid var(--line);border-radius:9px;background:white;color:var(--ink)}.lesson-tools{display:flex;gap:9px;flex-wrap:wrap;margin:0 0 16px}.tool-status{font-size:12px;color:var(--green);font-weight:700;min-height:18px}.access-large{font-size:1.12em!important}.access-larger{font-size:1.25em!important}.high-contrast{--ink:#000;--muted:#222;--green:#003d20;--line:#111;--white:#fff;background:#fff!important}.high-contrast .subject-card,.high-contrast .tool-card,.high-contrast .lesson-panel{border:2px solid #111}
    .career-hero{padding:28px 32px;border-radius:22px;background:linear-gradient(125deg,#e5eee5,#f1eaff);animation:appear .45s both}.career-hero h1{font-size:clamp(30px,5vw,44px);letter-spacing:-.05em;margin:3px 0 9px}.career-hero p{max-width:800px;color:#53635a;font-size:13px;margin:0}.career-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin:18px 0}.career-card,.career-result{padding:18px;border:1px solid var(--line);border-radius:15px;background:white;box-shadow:0 5px 18px #24332808}.career-card h3,.career-result h3{font-size:15px;margin:0 0 8px}.career-card p,.career-result p{font-size:12px;color:#56645a;margin:0 0 8px;line-height:1.55}.career-paths{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:16px 0}.career-path{padding:19px;border-radius:16px;background:#fff;border:1px solid var(--line)}.career-path h3{margin:0 0 8px;font-size:16px}.career-path p,.career-path li{font-size:12px;color:#58655d;line-height:1.55}.career-path ul{padding-left:19px;margin:8px 0}.career-test{margin-top:24px;padding:23px;border:1px solid var(--line);border-radius:18px;background:white}.career-test h2{font-size:22px;margin:0 0 7px}.career-test>p{font-size:12px;color:var(--muted)}.career-stage{display:flex;gap:12px;flex-wrap:wrap;padding:14px;margin:15px 0;background:#f6f8f3;border-radius:12px}.career-stage label{display:flex;align-items:center;gap:7px;font-size:12px;font-weight:700}.career-question{padding:15px 0;border-top:1px solid #edf0e9}.career-question h3{font-size:13px;margin:0 0 8px}.career-option{display:flex;gap:9px;align-items:flex-start;margin:6px 0;padding:9px 11px;border:1px solid #ecefe8;border-radius:10px;font-size:11px;color:#526157;cursor:pointer}.career-option:hover{background:#f7f9f5;border-color:#bfd0c3}.career-option input{accent-color:#4d7465;flex:none;margin-top:2px}.career-results{margin:20px 0;padding:20px;border-radius:17px;background:linear-gradient(135deg,#eef5e8,#f6f1ff)}.career-results h2{margin:0 0 8px}.career-results-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.career-links{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}.career-links a{font-size:12px;color:var(--green);font-weight:800}
    @keyframes planet3d{0%,100%{transform:rotateX(-13deg) rotateY(-15deg) rotateZ(-8deg)}50%{transform:rotateX(14deg) rotateY(165deg) rotateZ(8deg)}}@keyframes orbit3d{to{transform:rotateX(68deg) rotateY(-16deg) rotateZ(360deg)}}
    @media(max-width:800px){.nmt-banner{align-items:flex-start;flex-direction:column}.nmt-banner .button{align-self:flex-start}.career-grid{grid-template-columns:repeat(2,1fr)}.career-banner{align-items:flex-start;flex-direction:column}}
    @media(max-width:540px){.topbar{height:auto;min-height:67px;flex-wrap:wrap;gap:8px;padding:8px 12px}.top-actions{gap:6px;flex-wrap:wrap;justify-content:flex-end}.grade-switch{max-width:100%;overflow-x:auto}.grade-switch a{min-width:34px;padding:6px 5px;font-size:10px}.nmt-banner{padding:18px}.nmt-banner h2{font-size:18px}.career-grid,.career-paths,.career-results-grid{grid-template-columns:1fr}.career-hero{padding:22px 19px}.career-test{padding:17px}}
    @media(prefers-reduced-motion:reduce){*,*::before,*::after{scroll-behavior:auto!important;animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important}.subject-card:hover{transform:none!important}}
    @media(max-width:800px){.tool-grid{grid-template-columns:1fr}}
    @media(max-width:540px){.access-tools{width:100%;justify-content:flex-end}.topbar{height:auto}.tool-card{padding:16px}.topic-tools{align-items:stretch}.filter-select{width:100%}}
  </style>
  <link rel="stylesheet" href="{{ url_for('static', filename='design-system.css') }}">
</head>
<body>
  <header class="topbar">
    <a class="brand" href="{{ url_for('index') }}"><span class="brand-icon">Р</span><span>Розумник<small>твій простір для відкриттів</small></span></a>
  <div class="top-actions"><a class="career-link" data-i18n="careers" href="{{ url_for('career_guide', grade=grade) }}">🧭 Професії</a><a class="utility-link" data-i18n="tools" href="{{ url_for('learning_tools', grade=grade) }}">🧰 Мої інструменти</a><a class="progress-link" data-i18n="progress" href="{{ url_for('progress_page', grade=grade) }}">Мій прогрес</a><div class="access-tools"><button class="access-button" type="button" data-font="increase" aria-label="Збільшити шрифт">A+</button><button class="access-button" type="button" data-contrast aria-label="Контрастний режим">◐</button><button class="access-button" type="button" data-speak aria-label="Озвучити сторінку">🔊</button><button class="access-button" type="button" data-language>UA/EN</button></div><nav class="grade-switch" aria-label="Обрати клас">{% for class_number in range(5, 12) %}<a class="{{ 'active' if grade == class_number else '' }}" href="{{ url_for('index', grade=class_number) }}">{{ class_number }}</a>{% endfor %}</nav></div>
  </header>
  <main>{{ content|safe }}</main>
  <footer>Розумник · Навчайся у своєму темпі, відкривай нове щодня</footer>
  <script>
    const KEY='rozumnyk-completed-lessons-v1';
    const BOOKMARK_KEY='rozumnyk-bookmarks-v1', NOTES_KEY='rozumnyk-notes-v1', MISTAKES_KEY='rozumnyk-mistakes-v1', PLAN_KEY='rozumnyk-week-plan-v1', ACTIVITY_KEY='rozumnyk-activity-v1';
    function readDone(){try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch(e){return []}}
    function paintProgress(){const done=readDone();document.querySelectorAll('[data-progress-subject]').forEach(el=>{const slug=el.dataset.progressSubject;const n=done.filter(x=>x.startsWith(slug+':')).length;el.textContent=n+' / '+el.dataset.total+' тем'});document.querySelectorAll('[data-progress-bar]').forEach(el=>{const slug=el.dataset.progressBar;const n=done.filter(x=>x.startsWith(slug+':')).length;el.style.width=Math.min(100,n/Number(el.dataset.total||1)*100)+'%'});document.querySelectorAll('[data-lesson-key]').forEach(el=>{if(done.includes(el.dataset.lessonKey)){const badge=el.querySelector('.done');if(badge)badge.textContent='✓'}});const total=document.querySelector('[data-total-done]');if(total)total.textContent=done.length}
    document.querySelectorAll('[data-control-passed="true"]').forEach(el=>{const k=el.dataset.lessonKey;const done=readDone();if(k&&!done.includes(k)){done.push(k);localStorage.setItem(KEY,JSON.stringify(done))}});
    function readStore(key,fallback){try{return JSON.parse(localStorage.getItem(key)||JSON.stringify(fallback))}catch(e){return fallback}}
    function saveStore(key,value){localStorage.setItem(key,JSON.stringify(value))}
    function todayKey(){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
    function markActivity(){const a=readStore(ACTIVITY_KEY,{days:[]});const today=todayKey();if(!a.days.includes(today)){a.days.push(today);a.days.sort();saveStore(ACTIVITY_KEY,a)}}
    document.querySelectorAll('[data-control-passed="true"]').forEach(el=>markActivity());
    const quizForm=document.querySelector('.quiz form');if(quizForm)quizForm.addEventListener('submit',()=>{const quiz=quizForm.closest('.quiz'), key=quiz.dataset.lessonKey, misses=readStore(MISTAKES_KEY,[]);quizForm.querySelectorAll('.control-question').forEach((q,i)=>{const chosen=q.querySelector('input:checked');const correct=Number(q.dataset.correct);if(chosen&&Number(chosen.value)!==correct){const opts=[...q.querySelectorAll('.choice span')].map(x=>x.textContent.trim());const record={id:key+':'+i,key,question:q.querySelector('h3').textContent.replace(/^\\d+\\.\\s*/,''),options:opts,correct,href:location.pathname+location.search};if(!misses.some(x=>x.id===record.id))misses.push(record)}});saveStore(MISTAKES_KEY,misses);markActivity()});
    document.querySelectorAll('[data-lesson-bookmark]').forEach(btn=>{const key=btn.dataset.lessonBookmark;const update=()=>{const arr=readStore(BOOKMARK_KEY,[]);btn.textContent=arr.some(x=>x.key===key)?'★ У закладках':'☆ Додати в закладки'};update();btn.addEventListener('click',()=>{let arr=readStore(BOOKMARK_KEY,[]);if(arr.some(x=>x.key===key))arr=arr.filter(x=>x.key!==key);else arr.push({key,title:btn.dataset.title,href:btn.dataset.href});saveStore(BOOKMARK_KEY,arr);update()})});
    document.querySelectorAll('[data-lesson-note]').forEach(area=>{const key=area.dataset.lessonNote, notes=readStore(NOTES_KEY,{});area.value=notes[key]||'';area.addEventListener('input',()=>{const current=readStore(NOTES_KEY,{});current[key]=area.value;saveStore(NOTES_KEY,current);const status=document.querySelector('[data-note-status]');if(status)status.textContent='Нотатку збережено на цьому пристрої'})});
    document.querySelectorAll('[data-topic-search]').forEach(input=>{const list=document.querySelector(input.dataset.topicSearch);if(!list)return;const rows=[...list.querySelectorAll('[data-topic-row]')];const filter=document.querySelector('[data-topic-filter]');const run=()=>rows.forEach(row=>{const match=row.dataset.topicTitle.toLocaleLowerCase().includes(input.value.toLocaleLowerCase());const state=filter?.value||'all';const done=readDone().includes(row.dataset.lessonKey);row.hidden=!(match&&(state==='all'||(state==='done'&&done)||(state==='todo'&&!done)))});input.addEventListener('input',run);filter?.addEventListener('change',run)});
    const subjectSearch=document.querySelector('[data-subject-search]');if(subjectSearch)subjectSearch.addEventListener('input',()=>document.querySelectorAll('[data-subject-card]').forEach(card=>card.hidden=!card.dataset.subjectTitle.toLocaleLowerCase().includes(subjectSearch.value.toLocaleLowerCase())));
    document.querySelectorAll('[data-font]').forEach(btn=>btn.addEventListener('click',()=>{let size=Number(localStorage.getItem('rozumnyk-font-size')||0);size=Math.min(2,size+1);localStorage.setItem('rozumnyk-font-size',size);document.body.classList.toggle('access-large',size===1);document.body.classList.toggle('access-larger',size===2)}));
    let fontSize=Number(localStorage.getItem('rozumnyk-font-size')||0);document.body.classList.toggle('access-large',fontSize===1);document.body.classList.toggle('access-larger',fontSize===2);
    const contrastButton=document.querySelector('[data-contrast]');if(localStorage.getItem('rozumnyk-contrast')==='on')document.body.classList.add('high-contrast');contrastButton?.addEventListener('click',()=>{document.body.classList.toggle('high-contrast');localStorage.setItem('rozumnyk-contrast',document.body.classList.contains('high-contrast')?'on':'off')});
    document.querySelector('[data-speak]')?.addEventListener('click',()=>{if(!('speechSynthesis'in window)){alert('Озвучення не підтримується цим браузером.');return}speechSynthesis.cancel();const text=(document.querySelector('main')?.innerText||'').slice(0,12000);const utterance=new SpeechSynthesisUtterance(text);utterance.lang='uk-UA';speechSynthesis.speak(utterance)});
    const translations={careers:['🧭 Професії','🧭 Careers'],tools:['🧰 Мої інструменти','🧰 My tools'],progress:['Мій прогрес','My progress']};
    function setLanguage(lang){document.documentElement.lang=lang==='en'?'en':'uk';document.querySelectorAll('[data-i18n]').forEach(el=>{const pair=translations[el.dataset.i18n];if(pair)el.textContent=pair[lang==='en'?1:0]});localStorage.setItem('rozumnyk-ui-language',lang)}
    const langButton=document.querySelector('[data-language]');langButton?.addEventListener('click',()=>setLanguage(localStorage.getItem('rozumnyk-ui-language')==='en'?'uk':'en'));if(localStorage.getItem('rozumnyk-ui-language')==='en')setLanguage('en');
    const toolRoot=document.querySelector('[data-learning-tools]');if(toolRoot){const grade=toolRoot.dataset.grade;fetch('/study-items?grade='+encodeURIComponent(grade)).then(r=>r.json()).then(items=>initLearningTools(toolRoot,items)).catch(()=>{toolRoot.innerHTML='<p>Не вдалося завантажити список тем. Онови сторінку.</p>'})}
    function initLearningTools(root,items){const planKey=PLAN_KEY+":"+root.dataset.grade;const esc=s=>String(s).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));const bookmarks=readStore(BOOKMARK_KEY,[]),notes=readStore(NOTES_KEY,{}),misses=readStore(MISTAKES_KEY,[]),done=readDone();const bookmarkBox=root.querySelector('[data-bookmark-list]');bookmarkBox.innerHTML=bookmarks.length?bookmarks.map(b=>'<div class="tool-item"><a href="'+esc(b.href)+'">'+esc(b.title)+'</a> <button type="button" data-remove-bookmark="'+esc(b.key)+'">Прибрати</button></div>').join(''):'<p>Закладок поки немає. Додавай їх на сторінці уроку.</p>';root.querySelectorAll('[data-remove-bookmark]').forEach(b=>b.onclick=()=>{saveStore(BOOKMARK_KEY,readStore(BOOKMARK_KEY,[]).filter(x=>x.key!==b.dataset.removeBookmark));location.reload()});const notesBox=root.querySelector('[data-note-list]');const noteItems=Object.entries(notes).filter(([,v])=>v.trim());notesBox.innerHTML=noteItems.length?noteItems.map(([k,v])=>{const item=items.find(x=>x.key===k);return '<div class="tool-item"><a href="'+esc(item?.href||'#')+'">'+esc(item?.title||k)+'</a><p>'+esc(v)+'</p></div>'}).join(''):'<p>Нотаток поки немає. Залиш нотатку в уроці.</p>';const mistakeBox=root.querySelector('[data-mistake-list]');mistakeBox.innerHTML=misses.length?misses.map((m,i)=>{const item=items.find(x=>x.key===m.key),related=items.filter(x=>item&&x.slug===item.slug&&x.key!==m.key).slice(0,2);return '<div class="tool-item" data-review-card="'+i+'"><p><strong>'+esc(m.question)+'</strong></p><form data-review-form="'+i+'">'+m.options.map((o,j)=>'<label><input type="radio" name="r'+i+'" value="'+j+'" required> '+esc(o)+'</label><br>').join('')+'<button type="submit">Перевірити відповідь</button></form><p data-review-feedback></p><a href="'+esc(m.href)+'">Повернутися до теми й пройти контрольну →</a><p>Схожі теми предмета: '+related.map(x=>'<a href="'+esc(x.href)+'">'+esc(x.title)+'</a>').join(' · ')+'</p><button type="button" data-remove-mistake="'+esc(m.id)+'">Прибрати з повторення</button></div>'}).join(''):'<p>Помилок для повторення ще немає. Вони з’являться після контрольної, якщо відповідь буде неправильною.</p>';root.querySelectorAll('[data-review-form]').forEach(form=>form.onsubmit=e=>{e.preventDefault();const miss=misses[Number(form.dataset.reviewForm)],answer=Number(new FormData(form).values().next().value),feedback=form.parentElement.querySelector('[data-review-feedback]');if(answer===miss.correct){feedback.textContent='Правильно! Це питання прибрано з черги повторення.';saveStore(MISTAKES_KEY,readStore(MISTAKES_KEY,[]).filter(x=>x.id!==miss.id));setTimeout(()=>location.reload(),900)}else feedback.textContent='Спробуй ще раз. Перечитай пояснення в темі за посиланням нижче.'});root.querySelectorAll('[data-remove-mistake]').forEach(b=>b.onclick=()=>{saveStore(MISTAKES_KEY,readStore(MISTAKES_KEY,[]).filter(x=>x.id!==b.dataset.removeMistake));location.reload()});const streakBox=root.querySelector('[data-achievement-list]');const activity=readStore(ACTIVITY_KEY,{days:[]});let streak=0;const d=new Date();for(;;){const key=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');if(!activity.days.includes(key))break;streak++;d.setDate(d.getDate()-1)}const badges=[{n:1,t:'Перший крок',ok:done.length>=1},{n:10,t:'Десять тем',ok:done.length>=10},{n:50,t:'Дослідник',ok:done.length>=50},{n:100,t:'Майстер навчання',ok:done.length>=100},{n:3,t:'Три дні поспіль',ok:streak>=3},{n:7,t:'Тиждень регулярності',ok:streak>=7}];streakBox.innerHTML='<p><strong>'+streak+'</strong> дн. поспіль · <strong>'+done.length+'</strong> тем завершено</p>'+badges.map(x=>'<div class="tool-item">'+(x.ok?'🏅':'🔒')+' '+x.t+(x.ok?' — отримано':' — ціль: '+x.n)+'</div>').join('');const form=root.querySelector('[data-plan-form]');const selection=root.querySelector('[data-plan-subjects]');selection.innerHTML=[...new Map(items.map(x=>[x.slug,x.subject]))].entries().map(([slug,name])=>'<label><input type="checkbox" value="'+esc(slug)+'" checked> '+esc(name)+'</label>').join('');const saved=readStore(planKey,null);if(saved){form.elements.days.value=saved.days;form.elements.minutes.value=saved.minutes;selection.querySelectorAll('input').forEach(x=>x.checked=saved.subjects.includes(x.value));renderPlan(saved)}function renderPlan(p){const selected=items.filter(x=>p.subjects.includes(x.slug));const count=Math.min(selected.length,Math.max(1,Number(p.days)||5));const plan=Array.from({length:count},(_,i)=>selected[(i*3)%selected.length]).filter(Boolean);root.querySelector('[data-plan-output]').innerHTML=plan.map((x,i)=>'<div class="tool-item"><strong>День '+(i+1)+' · '+esc(p.minutes)+' хв</strong><br><a href="'+esc(x.href)+'">'+esc(x.subject)+' — '+esc(x.title)+'</a></div>').join('')||'<p>Обери хоча б один предмет для плану.</p>'}form.onsubmit=e=>{e.preventDefault();const p={days:Number(form.elements.days.value)||5,minutes:Number(form.elements.minutes.value)||20,subjects:[...selection.querySelectorAll('input:checked')].map(x=>x.value)};saveStore(planKey,p);renderPlan(p)}}
    paintProgress();
    if('IntersectionObserver'in window){const ob=new IntersectionObserver(items=>items.forEach(x=>{if(x.isIntersecting){x.target.classList.add('visible');ob.unobserve(x.target)}}),{threshold:.12});document.querySelectorAll('.reveal').forEach(x=>ob.observe(x))}
    if(matchMedia('(hover:hover) and (pointer:fine)').matches&&!matchMedia('(prefers-reduced-motion:reduce)').matches){document.querySelectorAll('.subject-card,.tool-card,.career-card,.career-result,.career-path,.progress-card').forEach(card=>{card.addEventListener('pointermove',event=>{const rect=card.getBoundingClientRect(),x=(event.clientX-rect.left)/rect.width-.5,y=(event.clientY-rect.top)/rect.height-.5;card.style.setProperty('--tilt-x',(x*5).toFixed(2)+'deg');card.style.setProperty('--tilt-y',(-y*5).toFixed(2)+'deg')});card.addEventListener('pointerleave',()=>{card.style.setProperty('--tilt-x','0deg');card.style.setProperty('--tilt-y','0deg')})})}
  </script>
</body>
</html>"""


def show_page(title, template, **values):
    grade = active_grade()
    values.setdefault("grade", grade)
    content = render_template_string(template, **values)
    return render_template_string(SHELL, title=title, content=Markup(content), grade=grade)


def active_grade():
    try:
        grade = int(request.args.get("grade", "5"))
    except ValueError:
        grade = 5
    return grade if grade in GRADES else 5


def get_subject(slug, grade=None):
    grade = grade or active_grade()
    return next((item for item in GRADES[grade] if item["slug"] == slug), None)


def get_lesson(subject, lesson_id):
    if not subject or lesson_id < 1 or lesson_id > len(subject["lessons"]):
        abort(404)
    return subject["lessons"][lesson_id - 1]


@app.get("/")
def index():
    grade = active_grade()
    subjects = GRADES[grade]
    lesson_count = sum(len(item["lessons"]) for item in subjects)
    return show_page(
        "Головна",
        """
        <section class="hero">
          <div>
            <p class="eyebrow">ПРИВІТ, ДОСЛІДНИКУ!</p>
            <h1>Навчайся.<br><em>Відкривай.</em><br>Зростай.</h1>
            <p class="intro">{% if grade == 11 %}Твій простір для підготовки до НМТ: систематизуй теми, тренуй тестові завдання й відстежуй прогрес.{% else %}Твій дружній навчальний простір для {{ grade }} класу. Обирай тему, розбирайся крок за кроком і перевіряй себе.{% endif %}</p>
            <a class="button" href="#subjects">Знайти свій предмет <span>↘</span></a>
            <div class="stats"><span><strong>{{ subjects|length }}</strong> навчальних напрямів</span><span><strong>{{ lesson_count }}</strong> тем для дослідження</span><span><strong data-total-done>0</strong> уже опрацьовано</span></div>
          </div>
          <div class="hero-visual" aria-hidden="true"><div class="hero-stage"><div class="hero-pedestal"></div><div class="hero-cube"><span class="hero-cube-face front">📚</span><span class="hero-cube-face back">✦</span><span class="hero-cube-face right">✏️</span><span class="hero-cube-face left">🔭</span><span class="hero-cube-face top">💡</span><span class="hero-cube-face bottom">🧩</span></div><div class="orbit"></div><div class="orbit orbit-tilt"></div><div class="planet">✦</div><div class="float-chip chip-a">✨ цікаві теми</div><div class="float-chip chip-b">🌱 твій темп</div><div class="float-chip chip-c">📚 {{ grade }} клас</div></div></div>
        </section>
        {% if grade == 11 %}<section class="nmt-banner"><div><p class="eyebrow">ФОКУС 11 КЛАСУ</p><h2>Готуємося до НМТ крок за кроком</h2><p>Обов’язкова база: українська мова, математика (алгебра й геометрія), історія України. Для предмета на вибір у тренажері є англійська (іноземна мова), українська література, біологія, географія, фізика та хімія. У кожній темі — 12 запитань і підказка для підготовки.</p></div><a class="button" href="{{ url_for('subject_page', slug='ukr-mova', grade=grade) }}">Почати з української мови　→</a></section>{% endif %}
        <section class="career-banner"><div><p class="eyebrow">ПЛАНУЙ НАСТУПНИЙ КРОК</p><h2>Ще обираєш, куди рухатися після школи?</h2><p>Порівняй освітні шляхи після 9-го та 12-го класу й пройди короткий тест на інтереси.</p></div><a class="button" href="{{ url_for('career_guide', grade=grade) }}">Дізнатися про напрями　→</a></section>
        <div class="topic-tools"><input class="topic-search" type="search" placeholder="Пошук предмета…" aria-label="Пошук предмета" data-subject-search></div>
        <div class="section-head" id="subjects"><div><p class="eyebrow">ОБИРАЙ, ЩО ЦІКАВО</p><h2>Предмети · {{ grade }} клас</h2></div><p>Почни з будь-якої теми →</p></div>
        <section class="subject-grid">
          {% for subject in subjects %}
          <a class="subject-card" data-subject-card data-subject-title="{{ subject.name|lower }}" style="--i:{{ loop.index0 }}" href="{{ url_for('subject_page', slug=subject.slug, grade=grade) }}">
            <div class="card-head"><span class="subject-icon">{{ subject.icon }}</span><span class="arrow">↗</span></div>
            <h3>{{ subject.name }}</h3><p>{{ subject.description }}</p>{% if subject.nmt_role %}<small class="nmt-badge">НМТ · {{ subject.nmt_role }}</small>{% endif %}{% if subject.reference_book %}<small class="reference-book">📚 {{ subject.reference_book }}</small>{% endif %}
            <div class="card-meta"><span>{{ subject.lessons|length }} теми</span><span class="mini-progress" data-progress-subject="{{ grade }}:{{ subject.slug }}" data-total="{{ subject.lessons|length }}">0 / {{ subject.lessons|length }} тем</span></div>
          </a>
          {% endfor %}
        </section>
        <aside class="note"><span>💡</span><p><strong>Про навчальні теми.</strong> Це тематичний огляд програм, а не точна копія одного підручника. Порядок і профіль предметів у школах можуть різнитися. У 11 класі добірка з НМТ є тренажером за основними напрямами; актуальний формат конкретного року перевіряй на сайті УЦОЯО.</p></aside>
        """,
        subjects=subjects,
        grade=grade,
        lesson_count=lesson_count,
    )


@app.get("/subject/<slug>")
def subject_page(slug):
    grade = active_grade()
    subject = get_subject(slug, grade)
    if not subject:
        abort(404)
    return show_page(
        subject["name"],
        """
        <nav class="crumb"><a href="{{ url_for('index', grade=grade) }}">Предмети</a>　/　{{ subject.name }}</nav>
        <section class="subject-banner"><span class="subject-icon">{{ subject.icon }}</span><div><p class="eyebrow">{{ subject.area }}</p><h1>{{ subject.name }}</h1><p>{{ subject.description }}</p>{% if subject.nmt_role %}<span class="nmt-badge">НМТ · {{ subject.nmt_role }}</span>{% endif %}{% if subject.reference_book %}<p class="reference-book">📚 Орієнтир для 6 класу: {{ subject.reference_book }}</p>{% endif %}</div></section>
        {% if subject.nmt_role %}<p class="nmt-subject-note">У темах є пояснення й контрольні з 12 запитань. Це тренування, а не повний демонстраційний варіант НМТ. Формат і програму свого року звіряй з офіційними матеріалами УЦОЯО.</p>{% endif %}
        <div class="section-head"><div><p class="eyebrow">ТВОЯ НАВЧАЛЬНА МАНДРІВКА · {{ grade }} КЛАС</p><h2>Теми й уроки</h2></div><p data-progress-subject="{{ grade }}:{{ subject.slug }}" data-total="{{ subject.lessons|length }}">0 / {{ subject.lessons|length }} тем</p></div>
        <div class="topic-tools"><input class="topic-search" type="search" placeholder="Знайти тему…" aria-label="Пошук теми" data-topic-search="#lesson-list"><select class="filter-select" aria-label="Фільтр тем" data-topic-filter><option value="all">Усі теми</option><option value="todo">Ще не пройдені</option><option value="done">Уже пройдені</option></select></div>
        <div class="lesson-list" id="lesson-list">
          {% for lesson in subject.lessons %}
          <a class="lesson-row" href="{{ url_for('lesson_page', subject_slug=subject.slug, lesson_id=loop.index, grade=grade) }}" data-topic-row data-topic-title="{{ lesson.title|lower }}" data-lesson-key="{{ grade }}:{{ subject.slug }}:{{ loop.index }}">
            <span class="lesson-no">{{ '%02d'|format(loop.index) }}</span><span class="lesson-title">{{ lesson.title }}<small>Пояснення · приклад · вправа · мінітест</small></span><span class="done"></span>
          </a>
          {% endfor %}
        </div>
        """,
        subject=subject,
        grade=grade,
    )


def lesson_content(subject, lesson, lesson_id, grade, submitted=False, score=0, selected_answers=None):
    selected_answers = selected_answers or []
    passing_score = 9 if len(lesson.get("control_work", [])) == 12 else 4
    passed = submitted and score >= passing_score
    return show_page(
        lesson["title"],
        """
        <div class="lesson-wrap">
          <nav class="crumb"><a href="{{ url_for('index', grade=grade) }}">Предмети</a>　/　<a href="{{ url_for('subject_page', slug=subject.slug, grade=grade) }}">{{ subject.name }}</a>　/　Тема {{ lesson_id }}</nav>
          <p class="lesson-label">{{ subject.icon }}　{{ subject.name|upper }}　·　ТЕМА {{ lesson_id }} З {{ subject.lessons|length }}</p>
          <h1 class="lesson-title-main">{{ lesson.title }}</h1>
          <div class="lesson-tools"><button class="access-button" type="button" data-lesson-bookmark data-lesson-key="{{ grade }}:{{ subject.slug }}:{{ lesson_id }}" data-title="{{ lesson.title }}" data-href="{{ url_for('lesson_page', subject_slug=subject.slug, lesson_id=lesson_id, grade=grade) }}">☆ Додати в закладки</button><a class="access-button" href="{{ url_for('learning_tools', grade=grade) }}">🧰 Мої інструменти</a></div>
          <section class="lesson-panel"><h2>📝 Моя нотатка до теми</h2><textarea data-lesson-note="{{ grade }}:{{ subject.slug }}:{{ lesson_id }}" placeholder="Запиши свої думки або те, що хочеш повторити…" aria-label="Моя нотатка до уроку"></textarea><p class="tool-status" data-note-status>Нотатка зберігається в цьому браузері.</p></section>
          <section class="lesson-panel"><h2>🧠 Розберімося</h2><p>{{ lesson.explain }}</p></section>
          <section class="lesson-panel example"><h2>💡 Приклад</h2><p>{{ lesson.example }}</p></section>
          <section class="lesson-panel task"><h2>✏️ Спробуй самостійно</h2><p>{{ lesson.task }}</p></section>
          {% if lesson.rule %}<section class="lesson-panel rule"><h2>📌 Запам’ятай правило</h2><p>{{ lesson.rule }}</p></section>{% endif %}
          {% if lesson.steps %}<section class="lesson-panel"><h2>🪜 Розв’язуємо крок за кроком</h2><ul>{% for step in lesson.steps %}<li>{{ step }}</li>{% endfor %}</ul></section>{% endif %}
          {% if lesson.common_mistake %}<section class="lesson-panel warning"><h2>⚠️ Типова помилка</h2><p>{{ lesson.common_mistake }}</p></section>{% endif %}
          {% if lesson.extra_task %}<section class="lesson-panel task"><h2>🚀 Завдання із зірочкою</h2><p>{{ lesson.extra_task }}</p></section>{% endif %}
          {% if lesson.nmt_tip %}<section class="lesson-panel nmt-tip"><h2>🎯 Підказка для НМТ · {{ lesson.nmt_role }}</h2><p>{{ lesson.nmt_tip }}</p></section>{% endif %}
          {% if lesson.study_guide %}<details class="course-guide"><summary>🧭 Пам’ятка з предмета</summary><ul class="guide-list">{% for point in lesson.study_guide %}<li>{{ point }}</li>{% endfor %}</ul></details>{% endif %}
          <section class="quiz" data-control-passed="{{ 'true' if passed else 'false' }}" data-lesson-key="{{ grade }}:{{ subject.slug }}:{{ lesson_id }}">
            <p class="eyebrow">{% if lesson.nmt_prep %}ТРЕНУВАННЯ НМТ · {% else %}КОНТРОЛЬНА РОБОТА · {% endif %}{{ lesson.control_work|length }} ЗАПИТАНЬ</p><h2>Перевір, як ти засвоїв тему</h2>
            {% if submitted %}<div class="quiz-message {{ 'good' if passed else 'try' }}">{% if passed %}Результат: {{ score }} із {{ lesson.control_work|length }}. Тему зараховано 🌟{% else %}Результат: {{ score }} із {{ lesson.control_work|length }}. Для зарахування потрібно {{ passing_score }} правильних відповідей. Перечитай тему й спробуй ще раз.{% endif %}</div>{% endif %}
            <form method="post" action="{{ url_for('quiz', subject_slug=subject.slug, lesson_id=lesson_id, grade=grade) }}">
              {% for question in lesson.control_work %}{% set question_index = loop.index0 %}<div class="control-question" data-correct="{{ question.answer }}"><h3>{{ loop.index }}. {{ question.question }}</h3>
                {% for option in question.options %}<label class="choice"><input type="radio" name="answer_{{ question_index }}" value="{{ loop.index0 }}" {% if selected_answers and selected_answers[question_index] == loop.index0|string %}checked{% endif %} required> <span>{{ option }}</span></label>{% endfor %}
              </div>{% endfor %}
              <button class="button" type="submit">Перевірити контрольну <span>→</span></button>
            </form>
          </section>
          <nav class="lesson-nav">
            {% if lesson_id > 1 %}<a href="{{ url_for('lesson_page', subject_slug=subject.slug, lesson_id=lesson_id-1, grade=grade) }}">← Попередня тема</a>{% else %}<span></span>{% endif %}
            {% if lesson_id < subject.lessons|length %}<a href="{{ url_for('lesson_page', subject_slug=subject.slug, lesson_id=lesson_id+1, grade=grade) }}">Наступна тема →</a>{% else %}<a href="{{ url_for('subject_page', slug=subject.slug, grade=grade) }}">До всіх тем →</a>{% endif %}
          </nav>
        </div>
        """,
        subject=subject,
        lesson=lesson,
        lesson_id=lesson_id,
        grade=grade,
        submitted=submitted,
        score=score,
        passing_score=passing_score,
        selected_answers=selected_answers,
    )


@app.get("/lesson/<subject_slug>/<int:lesson_id>")
def lesson_page(subject_slug, lesson_id):
    grade = active_grade()
    subject = get_subject(subject_slug, grade)
    lesson = get_lesson(subject, lesson_id)
    return lesson_content(subject, lesson, lesson_id, grade)


@app.post("/quiz/<subject_slug>/<int:lesson_id>")
def quiz(subject_slug, lesson_id):
    grade = active_grade()
    subject = get_subject(subject_slug, grade)
    lesson = get_lesson(subject, lesson_id)
    selected_answers = [request.form.get(f"answer_{index}", "") for index in range(len(lesson["control_work"]))]
    score = sum(selected == str(question["answer"]) for selected, question in zip(selected_answers, lesson["control_work"]))
    return lesson_content(subject, lesson, lesson_id, grade, submitted=True, score=score, selected_answers=selected_answers)


@app.get("/progress")
def progress_page():
    grade = active_grade()
    return show_page(
        "Мій прогрес",
        """
        <section class="progress-page">
          <nav class="crumb"><a href="{{ url_for('index', grade=grade) }}">Предмети</a>　/　Мій прогрес</nav>
          <p class="eyebrow">ТВОЇ НАВЧАЛЬНІ ПЕРЕМОГИ</p><h1>Мій прогрес</h1>
          <p class="intro">Теми зараховуються після щонайменше {{ 9 if grade >= 8 else 4 }} правильних відповідей із {{ 12 if grade >= 8 else 5 }} у контрольній роботі. Дані зберігаються в цьому браузері.</p>
          {% for subject in subjects %}<section class="progress-class"><h2>{{ subject.icon }} {{ subject.name }}</h2><div class="progress-grid"><article class="progress-card"><h3>Опрацьовано тем</h3><div class="progress-track"><span data-progress-bar="{{ grade }}:{{ subject.slug }}" data-total="{{ subject.lessons|length }}"></span></div><p data-progress-subject="{{ grade }}:{{ subject.slug }}" data-total="{{ subject.lessons|length }}">0 / {{ subject.lessons|length }} тем</p></article></div></section>{% endfor %}
        </section>
        """,
        subjects=GRADES[grade],
        grade=grade,
    )


@app.get("/study-items")
def study_items():
    grade = active_grade()
    items = []
    for subject in GRADES[grade]:
        for index, lesson in enumerate(subject["lessons"], 1):
            items.append({
                "key": f"{grade}:{subject['slug']}:{index}",
                "slug": subject["slug"],
                "subject": subject["name"],
                "title": lesson["title"],
                "href": url_for("lesson_page", subject_slug=subject["slug"], lesson_id=index, grade=grade),
            })
    return jsonify(items)


@app.get("/learning-tools")
def learning_tools():
    return show_page(
        "Мої інструменти",
        """
        <nav class="crumb"><a href="{{ url_for('index', grade=grade) }}">Предмети</a>　/　Мої інструменти</nav>
        <p class="eyebrow">ТВІЙ ОСОБИСТИЙ НАВЧАЛЬНИЙ ПРОСТІР</p><h1>Мої інструменти й налаштування</h1>
        <p class="intro">Плануй навчання, повертайся до збережених тем, переглядай помилки й відзначай свої успіхи. Ці дані зберігаються лише в цьому браузері.</p>
        <div class="tool-grid" data-learning-tools data-grade="{{ grade }}">
          <section class="tool-card"><h2>🗓️ План на тиждень</h2><p>Обери предмети, скільки днів займатимешся та тривалість одного заняття. План добере теми з поточного класу.</p><form data-plan-form><label>Днів навчання на тиждень <input type="number" name="days" min="1" max="7" value="5"></label><label>Хвилин на день <input type="number" name="minutes" min="10" max="180" step="5" value="25"></label><p>Предмети:</p><div class="tool-controls" data-plan-subjects></div><button class="button" type="submit">Зберегти план</button></form><div class="tool-list" data-plan-output></div></section>
          <section class="tool-card"><h2>🔖 Закладки</h2><p>Теми, до яких хочеться швидко повернутися.</p><div class="tool-list" data-bookmark-list></div></section>
          <section class="tool-card"><h2>📝 Нотатки</h2><p>Твої короткі записи з уроків.</p><div class="tool-list" data-note-list></div></section>
          <section class="tool-card"><h2>🔁 Повторення помилок</h2><p>Переглянь питання, у яких помилився/помилилася, і повтори відповідні теми. У контрольній можна пройти завдання знову; поруч є посилання на інші уроки предмета.</p><div class="tool-list" data-mistake-list></div></section>
          <section class="tool-card"><h2>🏅 Досягнення та регулярність</h2><p>Зараховані уроки й дні активного навчання допоможуть бачити поступ.</p><div class="tool-list" data-achievement-list></div></section>
          <section class="tool-card"><h2>♿ Доступність</h2><p>Ці кнопки також є у верхній частині сайту: збільшення шрифту, контрастний режим, озвучення сторінки та перемикач мови меню.</p><div class="tool-controls"><button class="access-button" data-font="increase" type="button">A+ Збільшити шрифт</button><button class="access-button" data-contrast type="button">◐ Контраст</button><button class="access-button" data-speak type="button">🔊 Озвучити</button><button class="access-button" data-language type="button">UA/EN</button></div><p>Перекладаються окремі елементи меню; навчальні уроки наразі залишаються українською.</p></section>
        </div>
        <section class="career-path"><p class="eyebrow">ПРО ПРОФЕСІЇ</p><h2>Досліджуй напрям, який тебе зацікавив</h2><p>У профорієнтаційному розділі є приклади професій і посилання на офіційні ресурси, де можна перевірити професійні програми та заклади. Переглянь програми в <a href="https://proftech.mon.gov.ua/" target="_blank" rel="noopener">порталі професійної освіти</a> або знайди освітні програми через <a href="https://registry.edbo.gov.ua/" target="_blank" rel="noopener">ЄДЕБО</a>. Умови вступу перевіряй безпосередньо в обраному закладі.</p><a class="button" href="{{ url_for('career_guide', grade=grade) }}">Перейти до тесту про професії →</a></section>
        """,
        grade=active_grade(),
    )


@app.route("/career-guide", methods=["GET", "POST"])
def career_guide():
    stage = request.form.get("stage", "after9") if request.method == "POST" else request.args.get("stage", "after9")
    if stage not in ("after9", "after12"):
        stage = "after9"

    submitted = False
    error_message = ""
    results = []
    if request.method == "POST":
        selected = [request.form.get(f"q{index}", "") for index in range(len(CAREER_QUESTIONS))]
        if any(answer not in CAREER_CATEGORIES for answer in selected):
            error_message = "Будь ласка, обери по одній відповіді в кожному запитанні."
        else:
            scores = {key: 0 for key in CAREER_CATEGORIES}
            for answer in selected:
                scores[answer] += 1
            best = sorted(CAREER_CATEGORIES, key=lambda key: scores[key], reverse=True)
            best = [key for key in best if scores[key] > 0][:2]
            results = [
                {
                    "name": CAREER_CATEGORIES[key]["name"],
                    "professions": CAREER_CATEGORIES[key]["professions"],
                    "skills": CAREER_CATEGORIES[key]["skills"],
                    "pathway": CAREER_CATEGORIES[key][stage],
                    "points": scores[key],
                }
                for key in best
            ]
            submitted = True

    questions = [
        {"prompt": question["prompt"], "choices": question["choices"], "index": index}
        for index, question in enumerate(CAREER_QUESTIONS)
    ]
    return show_page(
        "Профорієнтація",
        """
        <nav class="crumb"><a href="{{ url_for('index', grade=grade) }}">Предмети</a>　/　Профорієнтація</nav>
        <section class="career-hero">
          <p class="eyebrow">ТВОЇ ІНТЕРЕСИ · ТВОЇ МОЖЛИВОСТІ</p>
          <h1>Куди рухатися далі?</h1>
          <p>Подивись на освітні шляхи після 9-го й 12-го класу, а потім пройди тест із 12 запитань. Він підкаже, які напрями й професії можуть тобі відгукнутися.</p>
        </section>

        <div class="career-paths">
          <article class="career-path">
            <p class="eyebrow">ПІСЛЯ 9 КЛАСУ</p><h3>Можна продовжити різними шляхами</h3>
            <ul>
              <li><strong>Академічний ліцей:</strong> продовжити навчання, обрати профіль і готуватися до подальшого вступу. Мережа ліцеїв розгортається поступово, тож перевір, які варіанти є у твоїй громаді.</li>
              <li><strong>Професійний коледж або заклад професійної освіти:</strong> поєднати загальну освіту з опануванням практичної професії.</li>
              <li><strong>Фаховий коледж:</strong> дізнатися про прикладні програми та конкретні правила вступу для випускників 9 класу.</li>
            </ul>
            <p>Порівняй предмети, практику, гуртожиток, дорогу й умови вступу — не лише назву закладу.</p>
          </article>
          <article class="career-path">
            <p class="eyebrow">ПІСЛЯ 12 КЛАСУ</p><h3>Обирай, як поглибити підготовку</h3>
            <ul>
              <li><strong>Університет:</strong> бакалаврська програма за напрямом, який хочеш досліджувати глибше.</li>
              <li><strong>Фаховий коледж:</strong> прикладна спеціальність і багато практичного навчання.</li>
              <li><strong>Професійна освіта, робота або власний проєкт:</strong> здобути кваліфікацію, спробувати сферу й надалі продовжити навчання.</li>
            </ul>
            <p>Вступні вимоги, НМТ, творчі конкурси та строки щороку перевіряй на офіційних сторінках обраних закладів.</p>
          </article>
        </div>

        {% if submitted %}
        <section class="career-results" aria-live="polite">
          <p class="eyebrow">ТВОЇ ВІДПОВІДІ — ЦЕ ПІДКАЗКА, НЕ ВИРОК</p>
          <h2>Можуть відгукнутися ці напрями</h2>
          <p>Тест показує, які заняття ти обирав/обирала частіше. Це не оцінка здібностей і не остаточне рішення про професію.</p>
          <div class="career-results-grid">
            {% for result in results %}
            <article class="career-result">
              <p class="eyebrow">{{ result.points }} із 12 відповідей</p>
              <h3>{{ result.name }}</h3>
              <p><strong>Приклади професій:</strong> {{ result.professions }}.</p>
              <p><strong>Корисні навички:</strong> {{ result.skills }}.</p>
              <p><strong>Можливий наступний крок:</strong> {{ result.pathway }}</p>
              <p><a href="https://registry.edbo.gov.ua/" target="_blank" rel="noopener">Знайти освітні програми в ЄДЕБО ↗</a> · <a href="https://proftech.mon.gov.ua/" target="_blank" rel="noopener">Переглянути професійну освіту ↗</a></p>
            </article>
            {% endfor %}
          </div>
          <p>Обговори результати з рідними, учителем або кар’єрним радником. Спробуй короткий гурток, курс, волонтерство чи невеликий проєкт, щоб перевірити, чи подобається тобі ця сфера на практиці.</p>
        </section>
        {% endif %}

        {% if error_message %}<div class="quiz-message try">{{ error_message }}</div>{% endif %}
        <form class="career-test" method="post" action="{{ url_for('career_guide', grade=grade) }}">
          <h2>Тест на професійні інтереси</h2>
          <p>У кожному запитанні обери варіант, який найбільше схожий на тебе. Тут немає правильних чи неправильних відповідей.</p>
          <fieldset class="career-stage"><legend><strong>Для якого наступного кроку шукаєш ідеї?</strong></legend>
            <label><input type="radio" name="stage" value="after9" {% if stage == 'after9' %}checked{% endif %}> Після 9 класу</label>
            <label><input type="radio" name="stage" value="after12" {% if stage == 'after12' %}checked{% endif %}> Після 12 класу</label>
          </fieldset>
          {% for question in questions %}{% set question_index = loop.index0 %}
          <fieldset class="career-question"><legend><h3>{{ loop.index }}. {{ question.prompt }}</h3></legend>
            {% for category, option_text in question.choices %}<label class="career-option"><input type="radio" name="q{{ question_index }}" value="{{ category }}" required> <span>{{ option_text }}</span></label>{% endfor %}
          </fieldset>
          {% endfor %}
          <button class="button" type="submit">Побачити підказку за відповідями　→</button>
        </form>
        <div class="career-links">
          <a href="https://mon.gov.ua/news/de-navchatymutsia-starshoklasnyky-znaidit-svii-akademichnyi-litsei-u-hromadi" target="_blank" rel="noopener">Знайти академічний ліцей у громаді ↗</a>
          <a href="https://proftech.mon.gov.ua/" target="_blank" rel="noopener">Дізнатися про професійну освіту ↗</a>
          <a href="https://mon.gov.ua/osvita-2/vishcha-osvita-ta-osvita-doroslikh/vstupna-kampaniia-do-zvo/vstupna-kampaniia-do-zakladiv-vyshchoi-osvity-2026-roku/poriadok-pryiomu-dlia-zdobuttia-vyshchoi-osvity-v-2026-rotsi" target="_blank" rel="noopener">Правила вступу до університетів ↗</a>
        </div>
        <aside class="note"><span>ℹ️</span><p>Профорієнтаційний тест не визначає майбутнє та не замінює розмову з фахівцем. Навчальні траєкторії й правила вступу залежать від року, програми закладу та місцевої мережі. Перевіряй актуальну інформацію в закладі освіти й на сайтах МОН та ЄДЕБО.</p></aside>
        """,
        grade=active_grade(),
        stage=stage,
        questions=questions,
        results=results,
        submitted=submitted,
        error_message=error_message,
    )


@app.errorhandler(404)
def not_found(_error):
    return show_page(
        "Сторінку не знайдено",
        """
        <section class="empty"><div style="font-size:42px">🧭</div><p class="eyebrow">ЗДАЄТЬСЯ, МИ ЗВЕРНУЛИ НЕ ТУДИ</p><h1>Сторінку не знайдено</h1><p>Повернись до предметів і обери потрібну тему.</p><a class="button" href="{{ url_for('index', grade=grade) }}">На головну　→</a></section>
        """,
    ), 404


if __name__ == "__main__":
    app.run(debug=True)

