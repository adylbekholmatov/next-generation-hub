"""Демо-данные: python manage.py seed

Удаляет прежние демо-данные (курсы, группы, уроки, журнал, новости, заявки,
демо-пользователей) и создаёт их заново. Настоящие пользователи, созданные
вручную, не затрагиваются.
"""
import datetime
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from core.models import Attendance, Course, EnrollmentRequest, Group, Lesson, News

PASSWORDS = {
    "admin": "admin12345",
    "manager": "manager12345",
    "teacher": "teacher12345",
    "student": "student12345",
}

COURSES = [
    {
        "slug": "robotics-arduino",
        "direction": "robotics",
        "level": "beginner",
        "age": (9, 14),
        "months": 8,
        "price": 4500,
        "order": 1,
        "title": {
            "ru": "Робототехника на Arduino",
            "ky": "Arduino менен робототехника",
            "en": "Robotics with Arduino",
        },
        "short": {
            "ru": "Собираем и программируем роботов: от мигающего светодиода до машинки, которая объезжает препятствия.",
            "ky": "Роботторду чогултуп, программалайбыз: жымылдаган светодиоддон тартып тоскоолдуктарды айланып өткөн машинага чейин.",
            "en": "We build and program robots: from a blinking LED to a car that drives around obstacles.",
        },
        "description": {
            "ru": "Курс для тех, кто хочет понять, как устроены умные устройства. Ученики знакомятся с электроникой, собирают схемы на макетной плате и пишут программы для Arduino на C++.\n\nЧто изучаем: основы электричества и безопасная работа с компонентами; датчики расстояния, света и температуры; сервоприводы и моторы; управление по Bluetooth.\n\nИтоговый проект — собственный робот, которого ученик собирает, программирует и забирает домой.",
            "ky": "Акылдуу түзмөктөр кантип иштээрин түшүнгүсү келгендер үчүн курс. Окуучулар электроника менен таанышып, макет тактасында схемаларды чогултушат жана Arduino үчүн C++ тилинде программа жазышат.\n\nЭмнени үйрөнөбүз: электрдин негиздери жана компоненттер менен коопсуз иштөө; аралык, жарык жана температура датчиктери; сервоприводдор жана моторлор; Bluetooth аркылуу башкаруу.\n\nЖыйынтыктоочу долбоор — окуучу өзү чогултуп, программалап, үйүнө алып кете турган робот.",
            "en": "A course for those who want to understand how smart devices work. Students get to know electronics, assemble circuits on a breadboard and write programs for Arduino in C++.\n\nWhat we study: electricity basics and safe work with components; distance, light and temperature sensors; servos and motors; Bluetooth control.\n\nThe final project is the student's own robot, assembled, programmed and taken home.",
        },
    },
    {
        "slug": "frontend-html-css-js",
        "direction": "frontend",
        "level": "beginner",
        "age": (12, 17),
        "months": 9,
        "price": 5500,
        "order": 2,
        "title": {
            "ru": "Frontend: сайты на HTML, CSS и JavaScript",
            "ky": "Frontend: HTML, CSS жана JavaScript менен сайттар",
            "en": "Frontend: websites with HTML, CSS and JavaScript",
        },
        "short": {
            "ru": "Создаём адаптивные сайты и интерактивные интерфейсы — от первой страницы до портфолио на GitHub.",
            "ky": "Адаптивдүү сайттарды жана интерактивдүү интерфейстерди түзөбүз — биринчи барактан GitHub'дагы портфолиого чейин.",
            "en": "We create responsive websites and interactive interfaces — from the first page to a portfolio on GitHub.",
        },
        "description": {
            "ru": "Ученики проходят путь frontend-разработчика: верстают страницы на HTML и CSS, делают их удобными для телефонов и оживляют с помощью JavaScript.\n\nЧто изучаем: семантическая вёрстка, Flexbox и Grid, работа с макетом в Figma, основы JavaScript, DOM и события, работа с API, Git и GitHub.\n\nИтоговый проект — личный сайт-портфолио и небольшое веб-приложение, опубликованные в интернете.",
            "ky": "Окуучулар frontend-иштеп чыгуучунун жолун басып өтүшөт: HTML жана CSS менен барактарды түзүп, аларды телефонго ыңгайлаштырышат жана JavaScript менен жандандырышат.\n\nЭмнени үйрөнөбүз: семантикалык калып, Flexbox жана Grid, Figma'дагы макет менен иштөө, JavaScript негиздери, DOM жана окуялар, API менен иштөө, Git жана GitHub.\n\nЖыйынтыктоочу долбоор — интернетке жарыяланган жеке портфолио-сайт жана чакан веб-тиркеме.",
            "en": "Students walk the path of a frontend developer: they lay out pages with HTML and CSS, make them comfortable on phones and bring them to life with JavaScript.\n\nWhat we study: semantic markup, Flexbox and Grid, working with a Figma mockup, JavaScript basics, the DOM and events, working with APIs, Git and GitHub.\n\nThe final project is a personal portfolio website and a small web application published online.",
        },
    },
    {
        "slug": "backend-python-django",
        "direction": "backend",
        "level": "intermediate",
        "age": (13, 17),
        "months": 9,
        "price": 6000,
        "order": 3,
        "title": {
            "ru": "Backend на Python и Django",
            "ky": "Python жана Django менен Backend",
            "en": "Backend with Python and Django",
        },
        "short": {
            "ru": "Учимся программировать на Python и создаём серверную часть веб-сервисов с базами данных и API.",
            "ky": "Python тилинде программалоону үйрөнүп, маалымат базасы жана API менен веб-кызматтардын сервердик бөлүгүн түзөбүз.",
            "en": "We learn to program in Python and build the server side of web services with databases and APIs.",
        },
        "description": {
            "ru": "Курс для подростков, которые хотят понять, что происходит «под капотом» сайтов и приложений. Начинаем с основ Python и алгоритмического мышления, затем переходим к веб-разработке на Django.\n\nЧто изучаем: переменные, циклы, функции и ООП; работа с файлами и библиотеками; базы данных и SQL; Django — модели, представления, шаблоны, авторизация; REST API и размещение на сервере.\n\nИтоговый проект — собственный веб-сервис: блог, магазин или Telegram-бот с админ-панелью.",
            "ky": "Сайттардын жана тиркемелердин «капотунун астында» эмне болуп жатканын түшүнгүсү келген өспүрүмдөр үчүн курс. Python негиздеринен жана алгоритмдик ой жүгүртүүдөн баштап, андан кийин Django менен веб-иштеп чыгууга өтөбүз.\n\nЭмнени үйрөнөбүз: өзгөрмөлөр, циклдер, функциялар жана ООП; файлдар жана китепканалар менен иштөө; маалымат базасы жана SQL; Django — моделдер, көрүнүштөр, шаблондор, авторизация; REST API жана серверге жайгаштыруу.\n\nЖыйынтыктоочу долбоор — окуучунун өз веб-кызматы: блог, дүкөн же админ-панели бар Telegram-бот.",
            "en": "A course for teens who want to understand what happens under the hood of websites and apps. We start with Python basics and algorithmic thinking, then move on to web development with Django.\n\nWhat we study: variables, loops, functions and OOP; working with files and libraries; databases and SQL; Django — models, views, templates, authentication; REST APIs and deployment to a server.\n\nThe final project is the student's own web service: a blog, a shop or a Telegram bot with an admin panel.",
        },
    },
    {
        "slug": "fusion-360",
        "direction": "fusion360",
        "level": "beginner",
        "age": (11, 17),
        "months": 6,
        "price": 5000,
        "order": 4,
        "title": {
            "ru": "3D-моделирование в Fusion 360",
            "ky": "Fusion 360 программасында 3D-моделдөө",
            "en": "3D modeling in Fusion 360",
        },
        "short": {
            "ru": "Инженерное проектирование: создаём детали, сборки и чертежи и печатаем их на 3D-принтере.",
            "ky": "Инженердик долбоорлоо: тетиктерди, жыйнактарды жана чиймелерди түзүп, аларды 3D-принтерде басып чыгарабыз.",
            "en": "Engineering design: we create parts, assemblies and drawings and print them on a 3D printer.",
        },
        "description": {
            "ru": "Fusion 360 — профессиональная программа, в которой работают инженеры и конструкторы по всему миру. На курсе ученики учатся превращать идею в точную 3D-модель и настоящий физический предмет.\n\nЧто изучаем: эскизы и размеры, твердотельное моделирование, сборки и подвижные соединения, рендеринг, подготовка модели к 3D-печати и работа со слайсером.\n\nИтоговый проект — собственное изделие, спроектированное и напечатанное на 3D-принтере: от держателя для телефона до детали для робота.",
            "ky": "Fusion 360 — дүйнө жүзүндөгү инженерлер жана конструкторлор иштеген профессионалдык программа. Курста окуучулар идеяны так 3D-моделге жана чыныгы буюмга айландырганды үйрөнүшөт.\n\nЭмнени үйрөнөбүз: эскиздер жана өлчөмдөр, катуу денелүү моделдөө, жыйнактар жана кыймылдуу бириктирүүлөр, рендеринг, моделди 3D-басууга даярдоо жана слайсер менен иштөө.\n\nЖыйынтыктоочу долбоор — окуучу өзү долбоорлоп, 3D-принтерде басып чыгарган буюм: телефон кармагычтан тартып роботтун тетигине чейин.",
            "en": "Fusion 360 is a professional program used by engineers and designers all over the world. In the course, students learn to turn an idea into an accurate 3D model and a real physical object.\n\nWhat we study: sketches and dimensions, solid modeling, assemblies and movable joints, rendering, preparing a model for 3D printing and working with a slicer.\n\nThe final project is the student's own product, designed and printed on a 3D printer: from a phone holder to a part for a robot.",
        },
    },
    {
        "slug": "blender-3d",
        "direction": "blender",
        "level": "beginner",
        "age": (10, 17),
        "months": 6,
        "price": 5000,
        "order": 5,
        "title": {
            "ru": "3D-графика и анимация в Blender",
            "ky": "Blender'де 3D-графика жана анимация",
            "en": "3D graphics and animation in Blender",
        },
        "short": {
            "ru": "Моделируем персонажей и окружение, настраиваем свет и материалы и создаём собственные анимации.",
            "ky": "Каармандарды жана чөйрөнү моделдеп, жарык менен материалдарды жөндөп, өз анимацияларыбызды жаратабыз.",
            "en": "We model characters and environments, set up light and materials and create our own animations.",
        },
        "description": {
            "ru": "Blender — бесплатный и мощный 3D-редактор, в котором создают игры, мультфильмы и визуальные эффекты. Курс подходит тем, кто любит рисовать и хочет попробовать себя в цифровом творчестве.\n\nЧто изучаем: интерфейс и навигация, полигональное моделирование, скульптинг, материалы и текстуры, освещение и камера, анимация и рендер в Eevee и Cycles.\n\nИтоговый проект — короткий анимационный ролик или игровая 3D-сцена для портфолио.",
            "ky": "Blender — оюндар, мультфильмдер жана визуалдык эффекттер жаралган акысыз жана күчтүү 3D-редактор. Курс сүрөт тартканды жакшы көргөн жана санариптик чыгармачылыкта күчүн сынап көргүсү келгендерге ылайыктуу.\n\nЭмнени үйрөнөбүз: интерфейс жана навигация, полигондук моделдөө, скульптинг, материалдар жана текстуралар, жарык жана камера, Eevee жана Cycles'те анимация жана рендер.\n\nЖыйынтыктоочу долбоор — портфолио үчүн кыска анимациялык ролик же оюндун 3D-сахнасы.",
            "en": "Blender is a free and powerful 3D editor used to make games, cartoons and visual effects. The course suits those who love drawing and want to try themselves in digital art.\n\nWhat we study: interface and navigation, polygonal modeling, sculpting, materials and textures, lighting and camera, animation and rendering in Eevee and Cycles.\n\nThe final project is a short animated clip or a game 3D scene for the portfolio.",
        },
    },
]

