# Next-Generation-Hub

Сайт учебного центра **Next-Generation-Hub** (Ош): публичный сайт с курсами и новостями, приём заявок,
и кабинеты для администратора, менеджера, учителя и студента: видеоуроки, журнал посещаемости, группы и заявки.

Направления: **Робототехника**, **Frontend**, **Backend**, **Fusion 360**, **Blender**.

- Django 5.2, Python 3.11+, SQLite (разработка) / PostgreSQL (продакшен)
- Шаблоны Django + свой CSS и немного чистого JS. Сборка фронтенда не нужна.
- Три языка интерфейса: кыргызский, русский (по умолчанию), английский
- Голубо-белая светлая тема (по умолчанию) и тёмно-синяя тёмная, адаптив от 360 px

---

## Быстрый старт

### Windows (PowerShell)

```powershell
cd next-generation-hub
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # по желанию
python manage.py migrate
python manage.py seed           # демо-данные + логины в консоли
python manage.py createsuperuser  # по желанию, свой админ
python manage.py runserver
```

### Linux / macOS

```bash
cd next-generation-hub
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed
python manage.py createsuperuser
python manage.py runserver
```

Откройте http://127.0.0.1:8000/. Вход: http://127.0.0.1:8000/accounts/login/

> Скомпилированные переводы (`.mo`) лежат в репозитории, поэтому GNU gettext устанавливать не нужно.

---

## Роли и демо-аккаунты

Команда `python manage.py seed` пересоздаёт демо-данные (курсы, группы, уроки, журнал за последний месяц,
новости, заявки) и печатает логины. Пользователей, созданных вручную, она не трогает.

| Роль | Логин | Пароль | Что доступно |
|---|---|---|---|
| Администратор | `admin` | `admin12345` | Всё: дашборд со статистикой и графиками, пользователи и роли, курсы, а также все кабинеты менеджера и учителя, ссылка на `/django-admin/` |
| Менеджер | `manager` | `manager12345` | Заявки (статусы, заметки, «Создать студента из заявки»), студенты, группы, новости на 3 языках, просмотр журналов (только чтение) |
| Учитель | `teacher1` … `teacher3` | `teacher12345` | Свои группы, ближайшие занятия, видеоуроки (загрузка с прогрессом или YouTube), отметка посещаемости, журнал за месяц, экспорт в CSV/Excel |
| Студент | `student1` … `student20` | `student12345` | Свои группы и расписание, видеоуроки своих курсов, посещаемость и оценки |

`/cabinet/` перенаправляет в кабинет по роли. Чужой кабинет отдаёт **403**. Учитель видит и редактирует
только свои группы и уроки. Суперпользователь, созданный через `createsuperuser`, автоматически получает роль администратора.
Во всех кабинетах есть профиль и смена пароля.

---

## Как пользоваться сайтом

**Посетитель сайта.** Смотрит курсы (фильтр по направлениям), новости, контакты. Оставляет заявку
на бесплатный пробный урок через форму на главной, на странице курса или в «Контактах».
Язык (KY / RU / EN) и тема (светлая / тёмная) переключаются в шапке.

**Администратор** (`admin`). После входа открывается дашборд со статистикой.
- *Пользователи*: создать аккаунт с любой ролью, изменить роль, сбросить пароль (новый пароль показывается один раз), заблокировать или разблокировать.
- *Курсы*: добавить или изменить курс. Тексты заполняются на трёх языках во вкладках RU / KY / EN, русский обязателен.
- Администратору доступно всё, что умеют менеджер и учитель. Резервный вариант — `/django-admin/`.

**Менеджер** (`manager`).
- *Заявки*: новые заявки с сайта. Статус меняется прямо в списке (Новая → Связались → Записан / Отказ). На странице заявки есть заметка и кнопка **«Создать студента из заявки»**: логин подставится сам, а пароль, если оставить поле пустым, сгенерируется и покажется на экране — передайте его студенту.
- *Студенты*: поиск, создание, редактирование, добавление в группы.
- *Группы*: курс, учитель, дни и время занятий, кабинет, состав студентов.
- *Новости*: публикация на трёх языках, закрепление наверху.
- *Журналы посещаемости*: только просмотр.

