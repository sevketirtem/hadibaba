"""Hareketli avatarlar: assets/avatar/<kim>-<konusuyor|dinliyor>.mp4 (Gemini Omni Flash, 360x640, 24 fps)
klipleri kare kare okunur, ortadaki yuvarlak rozet kırpılır. Döngü ileri-geri (ping-pong) oynatılır ki
klip sonu ile başı arasında sıçrama olmasın.

Kullanım:
    ha = HareketliAvatar()            # klip yoksa ha.var == False, çağıran duran resme döner
    im = ha.kare("hadi", True, t, 170)  # RGBA daire, boy x boy
"""
import os, subprocess
from PIL import Image, ImageDraw

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLASOR = os.path.join(KOK, "assets", "avatar")
KIRP = (17, 151, 321, 455)  # rozetin klip içindeki yeri (360x640)
FPS = 12                    # bellek için klipten 12 kare/sn alınır


class HareketliAvatar:
    def __init__(self, taban=420):
        self.taban = taban
        self.kareler = {}
        self.var = False
        if os.environ.get("HAREKETLI_AVATAR", "1") == "0":
            return
        try:
            for kim in ("hadi", "yuru"):
                for durum in ("konusuyor", "dinliyor"):
                    yol = os.path.join(KLASOR, f"{kim}-{durum}.mp4")
                    if not os.path.exists(yol):
                        return
                    self.kareler[(kim, durum)] = self._oku(yol)
            self.var = all(len(v) > 10 for v in self.kareler.values())
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Hareketli avatar::okunamadı, duran resim kullanılacak: {e}", flush=True)
            self.var = False
        self.maskeler = {}

    def _oku(self, yol):
        b = self.taban
        x0, y0, x1, y1 = KIRP
        ham = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-vf",
                              f"fps={FPS},crop={x1 - x0}:{y1 - y0}:{x0}:{y0},scale={b}:{b}:flags=lanczos",
                              "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        n = len(ham) // (b * b * 3)
        ileri = [Image.frombytes("RGB", (b, b), ham[i * b * b * 3:(i + 1) * b * b * 3]) for i in range(n)]
        return ileri + ileri[-2:0:-1]  # ping-pong

    def _maske(self, boy):
        if boy not in self.maskeler:
            m = Image.new("L", (boy * 4, boy * 4), 0)
            ImageDraw.Draw(m).ellipse((8, 8, boy * 4 - 9, boy * 4 - 9), fill=255)
            self.maskeler[boy] = m.resize((boy, boy), Image.LANCZOS)
        return self.maskeler[boy]

    def kare(self, kim, konusuyor, t, boy):
        if not self.var:
            return None
        liste = self.kareler[(kim, "konusuyor" if konusuyor else "dinliyor")]
        # iki karakterin klipleri aynı anda aynı yüz ifadesine girmesin diye Yürü'ye küçük kaydırma
        i = int((t + (3.7 if kim == "yuru" else 0)) * FPS) % len(liste)
        im = liste[i].resize((boy, boy), Image.LANCZOS).convert("RGBA")
        im.putalpha(self._maske(boy))
        return im
