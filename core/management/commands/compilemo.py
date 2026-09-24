"""python manage.py compilemo — компиляция .po → .mo без GNU gettext.

Стандартная `compilemessages` требует утилиту msgfmt, которой обычно нет на
Windows. Эта команда делает то же самое на чистом Python для каталогов проекта
(LOCALE_PATHS). Нечёткие (#, fuzzy) и пустые переводы пропускаются.
"""
import ast
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


def _unquote(line):
    return ast.literal_eval(line)


def parse_po(path):
    """Возвращает словарь {ключ .mo: строка перевода}."""
    messages = {}
    entry = {}
    section = None
    fuzzy = False

    def flush():
        nonlocal entry, fuzzy
        if "msgid" in entry and not fuzzy:
            key = entry["msgid"]
            if "msgctxt" in entry:
                key = entry["msgctxt"] + "\x04" + key
            if "msgid_plural" in entry:
                key = key + "\x00" + entry["msgid_plural"]
                forms = [entry.get(f"msgstr[{i}]", "") for i in range(len([k for k in entry if k.startswith("msgstr[")]))]
                if all(forms):
                    messages[key] = "\x00".join(forms)
            elif entry.get("msgstr") or entry["msgid"] == "":
                messages[key] = entry.get("msgstr", "")
        entry, fuzzy = {}, False

    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            flush()
            section = None
            continue
        if line.startswith("#,") and "fuzzy" in line:
            fuzzy = True
            continue
        if line.startswith("#"):
            continue
        if line.startswith('"'):
            if section is None:
                raise CommandError(f"{path}: unexpected string: {raw}")
            entry[section] += _unquote(line)
            continue
        keyword, _, rest = line.partition(" ")
        if keyword == "msgid" and "msgid" in entry and section and section.startswith("msgstr"):
            flush()
        section = keyword
        entry[section] = _unquote(rest)
    flush()
    return messages


def write_mo(messages, path):
    """Формат GNU .mo (little-endian, без хеш-таблицы)."""
    keys = sorted(messages)
    ids = b""
    strs = b""
    offsets = []
    for key in keys:
        k = key.encode("utf-8")
        v = messages[key].encode("utf-8")
        offsets.append((len(ids), len(k), len(strs), len(v)))
        ids += k + b"\x00"
        strs += v + b"\x00"
    n = len(keys)
    key_start = 7 * 4 + 16 * n
    value_start = key_start + len(ids)
    koffsets, voffsets = [], []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + key_start]
        voffsets += [l2, o2 + value_start]
    output = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    output += struct.pack(f"{len(koffsets)}i", *koffsets)
    output += struct.pack(f"{len(voffsets)}i", *voffsets)
    output += ids + strs
    Path(path).write_bytes(output)


class Command(BaseCommand):
    help = "Компилирует .po файлы проекта в .mo без внешних утилит gettext."

    def handle(self, *args, **options):
        found = 0
        for base in settings.LOCALE_PATHS:
            for po in sorted(Path(base).glob("*/LC_MESSAGES/*.po")):
                messages = parse_po(po)
                write_mo(messages, po.with_suffix(".mo"))
                found += 1
                self.stdout.write(f"{po.relative_to(settings.BASE_DIR)} → .mo ({len(messages) - 1} messages)")
        if not found:
            raise CommandError("No .po files found in LOCALE_PATHS.")
        self.stdout.write(self.style.SUCCESS("Done."))