**Учитель** (`teacher1` … `teacher3`).
- *Обзор*: свои группы, ближайшие занятия, статистика посещаемости.
- *Видеоуроки*: «Загрузить урок» → курс, группа (пусто — для всех групп курса), ссылка на YouTube **или** видеофайл, материалы.
- *Отметить занятие*: выбрать группу и дату → отметить каждого (Присутствовал / Опоздал / Отсутствовал / Уважительная причина), оценка 1–5 и комментарий → «Сохранить». Кнопка «Все присутствуют» ставит всем «Присутствовал».
- *Журнал за месяц*: таблица «студенты × даты» с процентами, переключение месяцев, выгрузка в CSV или Excel.

**Студент** (`student1` … `student20`). Свои группы и расписание, видеоуроки своих курсов, посещаемость и оценки.

Во всех кабинетах есть «Профиль» (имя, телефон, фото) и «Пароль» (смена своего пароля).

---

## Структура

```
config/      настройки, urls, wsgi/asgi
accounts/    User (роль, телефон, фото, специализация, «о себе»), вход, профиль, декоратор role_required
core/        Course, Group, Lesson, Attendance, News, EnrollmentRequest; публичные страницы;
             TranslatableMixin + фильтр {{ obj|tr:"title" }}; команды seed / extractmessages / compilemo
cabinet/     кабинеты: views/admin.py, manager.py, teacher.py, student.py, common.py; журнал и экспорт
templates/   шаблоны (base.html — сайт, cabinet/base.html — кабинеты)
static/      css/main.css (дизайн-система), js/main.js
locale/      ky / ru / en — .po и скомпилированные .mo
```

---

## Настройки (переменные окружения)

Все переменные можно задать в файле `.env` в корне проекта (см. `.env.example`) или в окружении.

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DJANGO_SECRET_KEY` | dev-ключ | Секретный ключ. **Обязательно** смените в продакшене |
| `DJANGO_DEBUG` | `True` | Режим отладки |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Домены через запятую |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | — | Например `https://nextgenhub.kg` |
| `MAX_VIDEO_UPLOAD_MB` | `500` | Лимит размера видеофайла урока |
| `DB_ENGINE` | `sqlite` | `postgres` — переключение на PostgreSQL |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | — | Параметры PostgreSQL |
| `SITE_PHONE`, `SITE_EMAIL`, `SITE_ADDRESS`, `SITE_HOURS`, `SITE_INSTAGRAM`, `SITE_TELEGRAM`, `SITE_WHATSAPP`, `SITE_MAP_URL` | демо | Контакты на сайте |

Часовой пояс: `Asia/Bishkek`.

### Переход на PostgreSQL

```bash
pip install "psycopg[binary]"
```

В `.env`:

```
DB_ENGINE=postgres
DB_NAME=nextgenhub
DB_USER=nextgenhub
DB_PASSWORD=strong-password
DB_HOST=localhost
DB_PORT=5432
```

Затем `python manage.py migrate` (и при желании `python manage.py seed`).

---

## Языки и переводы

- Языки: `ky` (Кыргызча), `ru` (Русский, по умолчанию), `en` (English). Переключатель KY / RU / EN в шапке, выбор хранится в cookie `ngh_language`.
- Строки интерфейса — через `{% trans %}` / `{% blocktrans %}` / `gettext`. Исходные строки на английском, переводы в `locale/<lang>/LC_MESSAGES/django.po`.
- Контент (курсы, новости) хранится в полях `_ru`, `_ky`, `_en`. В шаблоне: `{{ course|tr:"title" }}`. Если перевода нет, показывается русский вариант. В формах редактирования языки разнесены по вкладкам.

**Как добавить или изменить перевод**

1. Добавьте строку в шаблон (`{% trans "New text" %}`) или в код (`_("New text")`).
2. Обновите каталоги:
   - без gettext (любая ОС): `python manage.py extractmessages`
   - или стандартно, если установлен GNU gettext: `django-admin makemessages -l ky -l ru -l en`
3. Переведите новые `msgstr` в `locale/ky/…/django.po` и `locale/ru/…/django.po` (в `en` заполнятся автоматически).
4. Скомпилируйте: `python manage.py compilemo` (без gettext) или `python manage.py compilemessages`.
5. Перезапустите сервер и закоммитьте `.po` и `.mo`.

Чтобы добавить новый язык, допишите его в `LANGUAGES` в `config/settings.py` и повторите шаги 2–4.

---

## Видео и медиа

- Урок = видеофайл (`mp4`, `webm`, `mov`, до `MAX_VIDEO_UPLOAD_MB`) **или** ссылка на YouTube (embed строится автоматически через youtube-nocookie).
- Загрузка идёт через XHR с прогресс-баром, а без JS работает обычная отправка формы.
- В режиме `DEBUG` медиа отдаёт Django. В продакшене — nginx (см. ниже).

