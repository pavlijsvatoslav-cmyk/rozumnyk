(() => {
  "use strict";

  const translations = {
    "До основного вмісту": "Skip to main content",
    "твій простір для відкриттів": "Your space for discovery",
    "Професії": "Careers",
    "Мої інструменти": "My tools",
    "Мій прогрес": "My progress",
    "Збільшити шрифт": "Increase font size",
    "Контрастний режим": "High contrast mode",
    "Обрати клас": "Choose grade",
    "Розумник · Навчайся у своєму темпі, відкривай нове щодня ·": "Rozumnyk · Learn at your own pace and discover something new every day ·",
    "Приватність і дані": "Privacy and data",
    "Головна": "Home",
    "Предмети": "Subjects",
    "Тема": "Topic",
    "Теми": "Topics",
    "Пояснення · приклад · вправа · мінітест": "Explanation · example · practice · mini quiz",
    "Навчальний маршрут": "Learning path",
    "Теми відкриваються по черзі. Пройди контрольну, щоб відкрити наступну. До вже пройдених тем можна повертатися.": "Topics unlock in order. Pass the quiz to open the next one. You can revisit completed topics.",
    "тем пройдено": "topics completed",
    "Починай звідси": "Start here",
    "Тема відкрита": "Topic unlocked",
    "Спершу пройди попередню тему": "Complete the previous topic first",
    "Пройдено": "Completed",
    "Почни з першої теми.": "Start with the first topic.",
    "Пройди відкриту тему, щоб продовжити.": "Complete the open topic to continue.",
    "Усі теми предмета пройдено — чудова робота!": "You completed every topic in this subject. Great work!",
    "Пройди першу тему, щоб відкрити наступну.": "Complete the first topic to unlock the next one.",
    "Після першої контрольної відкриється наступна тема.": "Pass the first quiz to unlock the next topic.",
    "Після контрольної відкриється наступна тема.": "Pass the quiz to unlock the next topic.",
    "Пройди контрольну, щоб відкрити наступну тему.": "Pass the quiz to unlock the next topic.",
    "Українська мова": "Ukrainian language",
    "Українська література": "Ukrainian literature",
    "Зарубіжна література": "World literature",
    "Іноземна мова (англійська)": "English",
    "Англійська мова": "English",
    "Математика": "Mathematics",
    "Алгебра": "Algebra",
    "Алгебра · блок математики": "Algebra · mathematics unit",
    "Геометрія": "Geometry",
    "Геометрія · блок математики": "Geometry · mathematics unit",
    "Пізнаємо природу": "Exploring nature",
    "Історія та громадянська освіта": "History and civics",
    "Історія України": "History of Ukraine",
    "Всесвітня історія": "World history",
    "Інформатика": "Computer science",
    "Технології": "Technology",
    "Мистецтво": "Art",
    "Здоров’я, безпека та добробут": "Health, safety, and well-being",
    "Етика й добросусідство": "Ethics and community",
    "Фізична культура": "Physical education",
    "Фізика": "Physics",
    "Фізика навколо нас": "Physics around us",
    "Хімія": "Chemistry",
    "Хімія навколо нас": "Chemistry around us",
    "Біологія": "Biology",
    "Географія": "Geography",
    "Правознавство": "Law",
    "Захист України": "Defense of Ukraine",
    "Привіт,": "Hello,",
    "досліднику!": "explorer!",
    "Займай своє місце в першому ряду. Тут кожна тема стає зрозумілою пригодою — крок за кроком, у твоєму темпі.": "Take your seat in the front row. Every topic becomes an easy-to-follow adventure, step by step and at your pace.",
    "Почати навчання": "Start learning",
    "Завдання дня": "Daily challenge",
    "Окрема підготовка до НМТ — у темах 11 класу.": "Dedicated NMT preparation is available in the Grade 11 topics.",
    "Інтерактивна модель Сонячної системи": "Interactive model of the Solar System",
    "Натисни на планету, щоб роздивитися її ближче": "Select a planet to explore it up close",
    "СОНЯЧНА СИСТЕМА · ОБЕРИ ПЛАНЕТУ": "SOLAR SYSTEM · CHOOSE A PLANET",
    "ДОСЛІДЖУЙ КОСМОС": "EXPLORE SPACE",
    "Обери планету": "Choose a planet",
    "Натисни на планету або обери її зі списку — вона підлетить ближче.": "Select a planet or choose one from the list to bring it closer.",
    "Цікаві факти": "Interesting fact",
    "Один оберт навколо Сонця": "One orbit around the Sun",
    "Кожен світ має власну атмосферу, поверхню та історію.": "Every world has its own atmosphere, surface, and story.",
    "Обрати планету": "Choose a planet",
    "Меркурій": "Mercury",
    "Венера": "Venus",
    "Земля": "Earth",
    "Марс": "Mars",
    "Юпітер": "Jupiter",
    "Сатурн": "Saturn",
    "Уран": "Uranus",
    "Нептун": "Neptune",
    "Повернути до системи": "Return to the Solar System",
    "Три основи підготовки до НМТ": "Three core subjects for NMT preparation",
    "Почни з обов’язкових предметів. У математиці є окремі теми з алгебри й геометрії.": "Start with the required subjects. Mathematics includes separate algebra and geometry topics.",
    "Правила, приклади й тренування →": "Rules, examples, and practice →",
    "Алгебра · графіки функцій →": "Algebra · function graphs →",
    "Події, постаті й хронологія →": "Events, people, and timelines →",
    "Потрібен предмет на вибір? Інші напрямки й надалі доступні у списку предметів нижче.": "Need an elective? Other subjects are available in the list below.",
    "Коротка діагностика →": "Quick check →",
    "Повний тренувальний НМТ →": "Full NMT practice test →",
    "Почни з теми, яка тебе цікавить": "Start with a topic that interests you",
    "Обери предмет і відкрий перший урок. Розумник запам’ятає, де ти зупинився.": "Choose a subject and open the first lesson. Rozumnyk will remember where you left off.",
    "Обрати предмет": "Choose a subject",
    "ПЛАНУЙ НАСТУПНИЙ КРОК": "PLAN YOUR NEXT STEP",
    "Ще обираєш, куди рухатися після школи?": "Still deciding what to do after school?",
    "Порівняй освітні шляхи після 9-го та 12-го класу й пройди короткий тест на інтереси.": "Compare study options after Grades 9 and 12, then take a short interests quiz.",
    "Дізнатися про напрями": "Explore career paths",
    "Пошук предмета…": "Search subjects…",
    "Пошук предмета": "Search subjects",
    "ОБИРАЙ, ЩО ЦІКАВО": "CHOOSE WHAT INTERESTS YOU",
    "Почни з будь-якої теми →": "Start with any topic →",
    "Про навчальні теми.": "About these topics.",
    "Це тематичний огляд програм, а не точна копія одного підручника. Порядок і профіль предметів у школах можуть різнитися. У 11 класі добірка з НМТ є тренажером за основними напрямами; актуальний формат конкретного року перевіряй на сайті УЦОЯО.": "This is a topic-based overview of the curriculum, not a copy of one textbook. Subject order and focus can vary by school. Grade 11 NMT topics provide practice in the core areas; check the official UCEQA website for the current exam format.",
    "ПЕРШИЙ КРОК ДО ПЛАНУ ПІДГОТОВКИ": "THE FIRST STEP IN YOUR STUDY PLAN",
    "Коротка діагностика до НМТ": "Quick NMT check",
    "12 навчальних запитань: по чотири з української мови, математики й історії України. Це швидкий орієнтир для повторення, а не повний варіант НМТ. Відповіді не зберігаються.": "12 study questions: four each in Ukrainian, mathematics, and the history of Ukraine. This is a quick guide for review, not a full NMT exam. Answers are not saved.",
    "Твій результат": "Your result",
    "Що повторити далі": "What to review next",
    "відкрити пояснення": "open explanation",
    "Чудово — усі відповіді правильні. Продовжуй тренуватися на темах 11 класу.": "Great — all answers are correct. Keep practicing with Grade 11 topics.",
    "Перевірити відповіді": "Check answers",
    "Практика на сьогодні": "Today’s practice",
    "ОДНЕ КОРОТКЕ ЗАВДАННЯ ЩОДНЯ": "ONE QUICK TASK EACH DAY",
    "Спробуй відповісти самостійно, а потім переглянь пояснення.": "Try to answer on your own, then read the explanation.",
    "Вірно! Гарна робота 🌟": "Correct! Great work 🌟",
    "Розберімо відповідь": "Let’s review the answer",
    "Правильна відповідь:": "Correct answer:",
    "Перевірити": "Check",
    "ТВОЯ НАВЧАЛЬНА МАНДРІВКА ·": "YOUR LEARNING JOURNEY ·",
    "Теми й уроки": "Topics and lessons",
    "Знайти тему…": "Find a topic…",
    "Пошук теми": "Search topics",
    "Фільтр тем": "Filter topics",
    "Усі теми": "All topics",
    "Ще не пройдені": "Not completed",
    "Уже пройдені": "Completed",
    "НМТ ·": "NMT ·",
    "Пояснення": "Explanation",
    "Приклад": "Example",
    "Вправа": "Practice",
    "Мінітест": "Mini quiz",
    "Додати в закладки": "Add bookmark",
    "Поділитися темою": "Share topic",
    "Зберегти для офлайну": "Save for offline use",
    "Конспект на друк": "Printable summary",
    "Повідомити про неточність": "Report an issue",
    "Моя нотатка до теми": "My topic notes",
    "Запиши свої думки або те, що хочеш повторити…": "Write your thoughts or what you want to review…",
    "Моя нотатка до уроку": "My lesson note",
    "Нотатка зберігається в цьому браузері.": "Your note is saved in this browser.",
    "Нотатку збережено на цьому пристрої": "Note saved on this device",
    "Розберімося": "Let’s understand it",
    "Пояснимо трохи глибше": "A closer look",
    "Як розібратися в темі": "How to work through this topic",
    "Рухайся від ідеї до прикладу, а потім перевір, чи можеш застосувати її самостійно.": "Move from the main idea to an example, then check whether you can apply it on your own.",
    "Карта теми": "Topic map",
    "ЗРОЗУМІЙ ІДЕЮ": "UNDERSTAND THE IDEA",
    "ПОБАЧ У ПРИКЛАДІ": "SEE IT IN AN EXAMPLE",
    "СПРОБУЙ САМ": "TRY IT YOURSELF",
    "Спробуй самостійно": "Try it yourself",
    "Розв’язуємо крок за кроком": "Let’s solve it step by step",
    "Типова помилка": "Common mistake",
    "Завдання із зірочкою": "Challenge task",
    "Підказка для НМТ": "NMT tip",
    "Пам’ятка з предмета": "Subject guide",
    "Помітив неточність або щось незрозуміло?": "Found an error or something unclear?",
    "Повідомлення перегляне команда сайту. Не додавай сюди особисті дані.": "The site team will review your report. Do not include personal information.",
    "Що саме?": "What is the issue?",
    "Пояснення незрозуміле": "The explanation is unclear",
    "Можлива помилка у факті або формулі": "Possible error in a fact or formula",
    "Малюнок чи приклад потребує виправлення": "An illustration or example needs correction",
    "Опиши коротко": "Briefly describe it",
    "Що саме варто перевірити?": "What should we check?",
    "Надіслати на перевірку": "Send for review",
    "Перевір, як ти засвоїв тему": "Check what you learned",
    "Перевірити контрольну": "Check answers",
    "← Попередня тема": "← Previous topic",
    "Наступна тема →": "Next topic →",
    "До всіх тем →": "All topics →",
    "Твої дані — під твоїм контролем": "Your data stays under your control",
    "Коротко пояснюємо, що зберігає «Розумник», де це зберігається і як видалити ці дані.": "Here is what Rozumnyk saves, where it is stored, and how to delete it.",
    "Обліковий запис не потрібен.": "No account is required.",
    "Що сайт зберігає в браузері": "What the site stores in your browser",
    "Як працюють контрольні": "How quizzes work",
    "Англійська мова": "English language",
    "Коли ти натискаєш кнопку EN, сторінка використовує вбудований словник перекладів. Текст не надсилається до зовнішнього сервісу. Основні написи доступні англійською; переклад пояснень до уроків поступово додається.": "When you choose EN, the page uses translations built into the site. Text is not sent to an external service. Main interface labels are available in English; lesson explanations are being translated gradually.",
    "Коли ти натискаєш кнопку EN, сторінка використовує вбудований словник перекладів. Текст сторінки не надсилається до зовнішнього сервісу. Основні написи доступні англійською; переклад пояснень до уроків поступово додається.": "When you choose EN, the page uses translations built into the site. Page text is not sent to an external service. Main interface labels are available in English; lesson explanations are being translated gradually.",
    "Щоб відкрити сторінку або перевірити контрольну, браузер надсилає запит сайту. Платформа хостингу може вести технічні журнали запитів за власними правилами. Вбудований перекладач працює у браузері й не надсилає текст до стороннього перекладача. Ця сторінка описує дані, які зберігає сам застосунок.": "To open a page or submit a quiz, your browser sends a request to the site. The hosting platform may keep technical request logs under its own policies. The built-in translator works in your browser and does not send text to a third-party translation service. This page describes data stored by the app itself.",
    "Зовнішня бібліотека для 3D-сцени": "External library for the 3D scene",
    "Видалити дані з цього браузера": "Delete data from this browser",
    "Видалити мої дані з цього браузера": "Delete my data from this browser",
    "Технічні запити": "Technical requests",
    "Мій прогрес": "My progress",
    "ТВОЇ НАВЧАЛЬНІ ПЕРЕМОГИ": "YOUR LEARNING MILESTONES",
    "Теми зараховуються після щонайменше": "Topics count as complete after at least",
    "правильних відповідей із": "correct answers out of",
    "у контрольній роботі. Дані зберігаються в цьому браузері.": "in the quiz. Data is saved in this browser.",
    "Опрацьовано тем": "Topics completed",
    "Мої інструменти": "My tools",
    "Мої інструменти й налаштування": "My tools and settings",
    "ТВІЙ ОСОБИСТИЙ НАВЧАЛЬНИЙ ПРОСТІР": "YOUR PERSONAL STUDY SPACE",
    "Плануй навчання, повертайся до збережених тем, переглядай помилки й відзначай свої успіхи. Ці дані зберігаються лише в цьому браузері.": "Plan your study, revisit saved topics, review mistakes, and track your progress. This data stays in this browser.",
    "Попередній місяць": "Previous month",
    "Наступний місяць": "Next month",
    "Календар навчання": "Study calendar",
    "Дні місяця": "Days of the month",
    "Що запланувати": "What would you like to plan?",
    "Наприклад, повторити дроби": "For example, review fractions",
    "Дата": "Date",
    "Навчальна тема (необов’язково)": "Study topic (optional)",
    "Без посилання на тему": "No topic link",
    "Додати до календаря": "Add to calendar",
    "Плани зберігаються у цьому браузері. Домашні завдання класу з терміном вказує вчитель у кабінеті класу.": "Plans are saved in this browser. The teacher posts class homework and due dates in the class portal.",
    "Калькулятор": "Calculator",
    "Чотири основні дії — без зайвих кнопок.": "Four basic operations, with no extra buttons.",
    "Стерти останню цифру": "Delete the last digit",
    "Ділення": "Division",
    "Множення": "Multiplication",
    "Віднімання": "Subtraction",
    "Десяткова крапка": "Decimal point",
    "На нуль ділити не можна.": "You cannot divide by zero.",
    "🧭 Мій персональний маршрут": "🧭 My personal study plan",
    "Обери мету й темп. План спершу запропонує незавершені теми та питання з черги помилок; дані залишаються у цьому браузері.": "Choose a goal and pace. The plan starts with unfinished topics and questions to review. Data stays in this browser.",
    "Мета": "Goal",
    "Підготуватися до НМТ": "Prepare for the NMT",
    "Надолужити теми": "Catch up on topics",
    "Досліджувати предмети": "Explore subjects",
    "Планувати до": "Plan until",
    "Днів навчання на тиждень": "Study days per week",
    "Хвилин на день": "Minutes per day",
    "Предмети:": "Subjects:",
    "Скласти мій маршрут": "Build my study plan",
    "🔖 Закладки": "🔖 Bookmarks",
    "Теми, до яких хочеться швидко повернутися.": "Topics you want to return to quickly.",
    "Закладок поки немає. Додавай їх на сторінці уроку.": "No bookmarks yet. Add one from a lesson page.",
    "Прибрати": "Remove",
    "📝 Нотатки": "📝 Notes",
    "Твої короткі записи з уроків.": "Your quick notes from lessons.",
    "Нотаток поки немає. Залиш нотатку в уроці.": "No notes yet. Add one on a lesson page.",
    "🔁 Повторення помилок": "🔁 Review mistakes",
    "Перевірити відповідь": "Check answer",
    "Повернутися до теми й пройти контрольну →": "Return to the topic and take the quiz →",
    "Схожі теми предмета:": "Related topics:",
    "Прибрати з повторення": "Remove from review",
    "Помилок для повторення ще немає. Вони з’являться після контрольної, якщо відповідь буде неправильною.": "No mistakes to review yet. Missed answers from quizzes will appear here.",
    "Правильно! Це питання прибрано з черги повторення.": "Correct! This question has been removed from your review list.",
    "Спробуй ще раз. Перечитай пояснення в темі за посиланням нижче.": "Try again. Review the explanation using the link below.",
    "🏅 Досягнення та регулярність": "🏅 Achievements and streaks",
    "Зараховані уроки й дні активного навчання допоможуть бачити поступ.": "Completed lessons and active study days help you track your progress.",
    "Перший крок": "First step",
    "Десять тем": "Ten topics",
    "Дослідник": "Explorer",
    "Майстер навчання": "Study master",
    "Три дні поспіль": "Three-day streak",
    "Тиждень регулярності": "One-week streak",
    "отримано": "earned",
    "ціль:": "goal:",
    "♿ Доступність": "♿ Accessibility",
    "Налаштуй зручний розмір тексту, контрастність або мову сторінки.": "Adjust text size, contrast, or page language.",
    "◐ Контраст": "◐ Contrast",
    "Англійський режим використовує вбудовані переклади. Пояснення до уроків перекладаються поступово.": "English mode uses built-in translations. Lesson explanations are being translated gradually.",
    "Англійська версія використовує вбудовані переклади й не потребує ключа або платного сервісу. Переклад пояснень уроків поступово додається.": "English mode uses built-in translations and needs no key or paid service. Lesson explanations are being translated gradually.",
    "✨ Щоденний виклик": "✨ Daily challenge",
    "Одне коротке запитання з предмета твого класу на кожен день.": "One short question from your grade’s subjects each day.",
    "Відкрити завдання дня →": "Open today’s challenge →",
    "Завершуй завдання щодня й стеж за регулярністю.": "Complete a task each day and keep your streak going.",
    "📴 Уроки офлайн": "📴 Offline lessons",
    "Збережи потрібну тему на цьому пристрої, щоб повернутися до неї без інтернету.": "Save a topic on this device to revisit it without internet access.",
    "На сторінці уроку натисни «Зберегти для офлайну».": "On a lesson page, choose “Save for offline use.”",
    "Встановити Розумник": "Install Rozumnyk",
    "Знайди відповідь на навчальне запитання й запиши, хто її опублікував.": "Find an answer to a study question and note who published it.",
    "Що допомагає оцінити надійність сторінки?": "What can help you judge whether a page is reliable?",
    "Автор і джерела": "Author and sources",
    "Кількість кольорів": "Number of colors",
    "Довжина адреси": "Address length",
    "На цю дату поки немає планів.": "No plans for this date yet.",
    "Завдання класу": "Class assignment",
    "Предмет і пояснення (необов’язково)": "Subject and lesson explanation (optional)",
    "Тема уроку": "Lesson topic",
    "Спочатку обери предмет": "Choose a subject first",
    "Не прив’язувати до окремої теми": "Do not link to a specific topic",
    "Переглянути пояснення до теми →": "Review the topic explanation →",
    "Відкрити предмет →": "Open subject →",
    "Фото або файл роботи (необов’язково)": "Photo or file of your work (optional)",
    "Можна надіслати текст, файл або обидва. До 15 МБ.": "Send text, a file, or both. Up to 15 MB.",
    "Відкрити роботу:": "Open submission:",
    "Домашніх робіт очікують перевірки:": "Homework awaiting review:",
    "Видалити план": "Remove plan",
    "День": "Day",
    "Хв": "min",
    "Обери хоча б один предмет для плану.": "Choose at least one subject for your plan.",
    "Обери хоча б один предмет для маршруту.": "Choose at least one subject for your study plan.",
    "Пошук і виправлення помилки": "Find and fix a mistake",
    "Скопіюй адресу теми з поля нижче.": "Copy the topic address from the field below.",
    "Посилання скопійовано. Надішли його тому, кому цікава ця тема.": "Link copied. Share it with someone who may find this topic useful.",
    "Дані та збережені уроки «Розумника» видалені з цього браузера.": "Rozumnyk data and saved lessons have been deleted from this browser.",
    "Частину даних не вдалося видалити. Перевір налаштування сховища браузера.": "Some data could not be deleted. Check your browser storage settings.",
    "Установлення доступне через меню браузера «Додати на головний екран»." : "You can install the site from your browser menu using “Add to home screen.”",
    "Зберігаю урок на цьому пристрої…": "Saving this lesson on your device…",
    "Готово. Цю тему можна відкрити без інтернету.": "Done. You can open this topic without internet access.",
    "Не вдалося зберегти урок. Перевір підключення та спробуй ще раз.": "Could not save the lesson. Check your connection and try again.",
    "Не вдалося завантажити список тем. Онови сторінку.": "Could not load the topic list. Refresh the page.",
    "Українська мова": "Ukrainian",
    "Математика · навчальний блок": "Mathematics · study unit",
    "Математика · вибіркова тема": "Mathematics · elective topic",
    "Історія України · обов’язковий предмет НМТ": "History of Ukraine · required NMT subject",
    "Переклад англійською": "English version",
    "Увімкнути англійську": "Switch to English",
    "Перемкнути на українську": "Switch to Ukrainian",
    "Англійська версія містить переклади інтерфейсу. Частина пояснень уроків поки українською.": "The English version includes translated interface text. Some lesson explanations are still in Ukrainian.",
    "Навчальні місії": "Learning missions",
    "Віртуальні лабораторії": "Virtual labs",
    "Мій маршрут": "My learning path",
    "Обери свою місію": "Choose a mission",
    "Місто, у якому зручно жити": "A city that is easy to live in",
    "Рятувальна команда для річки": "River rescue team",
    "База на Марсі": "Mars base",
    "ЗНАННЯ ПРАЦЮЮТЬ У СВІТІ": "KNOWLEDGE AT WORK IN THE REAL WORLD",
    "Твій поступ": "Your progress",
    "Моя ідея або результат": "My idea or result",
    "Занотуй план, висновок або наступне запитання…": "Write down a plan, conclusion, or next question…",
    "Місія не має єдиної правильної відповіді.": "There is no single right answer to a mission.",
    "ДОСЛІДЖУЙ БЕЗПЕЧНО": "EXPLORE SAFELY",
    "Показати моделі для класу": "Show models for grade",
    "У цьому класі поки немає інтерактивної моделі. Обери «Усі класи» або інший клас.": "There are no interactive models for this grade yet. Choose All grades or another grade.",
    "Відкрити модель у темі →": "Open the model in the lesson →",
    "ПЕРЕВІР НА ПРАКТИЦІ": "TRY IT IN PRACTICE",
    "Спробуй мініпрофесію за 5 хвилин": "Try a mini career task in 5 minutes",
    "Знайди середнє": "Find the average",
    "Порахувати": "Calculate",
    "Сплануй чесний дослід": "Plan a fair experiment",
    "Перевірити план": "Check the plan",
    "Поясни простими словами": "Explain it simply",
    "Перевірити пояснення": "Check the explanation",
    "Розподіли бюджет": "Plan a budget",
    "Знайди проблему в схемі": "Find the issue in the circuit",
    "Обери одну умову": "Choose one variable",
    "Моє пояснення": "My explanation",
    "Настрій": "Mood",
    "Спокій і природа": "Calm and nature",
    "Ідеї та космос": "Ideas and space",
    "Енергія і світло": "Energy and light",
    "Галерея проєктів класу": "Class project gallery",
    "Попросити додати роботу до галереї класу": "Ask to add work to the class gallery",
    "Схвалити показ": "Approve for sharing",
    "Прибрати з галереї": "Remove from gallery",
    "У галереї": "In gallery",
    "Просить показати класу": "Requested to share with class",
  };

  const patterns = [
    [/^(\d+) предметів у (\d+) класі$/, (_, count, grade) => `${count} subjects in Grade ${grade}`],
    [/^(\d+) тем для відкриття$/, (_, count) => `${count} topics to explore`],
    [/^(\d+) уже пройдено$/, (_, count) => `${count} completed`],
    [/^(\d+) теми$/, (_, count) => `${count} topics`],
    [/^(\d+) тем$/, (_, count) => `${count} topics`],
    [/^(\d+) \/ (\d+) тем$/, (_, done, total) => `${done} / ${total} topics`],
    [/^Предмети · (\d+) клас$/, (_, grade) => `Subjects · Grade ${grade}`],
    [/^ТЕМА (\d+) З (\d+)$/, (_, current, total) => `TOPIC ${current} OF ${total}`],
    [/^Тема (\d+)$/, (_, number) => `Topic ${number}`],
    [/^Тема: (.+)$/, (_, title) => `Topic: ${title}`],
    [/^Результат: (\d+) із (\d+)\. Тему зараховано 🌟$/, (_, score, total) => `Result: ${score} of ${total}. Topic completed 🌟`],
    [/^Результат: (\d+) із (\d+)\. Для зарахування потрібно (\d+) правильних відповідей\. Перечитай тему й спробуй ще раз\.$/, (_, score, total, needed) => `Result: ${score} of ${total}. You need ${needed} correct answers to pass. Review the topic and try again.`],
    [/^Теми зараховуються після щонайменше (\d+) правильних відповідей із (\d+) у контрольній роботі\. Дані зберігаються в цьому браузері\.$/, (_, needed, total) => `Topics count as complete after at least ${needed} correct answers out of ${total} in the quiz. Data is saved in this browser.`],
    [/^Навчання — (\d+) клас$/, (_, grade) => `Learning · Grade ${grade}`],
    [/^(.+) клас$/, (_, grade) => `Grade ${grade}`],
    [/^Від (\d+) днів до (\d+) років$/, (_, days, years) => `From ${days} days to ${years} years`],
    [/^Тема (\d+) з (\d+)$/, (_, current, total) => `Topic ${current} of ${total}`],
  ];

  const attributeNames = ["aria-label", "title", "placeholder", "alt"];
  const records = [];
  const recordsByNode = new WeakMap();
  let currentLanguage = "uk";
  let observer = null;

  function normalized(value) {
    return String(value).replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
  }

  function translate(value) {
    const key = normalized(value);
    if (Object.prototype.hasOwnProperty.call(translations, key)) return translations[key];
    const brandSuffix = " · Розумник";
    if (key.endsWith(brandSuffix)) {
      const translatedTitle = translate(key.slice(0, -brandSuffix.length));
      if (translatedTitle !== null) return `${translatedTitle} · Rozumnyk`;
    }
    for (const [pattern, replace] of patterns) {
      const match = key.match(pattern);
      if (match) return replace(...match);
    }
    return null;
  }

  function ignored(element) {
    return !element || element.closest(
      "script,style,noscript,template,textarea,input,[contenteditable='true'],[data-no-translate],[data-user-content],.submission-review,tbody td:first-child,.brand-icon,.translation-status",
    );
  }

  function recordFor(node, attribute, value) {
    let byAttribute = recordsByNode.get(node);
    if (!byAttribute) {
      byAttribute = new Map();
      recordsByNode.set(node, byAttribute);
    }
    let record = byAttribute.get(attribute);
    const read = () => attribute === "#text" ? node.nodeValue : node.getAttribute(attribute);
    if (!record) {
      record = { node, attribute, original: value, applied: null, read };
      byAttribute.set(attribute, record);
      records.push(record);
    } else if (record.applied === null || read() !== record.applied) {
      record.original = value;
      record.applied = null;
    }
    return record;
  }

  function assign(record, value) {
    if (record.attribute === "#text") record.node.nodeValue = value;
    else record.node.setAttribute(record.attribute, value);
    record.applied = value;
  }

  function translateNode(node) {
    const parent = node.parentElement;
    if (!parent || ignored(parent)) return;
    const value = node.nodeValue;
    if (!value || !/[\u0400-\u04ff]/.test(value)) return;
    const record = recordFor(node, "#text", value);
    if (currentLanguage === "uk") {
      if (record.applied !== null && record.read() === record.applied) assign(record, record.original);
      record.applied = null;
      return;
    }
    const leading = value.match(/^\s*/)?.[0] || "";
    const trailing = value.match(/\s*$/)?.[0] || "";
    const result = translate(record.original);
    if (result === null) return;
    const output = leading + result + trailing;
    if (value !== output) assign(record, output);
  }

  function translateAttributes(element) {
    if (ignored(element)) return;
    for (const attribute of attributeNames) {
      const value = element.getAttribute(attribute);
      if (!value || !/[\u0400-\u04ff]/.test(value)) continue;
      const record = recordFor(element, attribute, value);
      if (currentLanguage === "uk") {
        if (record.applied !== null && record.read() === record.applied) assign(record, record.original);
        record.applied = null;
        continue;
      }
      const result = translate(record.original);
      if (result !== null && result !== value) assign(record, result);
    }
  }

  function scan(root = document.body) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) translateNode(node);
    const elements = root.nodeType === Node.ELEMENT_NODE ? [root, ...root.querySelectorAll("*")] : [...root.querySelectorAll("*")];
    for (const element of elements) translateAttributes(element);
    if (root === document.body) translateDocumentTitle();
  }

  function translateDocumentTitle() {
    const titleElement = document.querySelector("title");
    if (!titleElement) return;
    translateNode(titleElement.firstChild || document.createTextNode(""));
  }

  function updateButtons() {
    document.querySelectorAll("[data-language]").forEach(button => {
      button.textContent = currentLanguage === "en" ? "UA" : "EN";
      button.setAttribute("aria-label", currentLanguage === "en" ? "Перемкнути на українську" : "Switch to English");
    });
  }

  function showNote() {
    let note = document.querySelector(".translation-status");
    if (!note) {
      note = document.createElement("div");
      note.className = "translation-status";
      note.setAttribute("role", "status");
      note.setAttribute("aria-live", "polite");
      document.body.appendChild(note);
    }
    note.textContent = currentLanguage === "en"
      ? "The English version includes translated interface text. Some lesson explanations are still in Ukrainian."
      : "Англійська версія містить переклади інтерфейсу. Частина пояснень уроків поки українською.";
    note.hidden = false;
    window.clearTimeout(note._hideTimer);
    note._hideTimer = window.setTimeout(() => { note.hidden = true; }, 5000);
  }

  function setLanguage(language, showStatus = true) {
    currentLanguage = language === "en" ? "en" : "uk";
    document.documentElement.lang = currentLanguage;
    try { localStorage.setItem("rozumnyk-ui-language", currentLanguage); } catch (_) {}
    updateButtons();
    scan();
    if (currentLanguage === "en" && showStatus) showNote();
  }

  document.querySelectorAll("[data-language]").forEach(button => {
    button.addEventListener("click", () => setLanguage(currentLanguage === "en" ? "uk" : "en"));
  });

  const saved = (() => { try { return localStorage.getItem("rozumnyk-ui-language"); } catch (_) { return null; } })();
  try { localStorage.removeItem("rozumnyk-english-translation-cache-v1"); } catch (_) {}
  setLanguage(saved === "en" ? "en" : "uk", saved === "en");

  observer = new MutationObserver(changes => {
    for (const change of changes) {
      if (change.type === "characterData") translateNode(change.target);
      else if (change.type === "attributes") translateAttributes(change.target);
      else change.addedNodes.forEach(added => {
        if (added.nodeType === Node.TEXT_NODE) translateNode(added);
        else if (added.nodeType === Node.ELEMENT_NODE) scan(added);
      });
    }
  });
  observer.observe(document.body, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: attributeNames });
})();