TEACHERS = [
    ("teacher1", "Азамат", "Токтогулов", "Инженер-робототехник, преподаватель Arduino и Fusion 360",
     "Восемь лет проектирует электронику и промышленную автоматику. Готовит команды к олимпиадам по робототехнике."),
    ("teacher2", "Айпери", "Садыкова", "Frontend-разработчик и 3D-художник",
     "Делает интерфейсы для веб-сервисов и визуализации в Blender. Учит видеть в коде и графике одно ремесло."),
    ("teacher3", "Бекзат", "Орозбеков", "Backend-разработчик на Python и Django",
     "Пишет серверную часть для финтеха и логистики. Любит объяснять сложное на простых примерах."),
]

STUDENTS = [
    ("Айбек", "Асанов"), ("Нурсултан", "Мамытов"), ("Алина", "Касымова"), ("Эмир", "Жолдошев"),
    ("Адина", "Бакирова"), ("Тимур", "Исаков"), ("Айжан", "Турдубаева"), ("Султан", "Абдраимов"),
    ("Бегимай", "Осмонова"), ("Эрлан", "Кадыров"), ("Мээрим", "Шаршеева"), ("Данияр", "Токтомушев"),
    ("Сезим", "Алымкулова"), ("Арсен", "Бообеков"), ("Нурай", "Эсенова"), ("Бакыт", "Мырзаев"),
    ("Аруужан", "Сатыбалдиева"), ("Эльдар", "Кенжебеков"), ("Камила", "Рысбекова"), ("Амир", "Уметалиев"),
]

