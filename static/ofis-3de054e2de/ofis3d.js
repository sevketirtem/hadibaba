// Hadi vs Yürü · 3D ajan ofisi (özgün kod; three.js MIT)
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const kap = document.querySelector('.harita');
const svg = document.getElementById('ofis');
const tuval = document.createElement('div');
tuval.style.cssText = 'position:relative;width:100%;aspect-ratio:' + (innerWidth < 700 ? '1/1' : '16/11') + ';touch-action:none';
const etiketKat = document.createElement('div');
etiketKat.style.cssText = 'position:absolute;inset:0;pointer-events:none;overflow:hidden';
tuval.append(etiketKat);

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
} catch (e) { throw new Error('WebGL yok, 2D ofis kalıyor'); }
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
tuval.prepend(renderer.domElement);
renderer.domElement.style.cssText = 'width:100%;height:100%;display:block;border-radius:12px';
svg.style.display = 'none';
kap.style.overflowX = 'visible';
kap.classList.add('uc-boyut');
kap.append(tuval);

const sahne = new THREE.Scene();
const kamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 400);
kamera.position.set(55, 62, 70);
const kontrol = new OrbitControls(kamera, renderer.domElement);
kontrol.enableDamping = true;
kontrol.enablePan = false;
kontrol.minPolarAngle = 0.55; kontrol.maxPolarAngle = 1.15;
kontrol.minZoom = 0.8; kontrol.maxZoom = 3;
kontrol.target.set(-1.5, 0, -2.5); kamera.position.add(new THREE.Vector3(-1.5, 0, -2.5));

sahne.add(new THREE.HemisphereLight(0xfff6e8, 0xb9a88c, 1.5));
const gunes = new THREE.DirectionalLight(0xffffff, 1.6);
gunes.position.set(-30, 60, 25);
gunes.castShadow = true;
gunes.shadow.mapSize.set(2048, 2048);
Object.assign(gunes.shadow.camera, { left: -40, right: 40, top: 40, bottom: -40, near: 1, far: 150 });
gunes.shadow.bias = -0.0008;
sahne.add(gunes);

const mat = (renk, ek = {}) => new THREE.MeshStandardMaterial(Object.assign({ color: renk, roughness: 0.85 }, ek));
function kutu(w, h, d, renk, ek) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), typeof renk === 'object' ? renk : mat(renk, ek));
  m.castShadow = true; m.receiveShadow = true; return m;
}
const ac = (hex, t) => new THREE.Color(hex).lerp(new THREE.Color(0xffffff), t);
const koyu = (hex, t) => new THREE.Color(hex).lerp(new THREE.Color(0x000000), t);

// ---------- ofis zemini ----------
const ODA = 9, ARA = 1.2, SUT = 4, SIRA = 3;
const genis = SUT * ODA + (SUT - 1) * ARA, derin = SIRA * ODA + (SIRA - 1) * ARA;
const kaide = kutu(genis + 3, 1.2, derin + 3, 0xe4d8c3); kaide.position.y = -0.6; sahne.add(kaide);
const koridor = kutu(genis + 1, 0.05, derin + 1, 0xf3ebdd); koridor.position.y = 0.02; sahne.add(koridor);

// ---------- kedi ----------
function kediYap(renk) {
  const g = new THREE.Group();
  const kurk = mat(renk, { roughness: 0.95 }), ic = mat(ac(renk, 0.55)), siyah = mat(0x222222);
  const govde = new THREE.Mesh(new THREE.SphereGeometry(0.62, 20, 16), kurk);
  govde.scale.set(1, 1.05, 0.85); govde.position.y = 0.62; govde.castShadow = true; g.add(govde);
  const gogus = new THREE.Mesh(new THREE.SphereGeometry(0.38, 16, 12), ic);
  gogus.position.set(0, 0.62, 0.36); gogus.scale.set(1, 1.2, 0.5); g.add(gogus);
  const bas = new THREE.Group(); bas.position.set(0, 1.42, 0.05); g.add(bas);
  const kafa = new THREE.Mesh(new THREE.SphereGeometry(0.46, 20, 16), kurk); kafa.scale.set(1.1, 0.95, 1); kafa.castShadow = true; bas.add(kafa);
  for (const s of [-1, 1]) {
    const kulak = new THREE.Mesh(new THREE.ConeGeometry(0.17, 0.32, 4), kurk);
    kulak.position.set(0.27 * s, 0.4, 0); kulak.rotation.z = -0.3 * s; bas.add(kulak);
    const kulakIc = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.2, 4), mat(0xf4b7b7));
    kulakIc.position.set(0.27 * s, 0.38, 0.06); kulakIc.rotation.z = -0.3 * s; bas.add(kulakIc);
    const goz = new THREE.Mesh(new THREE.SphereGeometry(0.065, 10, 8), siyah);
    goz.position.set(0.17 * s, 0.05, 0.42); goz.name = 'goz'; bas.add(goz);
    const kapak = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.025, 0.02), siyah);
    kapak.position.set(0.17 * s, 0.03, 0.46); kapak.name = 'kapak'; bas.add(kapak);
    const pati = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 10), ic);
    pati.position.set(0.28 * s, 0.12, 0.42); pati.name = 'pati'; g.add(pati);
  }
  const burun = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 6), mat(0xe58a8a)); burun.position.set(0, -0.05, 0.46); bas.add(burun);
  const kuyruk = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.09, 8, 20, Math.PI * 1.2), kurk);
  kuyruk.position.set(0.1, 0.3, -0.5); kuyruk.rotation.set(Math.PI / 2, 0, 0.6); kuyruk.castShadow = true; g.add(kuyruk);
  g.userData = { bas, kuyruk };
  return g;
}

