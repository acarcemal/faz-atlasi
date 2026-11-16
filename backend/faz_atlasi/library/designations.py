"""
Norm adlarının sadeleştirilmesi ve veri setlerindeki serbest metin adlardan norm çıkarılması.

code_norm: büyük harf, sadece harf+rakam. '1.7225' -> '17225', 'X5CrNi18-10' -> 'X5CRNI1810', 'SCM 440' -> 'SCM440'.
GOST adları Kiril ya da Latin harfle yazılabilir (12Х18Н10Т / 12X18N10T); ikisi aynı biçime indirilir.
"""
import re
import unicodedata

SISTEMLER = ('EN', 'WNR', 'AISI', 'UNS', 'ASTM', 'ACI', 'JIS', 'GOST', 'BS', 'TRADE')

# Kullanıcı aramaya norm önekini de yazabilir: "AISI 4140", "W.Nr. 1.7225", "JIS SCM440"
_ONEKLER = ('AISI', 'SAE', 'DIN', 'EN', 'WNR', 'WERKSTOFF', 'UNS', 'ASTM', 'ACI', 'JIS', 'GOST', 'BS')

# GOST harfleri: Kiril -> veri setindeki Latin harf çevirisi
_KIRIL = str.maketrans({
    'Х': 'X', 'Н': 'N', 'Т': 'T', 'М': 'M', 'В': 'V', 'Ф': 'F', 'Б': 'B', 'Г': 'G', 'С': 'S', 'Ю': 'YU',
    'Д': 'D', 'К': 'K', 'Р': 'R', 'А': 'A', 'Ц': 'C', 'Е': 'E', 'П': 'P', 'Ш': 'SH', 'У': 'U', 'Л': 'L',
})


def normalize(code, system=None):
    s = unicodedata.normalize('NFKC', str(code)).upper().translate(_KIRIL)
    s = re.sub(r'[^0-9A-Z]', '', s)
    if system == 'GOST':
        # Latin çeviride Si bazen 'C' (Kiril С) bazen 'S' yazılmış (36X18N25C2 / 40X10S2M); tek biçime indir
        s = s.replace('C', 'S')
    return s


def query_variants(q):
    """Arama metninin denenecek sadeleştirilmiş biçimleri (önekli ve öneksiz, GOST biçimi)."""
    n = normalize(q)
    out = [n]
    for on in _ONEKLER:
        if n.startswith(on) and len(n) > len(on):
            out.append(n[len(on):])
    out += [normalize(v, 'GOST') for v in list(out)]
    return list(dict.fromkeys(v for v in out if v))


def library_aisi(field):
    """celik_kutuphanesi.py'deki 'AISI/SAE' alanı -> [(sistem, kod, approx)]. '—' boş demek."""
    field = field.strip()
    if not field or field == '—':
        return []
    approx = '≈' in field
    kod = field.replace('(≈)', '').replace('≈', '').strip()
    if re.match(r'^A\d', kod) or re.match(r'^WC', kod):   # A36, A572 Gr.50, WCB, WC6, WC9 -> ASTM
        return [('ASTM', kod, approx)]
    return [('AISI', kod, approx)]


# Mendeley 3234 setindeki adların sonundaki açıklamalar
_SONEK = re.compile(r'\s+(?:High Manganese |Nonresulfurized |Low |)(?:Carbon |Alloy |)Steel$')


def parse_dataset_name(name):
    """
    'AISI 4140 Steel' -> ('AISI', '4140', 'grade'); 'ASTM A387 Alloy Steel' -> ('ASTM', 'A387', 'specification').
    Dönüş: (sistem, kod, kapsam) listesi. ASTM adları çoğunlukla şartnamedir (bir şartname birden çok kalite içerir).
    """
    ad = name.replace('®', '').strip()
    m = re.match(r'^Cast Stainless Steel\s+(\S+)$', ad)
    if m:
        return [('ACI', m.group(1), 'grade')]
    m = re.search(r'UNS\s+([A-Z]\d{5})', ad)
    if m:
        return [('UNS', m.group(1), 'grade'), ('TRADE', re.sub(r'\s+UNS.*$', '', ad), 'grade')]
    m = re.match(r'^(?:AK Steel\s+)?ASTM\s+A\s?(\d+)(.*)$', ad)
    if m:
        ek = _SONEK.sub('', m.group(2)).strip()
        if ek.lower() in ('steel', ''):
            return [('ASTM', 'A' + m.group(1), 'specification')]
        return [('ASTM', f'A{m.group(1)} {ek}', 'grade')]   # 'A209 T1', 'A424 Type II'
    m = re.match(r'^AISI\s+(.+)$', ad)
    if m:
        kod = _SONEK.sub('', m.group(1)).strip()
        return [('AISI', re.sub(r'\s+H$', 'H', kod), 'grade')]       # 'E4340 H' -> 'E4340H'
    m = re.match(r'^JIS\s+(\S+)', ad)
    if m:
        return [('JIS', m.group(1), 'grade')]
    m = re.match(r'^BS\s+\S+\s+(\d{3}[A-Z]\d{2})', ad)               # 'BS 970/1(83) 070M55 ...'
    if m:
        return [('BS', m.group(1), 'grade')]
    m = re.match(r'^Latrobe\s+(.+?)(?:\s+VAC-ARC)?$', ad)
    if m:
        return [('TRADE', m.group(1), 'grade')]
    return [('TRADE', ad, 'grade')]