# (название, slug курса, логин учителя, дни недели, начало, конец, кабинет, индексы студентов)
GROUPS = [
    ("ROBO-1", "robotics-arduino", "teacher1", "0,2", "15:00", "16:30", "101", [0, 1, 2, 3, 4, 5]),
    ("FRONT-1", "frontend-html-css-js", "teacher2", "1,3", "16:00", "17:30", "204", [6, 7, 8, 9, 10]),
    ("BACK-1", "backend-python-django", "teacher3", "0,2", "18:00", "19:30", "204", [11, 12, 13, 14, 7]),
    ("FUSION-1", "fusion-360", "teacher1", "1,4", "15:00", "16:30", "102", [15, 16, 17, 0]),
    ("BLENDER-1", "blender-3d", "teacher2", "3,5", "17:00", "18:30", "305", [18, 19, 2, 10, 16]),
]

LESSONS = {
    "robotics-arduino": [
        ("Знакомство с Arduino: плата, среда разработки и первая программа", "https://www.youtube.com/watch?v=fJWR7dBuc18",
         "Устанавливаем Arduino IDE, подключаем плату и заставляем светодиод мигать."),
        ("Полный вводный курс по Arduino", "https://www.youtube.com/watch?v=zJ-LqeX_fLU",
         "Цифровые и аналоговые входы, датчики и моторы — обзор всего, что пригодится в курсе."),
    ],
    "frontend-html-css-js": [
        ("HTML: структура страницы и основные теги", "https://www.youtube.com/watch?v=pQN-pnXPaVg",
         "Заголовки, абзацы, ссылки, изображения, списки и формы. Собираем первую страницу."),
        ("CSS: оформление, Flexbox и адаптивность", "https://www.youtube.com/watch?v=OXGznpKZ_sA",
         "Селекторы, блочная модель, цвета и шрифты, раскладка на Flexbox."),
        ("JavaScript: переменные, функции и события", "https://www.youtube.com/watch?v=PkZNo7MFNFg",
         "Основы языка и первые интерактивные элементы на странице."),
    ],
    "backend-python-django": [
        ("Python с нуля: переменные, условия и циклы", "https://www.youtube.com/watch?v=rfscVS0vtbw",
         "Устанавливаем Python и пишем первые программы."),
        ("Django: первый проект, модели и админка", "https://www.youtube.com/watch?v=F5mRW0jo-U4",
         "Создаём проект, описываем модели и знакомимся с административной панелью."),
    ],
    "fusion-360": [
        ("Интерфейс Fusion 360 и первый эскиз", "https://www.youtube.com/watch?v=A5bc9c3S12g",
         "Навигация, эскизы с размерами и выдавливание — первая деталь для печати."),
    ],
    "blender-3d": [
        ("Blender для начинающих: интерфейс и первые объекты", "https://www.youtube.com/watch?v=nIoXOplUvAw",
         "Навигация во вьюпорте, примитивы и модификаторы. Начинаем знаменитый «пончик»."),
        ("Blender 4: моделирование, материалы и рендер", "https://www.youtube.com/watch?v=B0J27sf9N1Y",
         "Доводим сцену до финального изображения: материалы, свет и камера."),
    ],
}