// ---------- ekran yazısı ----------
function ekranDokusu() {
  const c = document.createElement('canvas'); c.width = 256; c.height = 160;
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return { c, t, ciz(durum, yazi) {
    const x = c.getContext('2d');
    x.fillStyle = durum === 'calis' ? '#0f2a44' : durum === 'hata' ? '#3a0f12' : '#1d2230'; x.fillRect(0, 0, 256, 160);
    x.fillStyle = durum === 'calis' ? '#7fd1ff' : durum === 'hata' ? '#ff8a8a' : '#55607a';
    x.font = 'bold 26px system-ui'; x.textAlign = 'center';
    if (durum === 'uyuyor') { x.font = 'bold 40px system-ui'; x.fillText('z z z', 128, 95); }
    else {
      const kel = String(yazi || (durum === 'hata' ? 'HATA' : 'çalışıyor')).split(' '); let satir = '', y = 50;
      for (const k of kel) { if (x.measureText(satir + k).width > 230) { x.fillText(satir, 128, y); y += 32; satir = ''; } satir += k + ' '; }
      x.fillText(satir, 128, y);
    }
    t.needsUpdate = true;
  } };
}

// ---------- odalar ----------
const odalar = [];
const tiklanir = [];
function odalariKur() {
  ODALAR.forEach((oda, i) => {
    const s = i % SUT, r = Math.floor(i / SUT);
    const x0 = -genis / 2 + s * (ODA + ARA) + ODA / 2, z0 = -derin / 2 + r * (ODA + ARA) + ODA / 2;
    const g = new THREE.Group(); g.position.set(x0, 0, z0); sahne.add(g);
    const zemin = kutu(ODA, 0.2, ODA, ac(oda.renk, 0.82)); zemin.position.y = 0.1; g.add(zemin);
    const duvarMat = mat(oda.renk);
    const arka = kutu(ODA, 3.4, 0.3, duvarMat); arka.position.set(0, 1.9, -ODA / 2 + 0.15); g.add(arka);
    const sol = kutu(0.3, 3.4, ODA, mat(koyu(oda.renk, 0.08))); sol.position.set(-ODA / 2 + 0.15, 1.9, 0); g.add(sol);
    const pencere = kutu(2.4, 1.3, 0.05, mat(0xcfe3f2, { emissive: 0x6c8aa0, emissiveIntensity: 0.25 }));
    pencere.position.set(-ODA / 2 + 0.32, 2.2, 0.5); pencere.rotation.y = Math.PI / 2; g.add(pencere);
    const tablo = kutu(1.5, 1.1, 0.06, 0xfffaf2); tablo.position.set(-2, 2.2, -ODA / 2 + 0.33); g.add(tablo);
    const tabloIc = kutu(1.1, 0.7, 0.07, ac(oda.renk, 0.3)); tabloIc.position.set(-2, 2.2, -ODA / 2 + 0.34); g.add(tabloIc);
    const hali = kutu(5, 0.04, 3.4, ac(oda.renk, 0.45)); hali.position.set(0.5, 0.22, 1.6); hali.castShadow = false; g.add(hali);
    const hali2 = kutu(3, 0.045, 1.6, ac(oda.renk, 0.15)); hali2.position.set(0.5, 0.23, 1.6); hali2.castShadow = false; g.add(hali2);
    // masa
    const masa = kutu(3.6, 0.18, 1.7, 0xd9c7a8); masa.position.set(0.5, 1.35, -1.6); g.add(masa);
    for (const [ax, az] of [[-1.6, -0.7], [1.6, -0.7], [-1.6, 0.7], [1.6, 0.7]]) { const a = kutu(0.12, 1.2, 0.12, 0xb59f7c); a.position.set(0.5 + ax, 0.75, -1.6 + az); g.add(a); }
    const ekran = ekranDokusu();
    const monitor = kutu(1.9, 1.2, 0.1, 0x2b2f3a); monitor.position.set(0.5, 2.25, -2.15); g.add(monitor);
    const yuz = new THREE.Mesh(new THREE.PlaneGeometry(1.75, 1.06), new THREE.MeshBasicMaterial({ map: ekran.t }));
    yuz.position.set(0.5, 2.25, -2.09); g.add(yuz);
    const ayak = kutu(0.12, 0.5, 0.12, 0x2b2f3a); ayak.position.set(0.5, 1.6, -2.18); g.add(ayak);
    const klavye = kutu(1.1, 0.06, 0.38, 0xf0ece4); klavye.position.set(0.5, 1.47, -1.2); g.add(klavye);
    // sandalye + kedi
    const sandalye = kutu(1.1, 0.15, 1.1, koyu(oda.renk, 0.3)); sandalye.position.set(0.5, 0.75, -0.2); g.add(sandalye);
    const kedi = kediYap(oda.ceo ? 0x3a3128 : koyu(oda.renk, 0.15)); kedi.position.set(0.5, 0.82, -0.25); kedi.rotation.y = Math.PI; g.add(kedi);
    if (oda.ceo) { const tac = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.34, 0.22, 6), mat(0xf2b134, { metalness: 0.6, roughness: 0.3 })); tac.position.y = 0.55; kedi.userData.bas.add(tac); }
    // eşyalar
    const saksi = kutu(0.6, 0.6, 0.6, 0xc98b5a); saksi.position.set(ODA / 2 - 0.9, 0.5, ODA / 2 - 0.9); g.add(saksi);
    const yaprak = new THREE.Mesh(new THREE.IcosahedronGeometry(0.75, 0), mat(0x5fa35a, { flatShading: true })); yaprak.position.set(ODA / 2 - 0.9, 1.45, ODA / 2 - 0.9); yaprak.castShadow = true; g.add(yaprak);
    if (/Veri|Bekçi/.test(oda.ad)) for (let k = 0; k < 2; k++) { const raf = kutu(1, 2.8, 1, 0x2f3542); raf.position.set(-ODA / 2 + 0.9, 1.6, -ODA / 2 + 1 + k * 1.2); g.add(raf);
      const isik = kutu(0.6, 0.06, 0.02, 0x7cff9a, { emissive: 0x2ecc71, emissiveIntensity: 1 }); isik.position.set(-ODA / 2 + 1.41, 2.2, -ODA / 2 + 1 + k * 1.2); isik.rotation.y = Math.PI / 2; g.add(isik); }
    if (/Müzik/.test(oda.ad)) { const hop = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 1.4, 16), mat(0x2b2f3a)); hop.position.set(-3, 0.9, 2.8); hop.castShadow = true; g.add(hop); }
    if (/Podcast/.test(oda.ad)) { const mik = new THREE.Mesh(new THREE.CapsuleGeometry(0.12, 0.25, 4, 8), mat(0x444444, { metalness: 0.5 })); mik.position.set(1.4, 1.75, -1.3); g.add(mik); }
    if (/Tahmin/.test(oda.ad)) { const kupa = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.15, 0.6, 12), mat(0xf2b134, { metalness: 0.7, roughness: 0.25 })); kupa.position.set(-0.8, 1.74, -1.8); g.add(kupa); }
    // durum işareti
    const unlem = new THREE.Sprite(new THREE.SpriteMaterial({ map: isaretDokusu('!', '#d63c3c'), depthTest: false })); unlem.scale.set(0.9, 0.9, 1); unlem.position.set(0.5, 3.3, -0.25); unlem.visible = false; g.add(unlem);
    const zz = new THREE.Sprite(new THREE.SpriteMaterial({ map: isaretDokusu('z', 'rgba(0,0,0,0)', '#8a7d68'), transparent: true, depthTest: false })); zz.scale.set(0.8, 0.8, 1); zz.position.set(1.1, 2.6, -0.25); g.add(zz);
    // etiket
    const et = document.createElement('div'); et.className = 'etiket3d';
    et.innerHTML = '<b></b><small></small>'; et.querySelector('b').textContent = oda.ad;
    et.style.pointerEvents = 'auto'; et.onclick = () => window.odaDetay && window.odaDetay(oda);
    etiketKat.append(et);
    const kayit = { oda, g, kedi, ekran, unlem, zz, et, durum: 'uyuyor', zipla: 0 };
    g.traverse(m => { if (m.isMesh) { m.userData.kayit = kayit; tiklanir.push(m); } });
    odalar.push(kayit);
  });
}
function isaretDokusu(harf, zemin, yazi = '#fff') {
  const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d');
  x.fillStyle = zemin; x.beginPath(); x.arc(32, 32, 30, 0, Math.PI * 2); x.fill();
  x.fillStyle = yazi; x.font = 'bold 40px system-ui'; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(harf, 32, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------- veri geldikçe ----------
function guncelle() {
  for (const k of odalar) {
    const du = k.oda._du || {}; const yeni = du.calis ? 'calis' : du.hata ? 'hata' : 'uyuyor';
    k.durum = yeni;
    k.ekran.ciz(yeni, du.calis ? (k.oda._adim || 'çalışıyor') : du.hata ? 'HATA · bak' : '');
    k.unlem.visible = yeni === 'hata'; k.zz.visible = yeni === 'uyuyor';
    const s = k.et.querySelector('small');
    s.textContent = du.calis ? '● ' + (k.oda._adim ? 'şu an: ' + k.oda._adim : 'çalışıyor') : du.hata ? '● hata'
      : 'uyuyor' + (du.son ? ' · ' + onceSure(du.son.created_at).replace(' önce', '') : '') + (du.bugun ? ' · ' + du.bugun + ' iş' : '');
    s.className = yeni;
  }
}
window.addEventListener('ofis-veri', guncelle);

// ---------- tıklama: oda detayı + kedi numarası ----------
const ray = new THREE.Raycaster(), fare = new THREE.Vector2(); let basla = null;
renderer.domElement.addEventListener('pointerdown', e => { basla = [e.clientX, e.clientY]; });
renderer.domElement.addEventListener('pointerup', e => {
  if (!basla || Math.hypot(e.clientX - basla[0], e.clientY - basla[1]) > 6) return;
  const r = renderer.domElement.getBoundingClientRect();
  fare.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  ray.setFromCamera(fare, kamera);
  const hit = ray.intersectObjects(tiklanir, false)[0]; if (!hit) return;
  const k = hit.object.userData.kayit; k.zipla = 1; window.odaDetay && window.odaDetay(k.oda);
});

// ---------- boyut ve döngü ----------
function boyut() {
  const w = tuval.clientWidth, h = tuval.clientHeight; renderer.setSize(w, h, false);
  const oran = w / h, yar = oran < 1.2 ? 17 : 16.5; kamera.left = -yar * oran; kamera.right = yar * oran; kamera.top = yar; kamera.bottom = -yar;
  kamera.updateProjectionMatrix();
}
new ResizeObserver(boyut).observe(tuval);
const v = new THREE.Vector3(), saat = new THREE.Clock();
function dongu() {
  const dt = Math.min(saat.getDelta(), 0.05), t = saat.elapsedTime;
  kontrol.update();
  const w = tuval.clientWidth, h = tuval.clientHeight;
  for (const k of odalar) {
    const { bas, kuyruk } = k.kedi.userData; const faz = k.oda.ad.length;
    if (k.durum === 'calis') {
      k.kedi.position.y = 0.82 + Math.abs(Math.sin(t * 8 + faz)) * 0.08;
      bas.rotation.x = -0.15 + Math.sin(t * 6 + faz) * 0.06; bas.position.y = 1.42;
      k.kedi.children.filter(c => c.name === 'pati').forEach((p, i) => p.position.y = 0.12 + Math.abs(Math.sin(t * 14 + i * 1.6)) * 0.12);
    } else if (k.durum === 'uyuyor') {
      k.kedi.position.y = 0.82; bas.rotation.x = 0.55; bas.position.y = 1.25 + Math.sin(t * 1.5 + faz) * 0.02;
      k.zz.position.y = 2.4 + ((t * 0.4 + faz * 0.1) % 1) * 1.2; k.zz.material.opacity = 1 - ((t * 0.4 + faz * 0.1) % 1);
    } else { bas.rotation.x = -0.1; bas.rotation.z = Math.sin(t * 3) * 0.15; k.unlem.position.y = 3.3 + Math.sin(t * 4) * 0.1; }
    bas.traverse(m => { if (m.name === 'goz') m.visible = k.durum !== 'uyuyor'; if (m.name === 'kapak') m.visible = k.durum === 'uyuyor'; });
    kuyruk.rotation.z = 0.6 + Math.sin(t * (k.durum === 'calis' ? 6 : 1.2) + faz) * 0.25;
    if (k.zipla > 0) { k.zipla = Math.max(0, k.zipla - dt * 1.4); const p = 1 - k.zipla; k.kedi.position.y += Math.sin(p * Math.PI) * 1.6; k.kedi.rotation.y = Math.PI + p * Math.PI * 2; }
    // etiketi ekrana yansıt
    v.set(-1.2, 4.2, -3.2).applyMatrix4(k.g.matrixWorld).project(kamera);
    k.et.style.transform = `translate(-50%,-100%) translate(${(v.x * 0.5 + 0.5) * w}px,${(-v.y * 0.5 + 0.5) * h}px)`;
  }
  renderer.render(sahne, kamera);
  requestAnimationFrame(dongu);
}
odalariKur(); boyut(); guncelle(); dongu();
window.ofis3d = true;
