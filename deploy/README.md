`demo.sqlite3` — готовая демо-база для Vercel (копируется в /tmp при старте функции).

Пересоздать (например, чтобы обновить даты журнала посещаемости):

```bash
rm deploy/demo.sqlite3
SQLITE_PATH=deploy/demo.sqlite3 python manage.py migrate
SQLITE_PATH=deploy/demo.sqlite3 python manage.py seed
```