NEWS = [
    {
        "pinned": True,
        "days_ago": 2,
        "title": {
            "ru": "Открыт набор на осенний семестр",
            "ky": "Күзгү семестрге кабыл алуу башталды",
            "en": "Enrollment for the autumn semester is open",
        },
        "body": {
            "ru": "Мы открываем новые группы по всем пяти направлениям: робототехника, Frontend, Backend, Fusion 360 и Blender. Занятия проходят в группах до 10 человек.\n\nЗапишитесь на бесплатный пробный урок через форму на сайте — менеджер свяжется с вами и подберёт удобное время.",
            "ky": "Беш багыт боюнча тең жаңы топторду ачып жатабыз: робототехника, Frontend, Backend, Fusion 360 жана Blender. Сабактар 10 кишиге чейинки топтордо өтөт.\n\nСайттагы форма аркылуу акысыз сыноо сабагына жазылыңыз — менеджер сиз менен байланышып, ыңгайлуу убакытты тандап берет.",
            "en": "We are opening new groups in all five directions: robotics, Frontend, Backend, Fusion 360 and Blender. Classes are held in groups of up to 10 people.\n\nSign up for a free trial lesson using the form on the website — a manager will contact you and choose a convenient time.",
        },
    },
    {
        "pinned": False,
        "days_ago": 9,
        "title": {
            "ru": "Наши ученики — призёры республиканской олимпиады по робототехнике",
            "ky": "Окуучуларыбыз робототехника боюнча республикалык олимпиаданын байге ээлери болушту",
            "en": "Our students won prizes at the national robotics olympiad",
        },
        "body": {
            "ru": "Команда Next-Generation-Hub заняла второе место в категории «Автономные роботы». Ребята полностью сами собрали и запрограммировали робота, который проходит лабиринт за 40 секунд.\n\nПоздравляем участников и их наставника Азамата Токтогулова!",
            "ky": "Next-Generation-Hub командасы «Автономдуу роботтор» категориясында экинчи орунду ээледи. Балдар лабиринтти 40 секундда өтүүчү роботту толугу менен өздөрү чогултуп, программалашты.\n\nКатышуучуларды жана алардын насаатчысы Азамат Токтогуловду куттуктайбыз!",
            "en": "The Next-Generation-Hub team took second place in the “Autonomous robots” category. The kids assembled and programmed a robot that completes the maze in 40 seconds entirely on their own.\n\nCongratulations to the participants and their mentor Azamat Toktogulov!",
        },
    },
    {
        "pinned": False,
        "days_ago": 18,
        "title": {"ru": "Новая 3D-лаборатория", "ky": "Жаңы 3D-лаборатория", "en": "A new 3D laboratory"},
        "body": {
            "ru": "В центре появилась лаборатория с тремя 3D-принтерами и мощными компьютерами для рендера. Теперь ученики курсов Fusion 360 и Blender могут печатать свои модели прямо на занятиях.",
            "ky": "Борборубузда үч 3D-принтери жана рендер үчүн күчтүү компьютерлери бар лаборатория ачылды. Эми Fusion 360 жана Blender курстарынын окуучулары моделдерин сабак учурунда эле басып чыгара алышат.",
            "en": "The center now has a laboratory with three 3D printers and powerful computers for rendering. Students of the Fusion 360 and Blender courses can now print their models right during classes.",
        },
    },
    {
        "pinned": False,
        "days_ago": 27,
        "title": {"ru": "День открытых дверей", "ky": "Ачык эшиктер күнү", "en": "Open day"},
        "body": {
            "ru": "Приглашаем родителей и детей на день открытых дверей в субботу. Покажем лабораторию, проведём мастер-классы по каждому направлению и ответим на вопросы.\n\nВход свободный, но просим записаться заранее по телефону.",
            "ky": "Ата-энелерди жана балдарды ишемби күнү ачык эшиктер күнүнө чакырабыз. Лабораторияны көрсөтүп, ар бир багыт боюнча мастер-класс өткөрүп, суроолоруңуздарга жооп беребиз.\n\nКирүү акысыз, бирок алдын ала телефон аркылуу жазылууну суранабыз.",
            "en": "We invite parents and children to an open day on Saturday. We will show the laboratory, hold master classes in each direction and answer your questions.\n\nEntry is free, but please sign up in advance by phone.",
        },
    },
    {
        "pinned": False,
        "days_ago": 41,
        "title": {
            "ru": "Выпускники курса Frontend запустили свои сайты",
            "ky": "Frontend курсунун бүтүрүүчүлөрү өз сайттарын ишке киргизишти",
            "en": "Frontend graduates launched their websites",
        },
        "body": {
            "ru": "Девять учеников завершили курс Frontend и опубликовали личные сайты-портфолио. Среди проектов — сайт школьной футбольной команды, онлайн-меню для кафе и игра на JavaScript.",
            "ky": "Тогуз окуучу Frontend курсун аяктап, жеке портфолио-сайттарын жарыялашты. Долбоорлордун арасында мектептин футбол командасынын сайты, кафе үчүн онлайн-меню жана JavaScript'те жазылган оюн бар.",
            "en": "Nine students completed the Frontend course and published their personal portfolio websites. Among the projects are a website for a school football team, an online menu for a cafe and a JavaScript game.",
        },
    },
]