---

## Тесты

```bash
python manage.py test
```

Покрыто: доступ по ролям (403 для чужих кабинетов, владелец групп и уроков), сохранение и обновление журнала,
экспорт CSV/Excel, загрузка урока (файл, AJAX, неверный формат и размер, YouTube), заявки с сайта (валидация, ловушка для ботов),
переключение языка и fallback переводов контента, создание студента из заявки.

---

## Демо на Vercel

Проект можно открыть как демо на Vercel (serverless). Всё нужное уже в репозитории: `vercel.json`,
точка входа `api/index.py`, статика через WhiteNoise, готовая демо-база `deploy/demo.sqlite3`.

1. https://vercel.com/new → **Import** репозитория `next-generation-hub`. Framework Preset: **Other**, остальное не менять.
2. В **Environment Variables** добавьте `DJANGO_SECRET_KEY` — длинную случайную строку, например из
   `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`.
   Без этого ключа сайт на Vercel намеренно не запускается: репозиторий публичный, а сессии хранятся в подписанных cookie.
3. **Deploy**. Дальше каждый `git push` в `main` будет пересобирать сайт автоматически.

Ограничения демо-режима (включается сам по переменной `VERCEL`):
- база копируется в `/tmp` при старте функции, поэтому изменения (заявки, отметки, новые пользователи) **временные** и сбрасываются;
- загрузка видеофайлов до 4 МБ (лимит Vercel на тело запроса), загруженные файлы тоже временные. Ссылки на YouTube работают без ограничений;
- демо-логины показываются на странице входа (`SHOW_DEMO_ACCOUNTS=False` — скрыть).

Чтобы данные сохранялись, нужен внешний PostgreSQL (например Neon) и хранилище для медиа, или VPS по инструкции ниже.
Даты журнала в демо-базе отсчитываются от дня её создания. Как её пересоздать — в `deploy/README.md`.

---

## Развёртывание на VPS (Ubuntu + gunicorn + nginx + PostgreSQL)

```bash
sudo apt update && sudo apt install -y python3-venv python3-dev nginx postgresql
sudo -u postgres psql -c "CREATE USER nextgenhub WITH PASSWORD 'strong-password';"
sudo -u postgres psql -c "CREATE DATABASE nextgenhub OWNER nextgenhub;"

sudo mkdir -p /srv/nextgenhub && sudo chown $USER /srv/nextgenhub
git clone <repo> /srv/nextgenhub/app && cd /srv/nextgenhub/app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt gunicorn "psycopg[binary]"
cp .env.example .env   # DJANGO_DEBUG=False, DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DB_ENGINE=postgres, DB_*
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

`/etc/systemd/system/nextgenhub.service`:

```ini
[Unit]
Description=Next-Generation-Hub (gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/nextgenhub/app
EnvironmentFile=/srv/nextgenhub/app/.env
ExecStart=/srv/nextgenhub/app/venv/bin/gunicorn config.wsgi:application \
          --workers 3 --timeout 300 --bind unix:/run/nextgenhub.sock
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo chown -R www-data:www-data /srv/nextgenhub/app/media
sudo systemctl daemon-reload && sudo systemctl enable --now nextgenhub
```

`/etc/nginx/sites-available/nextgenhub`:

```nginx
server {
    listen 80;
    server_name nextgenhub.kg www.nextgenhub.kg;

    # Лимит должен быть не меньше MAX_VIDEO_UPLOAD_MB
    client_max_body_size 600m;
    client_body_timeout 300s;

    location /static/ {
        alias /srv/nextgenhub/app/staticfiles/;
        expires 30d;
        access_log off;
    }

    location /media/ {
        alias /srv/nextgenhub/app/media/;
        # Отдача видео с поддержкой перемотки (Range-запросы nginx обрабатывает сам)
        add_header Accept-Ranges bytes;
        expires 7d;
    }

    location / {
        proxy_pass http://unix:/run/nextgenhub.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_request_buffering off;   # большие видео не буферизуются целиком
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/nextgenhub /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo apt install -y certbot python3-certbot-nginx && sudo certbot --nginx -d nextgenhub.kg -d www.nextgenhub.kg
```

После HTTPS добавьте в `.env` строку `DJANGO_CSRF_TRUSTED_ORIGINS=https://nextgenhub.kg` и перезапустите сервис.

---

## Админка Django

Стандартная админка доступна по адресу `/django-admin/` (все модели зарегистрированы) как запасной вариант.
Основная работа идёт в кабинетах: `/cabinet/`.
