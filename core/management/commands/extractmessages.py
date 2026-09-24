"""python manage.py extractmessages — обновление .po без GNU gettext.

Собирает строки из шаблонов ({% trans %}, {% blocktrans %}, _("...")) и Python-кода
(gettext / gettext_lazy / pgettext / ngettext), затем обновляет
locale/<lang>/LC_MESSAGES/django.po для всех языков из LANGUAGES.
Уже сделанные переводы сохраняются, новые строки добавляются с пустым msgstr
(для английского msgstr = msgid). После перевода выполните `compilemo`.
"""
import ast
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation.template import templatize

from .compilemo import parse_po

FUNCS = {
    "_": "s", "gettext": "s", "gettext_lazy": "s", "gettext_noop": "s",
    "pgettext": "p", "pgettext_lazy": "p", "ngettext": "n", "ngettext_lazy": "n",
}
STR = r"u?'(?:[^'\\]|\\.)*'|u?\"(?:[^\"\\]|\\.)*\""
CALL = re.compile(r"\b(gettext|ngettext|pgettext|npgettext)\(((?:\s*(?:%s)\s*,?)+)" % STR)
SKIP_DIRS = {"venv", ".venv", ".git", "migrations", "media", "staticfiles", "static", "locale", "node_modules", "__pycache__"}
PLURAL_FORMS = {
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
}


def _quote(text):
    return '"%s"' % text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Command(BaseCommand):
    help = "Извлекает строки для перевода и обновляет .po файлы (без утилит gettext)."

    def handle(self, *args, **options):
        self.entries = {}
        base = Path(settings.BASE_DIR)
        for path in sorted(base.rglob("*")):
            if any(part in SKIP_DIRS for part in path.relative_to(base).parts) or not path.is_file():
                continue
            rel = path.relative_to(base).as_posix()
            if path.suffix == ".py":
                self._scan_python(path, rel)
            elif path.suffix in (".html", ".txt"):
                self._scan_template(path, rel)

        locale_dir = Path(settings.LOCALE_PATHS[0])
        for lang, _name in settings.LANGUAGES:
            po_path = locale_dir / lang / "LC_MESSAGES" / "django.po"
            old = parse_po(po_path) if po_path.exists() else {}
            po_path.parent.mkdir(parents=True, exist_ok=True)
            po_path.write_text(self._render(lang, old), encoding="utf-8", newline="\n")
            empty = sum(1 for key in self._keys() if not old.get(key) and lang != "en")
            self.stdout.write(f"{po_path.relative_to(base)}: {len(self.entries)} messages, untranslated: {empty}")

    # --- сбор строк ------------------------------------------------------
    def _add(self, ctx, msgid, plural, ref):
        entry = self.entries.setdefault((ctx, msgid), {"plural": plural, "refs": set()})
        entry["plural"] = entry["plural"] or plural
        entry["refs"].add(ref)

    def _scan_python(self, path, rel):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            return
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            kind = FUNCS.get(name)
            args = [a.value if isinstance(a, ast.Constant) and isinstance(a.value, str) else None for a in node.args]
            if kind == "s" and args and args[0]:
                self._add("", args[0], None, rel)
            elif kind == "p" and len(args) > 1 and args[0] and args[1]:
                self._add(args[0], args[1], None, rel)
            elif kind == "n" and len(args) > 1 and args[0] and args[1]:
                self._add("", args[0], args[1], rel)

    def _scan_template(self, path, rel):
        source = templatize(path.read_text(encoding="utf-8"))
        for match in CALL.finditer(source):
            strings = [ast.literal_eval(s.lstrip("u")) for s in re.findall(STR, match.group(2))]
            fn = match.group(1)
            if fn == "gettext":
                self._add("", strings[0], None, rel)
            elif fn == "ngettext":
                self._add("", strings[0], strings[1], rel)
            elif fn == "pgettext":
                self._add(strings[0], strings[1], None, rel)
            elif fn == "npgettext":
                self._add(strings[0], strings[1], strings[2], rel)

    # --- запись .po ------------------------------------------------------
    def _keys(self):
        for (ctx, msgid), entry in self.entries.items():
            key = (ctx + "\x04" if ctx else "") + msgid
            yield key + ("\x00" + entry["plural"] if entry["plural"] else "")

    def _render(self, lang, old):
        plural_forms = PLURAL_FORMS.get(lang, "nplurals=2; plural=(n != 1);")
        nplurals = int(plural_forms.split(";")[0].split("=")[1])
        lines = [
            "# Next-Generation-Hub translations.",
            "# После правок выполните: python manage.py compilemo",
            'msgid ""', 'msgstr ""',
            _quote("Project-Id-Version: Next-Generation-Hub 1.0\n"), _quote(f"Language: {lang}\n"),
            _quote("MIME-Version: 1.0\n"), _quote("Content-Type: text/plain; charset=UTF-8\n"),
            _quote("Content-Transfer-Encoding: 8bit\n"), _quote(f"Plural-Forms: {plural_forms}\n"), "",
        ]
        items = sorted(self.entries.items(), key=lambda kv: (sorted(kv[1]["refs"])[0], kv[0][1]))
        for (ctx, msgid), entry in items:
            plural = entry["plural"]
            key = (ctx + "\x04" if ctx else "") + msgid + ("\x00" + plural if plural else "")
            lines.append("#: " + " ".join(sorted(entry["refs"])[:4]))
            if "%(" in msgid or "%%" in msgid:
                lines.append("#, python-format")
            if ctx:
                lines.append("msgctxt " + _quote(ctx))
            lines.append("msgid " + _quote(msgid))
            if plural:
                lines.append("msgid_plural " + _quote(plural))
                forms = old.get(key, "").split("\x00") if old.get(key) else []
                if not forms and lang == "en":
                    forms = [msgid, plural]
                forms = (forms + [""] * nplurals)[:nplurals]
                lines += [f"msgstr[{i}] {_quote(f)}" for i, f in enumerate(forms)]
            else:
                value = old.get(key) or (msgid if lang == "en" else "")
                lines.append("msgstr " + _quote(value))
            lines.append("")
        return "\n".join(lines)