REQUESTS = [
    ("Гульнара Асанбекова", "+996 700 112 233", "gulnara@mail.kg", 11, "robotics-arduino", "new", 0,
     "Сын очень любит конструкторы, хотим попробовать робототехнику."),
    ("Руслан Жээнбеков", "+996 555 908 070", "", 14, "backend-python-django", "new", 1,
     "Есть ли группы по выходным?"),
    ("Айгерим Токтосунова", "+996 777 450 120", "aigerim.t@gmail.com", 12, "blender-3d", "new", 3, ""),
    ("Максат Бейшеналиев", "+996 502 334 455", "", 13, "", "contacted", 6,
     "Не можем выбрать между Frontend и Blender, нужна консультация."),
    ("Жанара Мукашева", "+996 709 876 543", "zhanara@inbox.ru", 10, "robotics-arduino", "contacted", 10, ""),
    ("Талант Сыдыков", "+996 555 121 314", "", 15, "frontend-html-css-js", "enrolled", 16, "Записались в FRONT-1."),
    ("Элина Абдыкалыкова", "+996 700 909 808", "elina.a@mail.ru", 16, "fusion-360", "rejected", 24,
     "Не подошло время занятий."),
    ("Нурбек Качкынбаев", "+996 772 001 002", "", 9, "robotics-arduino", "new", 45, ""),
]


