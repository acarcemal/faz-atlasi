// Paylaşım / README görselleri için senaryolar (hesap/gorsel_uret.ps1 kullanır).
// web/_gorsel.html içine eklenir; adres sonundaki #senaryo ile uygulamayı o duruma getirir.
(async () => {
  const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
  const s = location.hash.slice(1);
  const tema = (x) => { document.documentElement.dataset.theme = x; temaYaz(); };
  const celik = async (ad) => {
    const ara = document.getElementById('celikAra');
    ara.value = ad; ara.dispatchEvent(new Event('input')); await bekle(50);
    document.querySelector('#celikListe [data-secim]').click();
    for (let i = 0; i < 100 && !KAYNAK.alt; i++) await bekle(30);
    ara.blur(); await bekle(150);
  };
  await bekle(300);
  // önceki çekimden kalan sabit noktaları temizle (aynı tarayıcı profili kullanılıyor)
  st.pinler = []; try { localStorage.removeItem('fec-pinler-v1'); } catch (e) { /* yok */ }
  if (s === 'kesit') {
    tema('dark');
    document.getElementById('detayBtn').click(); await bekle(100);
    await celik('42CrMo4');
    document.querySelector('[data-katman=etiket]').click();   // bölge adları kalabalık etmesin
    sec(0.42, 845); await bekle(100);
    pinEkle(0.9, 735); await bekle(150);
    const p = gorunenPinler()[0];
    KANCA.uzerinde.forEach((f) => f(sx(p.w), sy(p.T))); guncelle();
  } else if (s === 'ikili') {
    tema('light');
    document.querySelector('[data-v=celik]').click(); await bekle(50);
    sec(0.35, 765); await bekle(100);
  } else if (s === 'bilgi') {
    tema('light');
    document.getElementById('detayBtn').click(); await bekle(100);
    await celik('100Cr6'); sec(1.0, 790); await bekle(100);
    bilgiAc('kIslem');
  } else if (s === 'mobil') {
    tema('dark');
    document.querySelector('[data-v=celik]').click(); sec(0.6, 760);
  }
  await bekle(300);
  document.title = 'HAZIR';
})();
