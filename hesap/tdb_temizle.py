"""
MatCalc TDB dosyasını pycalphad'ın okuyabileceği hale getirir.
Orijinal dosyaya dokunmaz; temizlenmiş kopyayı yazar.

  .venv/Scripts/python hesap/tdb_temizle.py hesap/tdb/mc_fe_v2062.tdb hesap/tdb/mc_fe_pycalphad.tdb

Atılan MatCalc'a özgü komutlar:
  REFERENCE_ELEMENT, ATTACH_CONTRIBUTION (BCC_B2 düzen/düzensizlik — Fe-C-X çeliklerde gereksiz)
  ADD_COMPOSITION_SET -> pycalphad kendi kompozisyon kümelerini otomatik açar (miscibility gap),
                         bu yüzden FCC_A1 içindeki MC karbürleri (VC, NbC, TiC) yine bulunabilir.
Atılan parametre türleri:
  HMVA (boşluk oluşum entalpisi, sadece kinetik; dengeye etkisi yok)
Yazım hatası düzeltmesi:
  G(FAZ;A:B;0) -> G(FAZ,A:B;0)  (kaynakta faz adından sonra virgül yerine ';' yazılmış parametreler)
"""
import re, sys

ATILAN = {'REFERENCE_ELEMENT', 'ATTACH_CONTRIBUTION', 'ADD_COMPOSITION_SET'}
ATILAN_PARAM = {'HMVA'}

# Çelik hesabı için gereken elementler; diğerlerini içeren parametreler atılır
# (ilgisiz sistemlerdeki — Pd, Ti, Y ... — yazım hatalarından da böylece kurtuluyoruz)
ELEMENT_KUMESI = {'FE', 'C', 'VA', 'MN', 'SI', 'CR', 'NI', 'MO', 'V', 'W', 'CU'}

TDB_KOMUTLARI = ('ELEM', 'SPEC', 'FUNC', 'PHAS', 'CONST', 'PARAM', 'TYPE_DEF',
                 'DEFINE_SYSTEM_DEFAULT', 'DEFAULT_COMMAND')

src, dst = sys.argv[1], sys.argv[2]
metin = open(src, encoding='latin-1').read().replace('\r', '')
satirlar = [s for s in metin.split('\n') if not s.lstrip().startswith('$')]
metin = '\n'.join(satirlar).encode('ascii', 'ignore').decode()

cikti, sayac = [], {}
# kaynakta '!' unutulmuş yerler: ifadenin ortasında yeni bir komut başlıyorsa böl
KOMUT = r'\s(?=(?:PARAMETER|FUNCTION|PHASE|CONSTITUENT|TYPE_DEFINITION|ELEMENT|SPECIES)\s)'
ifadeler = []
for ifade in metin.split('!'):
    parcalar = re.split(KOMUT, ifade.strip())
    if len(parcalar) > 1:
        sayac['eksik_unlem'] = sayac.get('eksik_unlem', 0) + len(parcalar) - 1
    ifadeler.extend(parcalar)
for ifade in ifadeler:
    s = ifade.strip()
    if not s:
        continue
    ilk = s.split()[0].upper()
    if ilk in ATILAN:
        sayac[ilk] = sayac.get(ilk, 0) + 1
        continue
    # beyaz liste: standart TDB komutu ile başlamayan her şeyi (kaynakça listesi vb.) at
    if not any(ilk.startswith(k) for k in TDB_KOMUTLARI):
        sayac['standart_disi'] = sayac.get('standart_disi', 0) + 1
        continue
    if ilk.startswith('PARAM'):
        tur = s.split()[1].split('(')[0].upper()
        if tur in ATILAN_PARAM:
            sayac[tur] = sayac.get(tur, 0) + 1
            continue
        # bizim element kümesi dışında element içeren parametreleri at
        m = re.match(r'PARAM\w*\s+\w+\(\s*[\w%]+\s*[,;]\s*([^;)]*)', s, re.I)
        if m:
            turler = {t.strip().upper() for t in re.split(r'[,:]', m.group(1)) if t.strip()}
            if turler - ELEMENT_KUMESI - {'*'}:
                sayac['disari_param'] = sayac.get('disari_param', 0) + 1
                continue
        # sondaki kaynakça etiketini at (bazıları bozuk: 'REF:TEST KOZE10'); hesaba etkisi yok
        s = re.sub(r'(\s[NY])\s+REF.*$', r'\1', s, flags=re.S)
    cikti.append(s)

# Fazları süz: bir alt kafeste bizim elementlerden hiçbiri yoksa faz oluşamaz -> at.
# Kalan fazların bileşen listelerinden dışarıdaki elementleri (ve bozuk işaretleri) çıkar.
atilan_faz = set()
for i, s in enumerate(cikti):
    if not s.upper().startswith('CONSTITUENT'):
        continue
    ad = s.split()[1].split(':')[0].upper()
    govde = s[s.index(':'):] if ':' in s else ''
    altlar = [a for a in govde.strip().strip(':').split(':')]
    yeni = []
    for a in altlar:
        turler = [t.strip() for t in a.split(',') if t.strip()]
        kalan = [t for t in turler if t.rstrip('%').upper() in ELEMENT_KUMESI]
        yeni.append(kalan)
    if any(not k for k in yeni):
        atilan_faz.add(ad)
    else:
        cikti[i] = f'CONSTITUENT {ad} :' + ':'.join(','.join(k) for k in yeni) + ':'

def _faz_adi(s):
    u = s.upper().split()
    if u[0] == 'PHASE':
        return u[1].split(':')[0]
    if u[0] == 'CONSTITUENT':
        return u[1].split(':')[0]
    if u[0] == 'TYPE_DEFINITION' and 'AMEND_PHASE_DESCRIPTION' in u:
        return u[u.index('AMEND_PHASE_DESCRIPTION') + 1]
    if u[0].startswith('PARAM'):
        m = re.match(r'PARAM\w*\s+\w+\(\s*([\w%]+)', s, re.I)
        return m.group(1).upper() if m else None
    return None

once = len(cikti)
cikti = [s for s in cikti if _faz_adi(s) not in atilan_faz]
sayac['atilan_faz'] = len(atilan_faz)
sayac['faz_satiri'] = once - len(cikti)

sonuc = ' !\n'.join(cikti) + ' !\n'
duzeltilen = []
def _duzelt(m):
    duzeltilen.append(m.group(0))
    return m.group(1) + ',' + m.group(2) + ';'
sonuc = re.sub(r'(PARAMETER\s+\w+\(\s*[\w%]+)\s*;([^;()]+);', _duzelt, sonuc)
sayac['virgul_duzeltme'] = len(duzeltilen)
# '6000.00.00' gibi çift ondalık noktalı sıcaklık sınırları
sonuc, n = re.subn(r'(\d+\.\d+)\.\d+(?=\s+[NY]\b)', r'\1', sonuc)
sayac['cift_nokta'] = n
with open(dst, 'w', encoding='ascii') as f:
    f.write(sonuc)
print('yazildi:', dst, '| atilan:', sayac)