class Command(BaseCommand):
    help = "Заполняет базу демо-данными (курсы, пользователи, группы, уроки, журнал, новости, заявки)."

    def handle(self, *args, **options):
        random.seed(2026)
        with transaction.atomic():
            self._reset()
            users = self._users()
            courses = self._courses(users)
            groups = self._groups(users, courses)
            self._lessons(users, courses, groups)
            self._attendance(groups)
            self._news(users)
            self._requests(courses, users)
        self._print_accounts()

    # ------------------------------------------------------------------
    def _reset(self):
        Attendance.objects.all().delete()
        Lesson.objects.all().delete()
        EnrollmentRequest.objects.all().delete()
        Group.objects.all().delete()
        News.objects.all().delete()
        Course.objects.all().delete()
        demo = ["admin", "manager"] + [t[0] for t in TEACHERS] + [f"student{i}" for i in range(1, len(STUDENTS) + 1)]
        User.objects.filter(username__in=demo).delete()

    def _make_user(self, username, password, role, first, last, **extra):
        user = User(username=username, role=role, first_name=first, last_name=last, **extra)
        user.set_password(password)
        user.save()
        return user

    def _users(self):
        users = {}
        users["admin"] = self._make_user(
            "admin", PASSWORDS["admin"], User.Role.ADMIN, "Адилет", "Жумабаев",
            is_staff=True, is_superuser=True, email="admin@nextgenhub.kg", phone="+996 555 000 001",
            specialization="Администратор учебного центра",
        )
        users["manager"] = self._make_user(
            "manager", PASSWORDS["manager"], User.Role.MANAGER, "Нургуль", "Абдыкадырова",
            email="manager@nextgenhub.kg", phone="+996 555 000 002", specialization="Менеджер по работе с клиентами",
        )
        for username, first, last, spec, about in TEACHERS:
            users[username] = self._make_user(
                username, PASSWORDS["teacher"], User.Role.TEACHER, first, last,
                specialization=spec, about=about, email=f"{username}@nextgenhub.kg",
                phone=f"+996 555 10{username[-1]} 0{username[-1]}0",
            )
        users["students"] = []
        for i, (first, last) in enumerate(STUDENTS, start=1):
            users["students"].append(
                self._make_user(
                    f"student{i}", PASSWORDS["student"], User.Role.STUDENT, first, last,
                    phone=f"+996 700 {100 + i:03d} {200 + i * 7:03d}",
                )
            )
        return users

    def _courses(self, users):
        teacher_map = {
            "robotics-arduino": ["teacher1"],
            "frontend-html-css-js": ["teacher2"],
            "backend-python-django": ["teacher3"],
            "fusion-360": ["teacher1"],
            "blender-3d": ["teacher2"],
        }
        courses = {}
        for data in COURSES:
            course = Course.objects.create(
                slug=data["slug"],
                direction=data["direction"],
                level=data["level"],
                age_from=data["age"][0],
                age_to=data["age"][1],
                duration_months=data["months"],
                lessons_per_week=2,
                price=data["price"],
                order=data["order"],
                **{f"{field}_{lang}": data[field][lang] for field in ("title", "short", "description") for lang in ("ru", "ky", "en")},
            )
            course.teachers.set([users[t] for t in teacher_map[data["slug"]]])
            courses[data["slug"]] = course
        return courses

    def _groups(self, users, courses):
        start = timezone.localdate() - datetime.timedelta(days=75)
        groups = []
        for name, slug, teacher, days, t1, t2, room, student_idx in GROUPS:
            group = Group.objects.create(
                name=name,
                course=courses[slug],
                teacher=users[teacher],
                weekdays=days,
                start_time=datetime.time.fromisoformat(t1),
                end_time=datetime.time.fromisoformat(t2),
                room=room,
                start_date=start,
            )
            group.students.set([users["students"][i] for i in student_idx])
            groups.append(group)
        return groups

    def _lessons(self, users, courses, groups):
        by_course = {g.course.slug: g for g in groups}
        for slug, items in LESSONS.items():
            group = by_course.get(slug)
            for number, (title, url, description) in enumerate(items, start=1):
                lesson = Lesson.objects.create(
                    course=courses[slug],
                    group=None if number == 1 else group,
                    teacher=group.teacher,
                    number=number,
                    title=title,
                    description=description,
                    youtube_url=url,
                )
                Lesson.objects.filter(pk=lesson.pk).update(
                    created_at=timezone.now() - datetime.timedelta(days=30 - number * 7)
                )

    def _attendance(self, groups):
        today = timezone.localdate()
        first = today - datetime.timedelta(days=35)
        statuses = ["present"] * 78 + ["late"] * 10 + ["absent"] * 8 + ["excused"] * 4
        records = []
        for group in groups:
            for day in group.lesson_dates_in_range(first, today - datetime.timedelta(days=1)):
                for student in group.students.all():
                    status = random.choice(statuses)
                    grade = None
                    if status in ("present", "late") and random.random() < 0.6:
                        grade = random.choice([3, 4, 4, 5, 5, 5])
                    comment = ""
                    if status == "excused":
                        comment = "Болел, есть справка"
                    elif status == "late":
                        comment = random.choice(["", "", "Опоздал на 10 минут"])
                    records.append(
                        Attendance(group=group, student=student, date=day, status=status, grade=grade,
                                   comment=comment, marked_by=group.teacher)
                    )
        Attendance.objects.bulk_create(records)

    def _news(self, users):
        for item in NEWS:
            News.objects.create(
                is_pinned=item["pinned"],
                published_at=timezone.now() - datetime.timedelta(days=item["days_ago"], hours=3),
                author=users["manager"],
                **{f"{field}_{lang}": item[field][lang] for field in ("title", "body") for lang in ("ru", "ky", "en")},
            )

    def _requests(self, courses, users):
        for name, phone, email, age, slug, status, days_ago, message in REQUESTS:
            req = EnrollmentRequest.objects.create(
                name=name, phone=phone, email=email, age=age, course=courses.get(slug), message=message,
                status=status, handled_by=None if status == "new" else users["manager"],
                manager_note="" if status == "new" else "Позвонили, рассказали о курсе.",
            )
            EnrollmentRequest.objects.filter(pk=req.pk).update(
                created_at=timezone.now() - datetime.timedelta(days=days_ago, hours=random.randint(1, 9))
            )

    def _print_accounts(self):
        line = "─" * 52
        self.stdout.write(self.style.SUCCESS("\nДемо-данные созданы."))
        self.stdout.write(line)
        self.stdout.write(f"{'Роль':<14}{'Логин':<22}Пароль")
        self.stdout.write(line)
        rows = [
            ("Админ", "admin", PASSWORDS["admin"]),
            ("Менеджер", "manager", PASSWORDS["manager"]),
            ("Учитель", "teacher1..teacher3", PASSWORDS["teacher"]),
            ("Студент", "student1..student20", PASSWORDS["student"]),
        ]
        for role, login, password in rows:
            self.stdout.write(f"{role:<14}{login:<22}{password}")
        self.stdout.write(line)
        self.stdout.write("Вход: http://127.0.0.1:8000/accounts/login/\n")
