"""Собирает index.html из src/template.html: типографика и встроенные фото из папки img.

Каталог букетов (массивы IMG и bouquets в template.html) приходит из базы бота:
в папке бота  python -m tools.catalog export. Руками эти массивы не правим.

Запуск из папки проекта:  python src/build.py
"""
import base64
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, '..', 'img')
NB = ' '  # неразрывный пробел

SHORT = ('а в и к о с у во да до за из ко на не но ни об от по со '
         'для без при под над про или').split()
SHORT_RE = re.compile(r'(?<![\w-])(' + '|'.join(sorted(set(SHORT), key=len, reverse=True)) + r') (?=\S)',
                      re.IGNORECASE)
UNITS_RE = re.compile(r'(\d) (BYN|₽|мин|минут|часа|часов|дней|дня|роз|символов|из|г\.)')


def typograph(s):
    s = SHORT_RE.sub(lambda m: m.group(1) + NB, s)
    s = SHORT_RE.sub(lambda m: m.group(1) + NB, s)  # второй проход для «и в», «а на»
    s = s.replace(' — ', NB + '— ').replace(' – ', NB + '– ')
    s = UNITS_RE.sub(lambda m: m.group(1) + NB + m.group(2), s)
    s = s.replace('+375 (29) 000-00-00', '+375' + NB + '(29)' + NB + '000-00-00')
    s = re.sub(r'(№|г\.|ул\.|д\.) ', lambda m: m.group(1) + NB, s)
    s = re.sub(r'(\d) (\d{3})(?!\d)', lambda m: m.group(1) + NB + m.group(2), s)
    return s


def typograph_html(html):
    """Меняет только видимый текст между тегами, не трогая CSS, JS и атрибуты."""
    out, skip = [], None
    for part in re.split(r'(<[^>]+>)', html):
        if part.startswith('<'):
            low = part.lower()
            if skip is None and (low.startswith('<style') or low.startswith('<script')):
                skip = 'style' if low.startswith('<style') else 'script'
            elif skip and low.startswith('</' + skip):
                skip = None
            # подписи для окошка звонка — тоже текст для людей
            part = re.sub(r'(data-call-(?:sub|title)=")([^"]*)(")',
                          lambda m: m.group(1) + typograph(m.group(2)) + m.group(3), part)
            out.append(part)
        elif skip:
            out.append(part)
        else:
            out.append(typograph(part))
    return ''.join(out)


def typograph_js_data(html):
    """Тексты букетов и вопросов живут в JS — обрабатываем только строки внутри этих массивов."""
    for name in ('var bouquets = [', 'var faq = ['):
        s = html.index(name)
        e = html.index('];', s)
        block = re.sub(r"'((?:[^'\\]|\\.)*)'", lambda m: "'" + typograph(m.group(1)) + "'", html[s:e])
        html = html[:s] + block + html[e:]
    return html


def strip_gaps(html):
    """Убирает пустые переносы строк между тегами (они только для читаемости исходника).
    Иначе некоторые просмотрщики рисуют на их месте лишние символы. Скрипты, стили и поля ввода не трогаем."""
    parts = re.split(r'(<(script|style|textarea|pre)\b.*?</\2>)', html, flags=re.S)
    out = []
    for k, part in enumerate(parts):
        if k % 3 == 0:
            part = re.sub(r'>[ \t]*\n\s*<', '><', part)
        elif k % 3 == 1:
            out.append(part)
            continue
        else:
            continue
        out.append(part)
    return ''.join(out)


def main():
    root = os.path.join(HERE, '..')
    t = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    t = strip_gaps(typograph_js_data(typograph_html(t)))
    # Фото встраиваем по меткам __IMG_имя__ -> img/имя.jpg. Список не задан заранее:
    # новые фото букетов приходят из админки бота (python -m tools.catalog export).
    for k in sorted(set(re.findall(r'__IMG_(\w+)__', t))):
        path = os.path.join(IMG_DIR, k + '.jpg')
        if not os.path.exists(path):
            sys.exit('Ошибка: в шаблоне есть фото ' + k + ', а файла img/' + k + '.jpg нет')
        data = base64.b64encode(open(path, 'rb').read()).decode()
        t = t.replace('__IMG_' + k + '__', 'data:image/jpeg;base64,' + data)
    assert '__IMG_' not in t, 'в шаблоне есть фото, которого нет в папке img'
    head = ('<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">\n')
    i = t.index('</style>') + len('</style>')
    out = os.path.join(root, 'index.html')
    open(out, 'w', encoding='utf-8').write(head + t[:i] + '\n</head>\n<body>\n' + t[i:] + '\n</body>\n</html>\n')
    print('Готово: index.html,', os.path.getsize(out) // 1024, 'КБ')


if __name__ == '__main__':
    sys.exit(main())
