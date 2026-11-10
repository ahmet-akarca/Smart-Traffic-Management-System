import cv2
import numpy as np
import time
import os
import argparse
import socket
import json
import uuid
import tkinter as tk
from tkinter import ttk
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont  # Emojiler için Pillow kütüphanesi

# --- KOMUT SATIRI ARGÜMANLARINI AYRIŞTIRMA ---
parser = argparse.ArgumentParser(description="Otonom Kamera Süreci")
parser.add_argument("--camera", type=str, default="KAMERA_1", help="Çalıştırılacak Kamera ID'si")
parser.add_argument("--video", type=str, default="4corner2.mp4", help="İşlenecek Video Dosyasının Adı")
# ESKİ HALİ:
# parser.add_argument("--data_dir", type=str, default=".", help="...")

# YENİ HALİ (Varsayılan olarak direkt C# klasörüne baksın):
parser.add_argument("--data_dir", type=str, default=r"D:\MapApp\MapApp\bin\Debug\net8.0-windows", help="C# JSON dosyalarının bulunduğu ortak klasör")
args = parser.parse_args()

# --- UDP SOKET AYARLARI ---
UDP_IP = "host.docker.internal"  # DOCKER İÇİN GÜNCELLENDİ
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- RENK PALETLERİ ---
SERIT_RENKLERI = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 0, 255), (0, 165, 255), (255, 255, 0), (147, 20, 255)]
OK_RENKLERI = [(255, 0, 255), (0, 255, 255), (255, 255, 0), (200, 100, 50), (50, 200, 100), (0, 150, 255)]


def create_1_to_1_roi(pts, frame_shape=(768, 1024)):
    x, y, w, h = cv2.boundingRect(pts)
    mask = np.zeros((frame_shape[0], frame_shape[1]), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 255)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        c = max(contours, key=cv2.contourArea)
        return cv2.approxPolyDP(c, 0.005 * cv2.arcLength(c, True), True)
    return pts


def hesapla_zincir_yogunlugu(baslangic_id, etki_sozlugu, yogunluk_havuzu, max_derinlik=3, visited=None):
    if visited is None:
        visited = set()

    toplam_gelen = 0
    detaylar = []
    oncekiler = etki_sozlugu.get(baslangic_id, {}).get("oncekiler", [])

    for oid in oncekiler:
        if oid not in visited:
            visited.add(oid)
            arac = yogunluk_havuzu.get(oid, 0)
            toplam_gelen += arac

            kisa_id = oid[-6:] if len(oid) > 6 else oid
            detaylar.append(f"  -> ID ...{kisa_id}: {arac} Arac")

            if max_derinlik > 1:
                alt_toplam, alt_detaylar = hesapla_zincir_yogunlugu(oid, etki_sozlugu, yogunluk_havuzu,
                                                                    max_derinlik - 1, visited)
                toplam_gelen += alt_toplam
                detaylar.extend(alt_detaylar)

    return toplam_gelen, detaylar


def show_summary_dialog(polygons):
    root = tk.Tk()
    root.title("Şerit ID Listesi ve Onay")
    root.geometry("500x500")
    root.attributes('-topmost', True)
    root.configure(bg="#f4f4f4")

    tk.Label(root, text="Çizim Tamamlandı!", font=("Segoe UI", 14, "bold"), bg="#f4f4f4", fg="#333").pack(pady=10)
    tk.Label(root, text="C# Haritasına aktarmak için ID'leri kopyalayın.", font=("Segoe UI", 10), bg="#f4f4f4").pack(
        pady=5)

    frame_list = tk.Frame(root, bg="#f4f4f4")
    frame_list.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    canvas = tk.Canvas(frame_list, bg="#fff", highlightthickness=1, highlightbackground="#ccc")
    scrollbar = ttk.Scrollbar(frame_list, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#fff")

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def make_copy_cmd(text, btn):
        def cmd():
            root.clipboard_clear()
            root.clipboard_append(text)
            btn.config(text="Kopyalandı!", bg="#d4edda", fg="#155724")
            root.after(1500, lambda: btn.config(text="Kopyala", bg="#e2e6ea", fg="#333"))

        return cmd

    for p in polygons:
        row = tk.Frame(scrollable_frame, bg="#fff", pady=5)
        row.pack(fill=tk.X, expand=True, padx=10)
        lbl_id = tk.Label(row, text=p["id"], font=("Consolas", 9, "bold"), bg="#fff", fg="#0056b3", width=40,
                          anchor="w")
        lbl_id.pack(side=tk.LEFT)
        btn_copy = tk.Button(row, text="Kopyala", bg="#e2e6ea", relief=tk.FLAT, cursor="hand2")
        btn_copy.config(command=make_copy_cmd(p["id"], btn_copy))
        btn_copy.pack(side=tk.RIGHT, padx=5)

    def on_start():
        root.quit()
        root.destroy()

    btn_start = tk.Button(root, text="✔ SİSTEMİ BAŞLAT", font=("Segoe UI", 12, "bold"), bg="#28a745", fg="white",
                          relief=tk.FLAT, command=on_start, cursor="hand2")
    btn_start.pack(fill=tk.X, padx=20, pady=15, ipady=5)

    root.protocol("WM_DELETE_WINDOW", on_start)
    root.mainloop()


class PolygonDrawer:
    def __init__(self, window_name):
        self.window_name = window_name
        self.polygons = []
        self.links = []
        self.current_polygon = []
        self.mode = "DRAW"
        self.selected_link_idx = None
        self.scale = 1.0

    def mouse_callback(self, event, x, y, flags, param):
        real_x = int(x / self.scale)
        real_y = int(y / self.scale)

        if event == cv2.EVENT_MOUSEWHEEL:
            if flags > 0:
                self.scale = min(2.5, self.scale + 0.1)
            else:
                self.scale = max(0.5, self.scale - 0.1)
            return

        if self.mode == "DRAW":
            if event == cv2.EVENT_LBUTTONDOWN:
                self.current_polygon.append((real_x, real_y))
            elif event == cv2.EVENT_RBUTTONDOWN:
                if len(self.current_polygon) > 2:
                    self.polygons.append({"points": self.current_polygon.copy()})
                    self.current_polygon = []
        elif self.mode == "LINK":
            if event == cv2.EVENT_LBUTTONDOWN:
                clicked_idx = -1
                for i, p_data in enumerate(self.polygons):
                    pts = np.array(p_data["points"], np.int32)
                    if cv2.pointPolygonTest(pts, (float(real_x), float(real_y)), False) >= 0:
                        clicked_idx = i
                        break
                if clicked_idx != -1:
                    if self.selected_link_idx is None:
                        self.selected_link_idx = clicked_idx
                    elif self.selected_link_idx != clicked_idx:
                        self.links.append((self.selected_link_idx, clicked_idx))
                        self.selected_link_idx = None


def select_polygons(frame, camera_id="KAMERA_1"):
    drawer = PolygonDrawer(f"Cizim Ekrani - {camera_id} (Scroll: Zoom | Z: Geri Al)")
    cv2.namedWindow(drawer.window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(drawer.window_name, drawer.mouse_callback)

    while True:
        h, w = frame.shape[:2]
        new_w, new_h = int(w * drawer.scale), int(h * drawer.scale)
        display_frame = cv2.resize(frame.copy(), (new_w, new_h))

        info = "Cizim Modu: Sol Tikla Ekle, Sag Tikla Bitir. ENTER: Rotaya Gec." if drawer.mode == "DRAW" else "Rota Modu: Once Giris, Sonra Cikis. ENTER: Baslat."
        cv2.putText(display_frame, info, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(display_frame, info, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        for i, poly_data in enumerate(drawer.polygons):
            renk = SERIT_RENKLERI[i % len(SERIT_RENKLERI)]
            if drawer.mode == "LINK" and drawer.selected_link_idx == i: renk = (255, 255, 255)
            scaled_pts = (np.array(poly_data["points"], np.float32) * drawer.scale).astype(np.int32).reshape((-1, 1, 2))
            cv2.polylines(display_frame, [scaled_pts], isClosed=True, color=renk, thickness=2)
            M = cv2.moments(scaled_pts)
            if M["m00"] != 0:
                cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                cv2.putText(display_frame, f"S{i}", (cx - 10, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
                cv2.putText(display_frame, f"S{i}", (cx - 10, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.8, renk, 2)

        for link_idx, (idx1, idx2) in enumerate(drawer.links):
            pts1 = (np.array(drawer.polygons[idx1]["points"], np.float32) * drawer.scale).astype(np.int32)
            pts2 = (np.array(drawer.polygons[idx2]["points"], np.float32) * drawer.scale).astype(np.int32)
            M1, M2 = cv2.moments(pts1), cv2.moments(pts2)
            if M1["m00"] != 0 and M2["m00"] != 0:
                pt1 = (int(M1["m10"] / M1["m00"]), int(M1["m01"] / M1["m00"]))
                pt2 = (int(M2["m10"] / M2["m00"]), int(M2["m01"] / M2["m00"]))
                ok_rengi = OK_RENKLERI[idx2 % len(OK_RENKLERI)]
                cv2.arrowedLine(display_frame, pt1, pt2, ok_rengi, max(2, int(3 * drawer.scale)), tipLength=0.04)

        if len(drawer.current_polygon) > 0:
            scaled_curr = [(int(x * drawer.scale), int(y * drawer.scale)) for x, y in drawer.current_polygon]
            for i in range(len(scaled_curr) - 1):
                cv2.line(display_frame, scaled_curr[i], scaled_curr[i + 1], (255, 255, 255), 2)
            cv2.circle(display_frame, scaled_curr[-1], 4, (255, 255, 255), -1)

        cv2.imshow(drawer.window_name, display_frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('z') or key == 26:
            if len(drawer.current_polygon) > 0: drawer.current_polygon.pop()
        elif key == 13:
            if drawer.mode == "DRAW":
                drawer.mode = "LINK"
            else:
                break

    cv2.destroyWindow(drawer.window_name)

    girisler = set(l[0] for l in drawer.links)
    cikislar = set(l[1] for l in drawer.links)
    saf_cikislar = cikislar - girisler

    grup_sayaci = 1
    atanan_gruplar = {}
    for g, c in drawer.links:
        if c not in atanan_gruplar:
            atanan_gruplar[c] = grup_sayaci
            grup_sayaci += 1
        atanan_gruplar[g] = atanan_gruplar[c]

    for i, p in enumerate(drawer.polygons):
        grup_no = atanan_gruplar.get(i, grup_sayaci)
        if i not in atanan_gruplar: grup_sayaci += 1

        unique_hash = uuid.uuid4().hex[:8].upper()
        if i in saf_cikislar:
            p["id"] = f"{camera_id}_{unique_hash}_GRUP{grup_no}_CIKIS_{i}"
        else:
            p["id"] = f"{camera_id}_{unique_hash}_GRUP{grup_no}_GIRIS_{i}"

        pts = np.array(p["points"], np.int32)
        M = cv2.moments(pts)
        p["center"] = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])) if M["m00"] != 0 else (0, 0)

    if len(drawer.polygons) > 0: show_summary_dialog(drawer.polygons)
    return drawer.polygons, drawer.links


mouse_hover_pos = (-1, -1)


def main_mouse_callback(event, x, y, flags, param):
    global mouse_hover_pos
    if event == cv2.EVENT_MOUSEMOVE: mouse_hover_pos = (x, y)


def draw_rich_hover_info(overlay, x, y, data_lines):
    box_w = 420
    box_h = 15 + (len(data_lines) * 20)

    cv2.rectangle(overlay, (x, y), (x + box_w, y + box_h), (25, 25, 30), -1)
    cv2.rectangle(overlay, (x, y), (x + box_w, y + box_h), (255, 255, 255), 1)

    img_pil = Image.fromarray(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    try:
        font = ImageFont.truetype("seguiemj.ttf", 14)
    except IOError:
        font = ImageFont.load_default()

    for idx, text in enumerate(data_lines):
        color_bgr = (255, 255, 255)
        if "YESIL" in text:
            color_bgr = (0, 255, 0)
        elif "SARI" in text:
            color_bgr = (0, 255, 255)
        elif "KIRMIZI" in text:
            color_bgr = (0, 0, 255)
        elif "AMBULANS" in text or "ITFAIYE" in text:
            color_bgr = (0, 0, 255)
        elif "KAPASITE" in text:
            color_bgr = (0, 165, 255)
        elif "Hava:" in text:
            color_bgr = (255, 200, 0)
        elif "Levhalar:" in text or "Levha: Yok" in text:
            color_bgr = (0, 200, 255)
        elif text.startswith("  -"):
            color_bgr = (0, 200, 255)
        elif "HESAPLAMA" in text:
            color_bgr = (255, 100, 100)
        elif text.startswith("  -> ID"):
            color_bgr = (0, 200, 255)
        elif "Taban:" in text or "Kendi Araci:" in text:
            color_bgr = (200, 200, 200)
        elif "= HEDEF SURE:" in text:
            color_bgr = (0, 255, 0)
        elif "-" in text and len(text) > 10 and not text.startswith("  -"):
            color_bgr = (100, 100, 100)
        elif "ID:" in text:
            color_bgr = (150, 150, 255)

        b, g, r = color_bgr
        color_rgb = (r, g, b)

        try:
            draw.text((x + 10, y + 10 + (idx * 20)), text, font=font, fill=color_rgb, embedded_color=True)
        except TypeError:
            draw.text((x + 10, y + 10 + (idx * 20)), text, font=font, fill=color_rgb)

    overlay[:] = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


def main():
    video_path = args.video
    target_camera_id = args.camera

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Hata: {video_path} dosyası açılamadı!")
        return

    ret, first_frame = cap.read()
    if not ret: return
    first_frame = cv2.resize(first_frame, (1024, 768))

    window_title = f"Akilli Ag - {target_camera_id}"
    cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_title, 1024, 768)
    cv2.setMouseCallback(window_title, main_mouse_callback)

    # --- DOSYA YOLLARI DİNAMİK HALE GETİRİLDİ ---
    poly_file = os.path.join(args.data_dir, f"{target_camera_id}_polygons.json")

    if os.path.exists(poly_file):
        with open(poly_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            polygons_data = saved_data["polygons"]
            links = [tuple(l) for l in saved_data["links"]]
    else:
        polygons_data, links = select_polygons(first_frame, target_camera_id)
        if len(polygons_data) == 0: return
        with open(poly_file, "w", encoding="utf-8") as f:
            json.dump({"polygons": polygons_data, "links": links}, f)

    np_polygons = [np.array(p["points"], np.int32) for p in polygons_data]
    serit_idleri = [p["id"] for p in polygons_data]
    serit_merkezleri = [p["center"] for p in polygons_data]

    giris_yapanlar = set(l[0] for l in links)
    cikis_yapanlar = set(l[1] for l in links)
    saf_cikislar = cikis_yapanlar - giris_yapanlar

    model_trafik = YOLO("yolo11s.pt")
    model_acil_durum = YOLO("best.pt")

    aktif_serit_idx = 0
    while aktif_serit_idx in saf_cikislar and aktif_serit_idx < len(np_polygons): aktif_serit_idx += 1

    aktif_isik_durumu = "GREEN"
    faz_baslangici = time.time()

    TABAN_YESIL_SURESI = 5.0
    ARAC_BASINA_EK_SURE = 2.0
    ANTISIPASYON_SURE_CARPANI = 1.5
    MUTLAK_MAKSIMUM_SURE = 40.0
    SARI_ISIK_SURESI = 3.0
    HEDEF_SERIT_KAPASITESI = 6
    BOSLUK_TOLERANSI = 2.0

    son_dolu_zaman = time.time()
    kilitli_max_sure = TABAN_YESIL_SURESI
    frame_count = 0

    harita_ayarlari = []
    serit_etkileri = {}
    canli_yogunluk_havuzu = {}

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame_count += 1
        if frame_count % 10 != 0: continue
        frame = cv2.resize(frame, (1024, 768))
        su_an = time.time()

        if frame_count % 30 == 0:
            try:
                # --- DOSYA YOLLARI DİNAMİK HALE GETİRİLDİ ---
                json_yolu = os.path.join(args.data_dir, "seritler.json")
                if os.path.exists(json_yolu):
                    with open(json_yolu, "r", encoding="utf-8") as f:
                        harita_ayarlari = json.load(f)
            except:
                pass

            try:
                # --- DOSYA YOLLARI DİNAMİK HALE GETİRİLDİ ---
                yogunluk_yolu = os.path.join(args.data_dir, "canli_yogunluk.json")
                if os.path.exists(yogunluk_yolu):
                    with open(yogunluk_yolu, "r", encoding="utf-8") as f:
                        canli_yogunluk_havuzu = json.load(f)
            except:
                pass

        for ayar in harita_ayarlari:
            s_id = ayar.get("Id", "")
            h_durum = ayar.get("HavaDurumu", "Güneşli")
            h_carp = 1.0

            if "Yağmurlu" in h_durum or "Yagmurlu" in h_durum:
                h_carp = 1.2
            elif "Karlı" in h_durum or "Karli" in h_durum:
                h_carp = 1.5
            elif "Sisli" in h_durum:
                h_carp = 1.3

            l_detaylar = []
            l_toplam = 0
            for lev in ayar.get("Levhalar", []):
                ad = lev.get("Ad", "Levha")
                sure = lev.get("VarsayilanSureEtkisi", lev.get("Sure", 0))
                l_detaylar.append(f"  - {ad}: {sure:+}s")
                l_toplam += sure

            serit_etkileri[s_id] = {
                "h_durum": h_durum,
                "h_carp": h_carp,
                "levhalar": l_detaylar,
                "l_toplam": l_toplam,
                "oncekiler": ayar.get("OncekiSeritler", []),
                "sonrakiler": ayar.get("SonrakiSeritler", [])
            }

        bolge_arac_sayilari = [0] * len(np_polygons)
        yolo_kutu_listesi = []

        results_trafik = model_trafik.track(frame, persist=True, classes=[2, 3, 5, 7], device="cpu",
                                            tracker="bytetrack.yaml", verbose=False, imgsz=800, conf=0.15)

        for r in results_trafik:
            if r.boxes.id is not None:
                boxes = r.boxes.xyxy.cpu().numpy().astype(int)
                for box in boxes:
                    cx = (box[0] + box[2]) // 2
                    cy = box[3]

                    bulunan_serit = -1
                    for i, pts in enumerate(np_polygons):
                        if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                            bolge_arac_sayilari[i] += 1
                            bulunan_serit = i
                            break
                    yolo_kutu_listesi.append((box, bulunan_serit, "YOLO"))

        acil_durum_seridi = -1
        tespit_edilen_tip = "YOK"
        results_acil = model_acil_durum.predict(frame, device="cpu", verbose=False, imgsz=640, conf=0.65)

        for r in results_acil:
            if len(r.boxes) > 0:
                boxes = r.boxes.xyxy.cpu().numpy().astype(int)
                classes = r.boxes.cls.cpu().numpy().astype(int)

                for box, cls_id in zip(boxes, classes):
                    cx = (box[0] + box[2]) // 2
                    cy = box[3]

                    for i, pts in enumerate(np_polygons):
                        if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                            acil_durum_seridi = i
                            if cls_id == 0:
                                tespit_edilen_tip = "AMBULANS"
                            elif cls_id == 1:
                                tespit_edilen_tip = "ITFAIYE"

                            yolo_kutu_listesi.append((box, i, tespit_edilen_tip))
                            break

        hedef_doluluk_carpani = 1.0
        hedef_tamamen_dolu = False
        bagli_hedef_seritler = [l[1] for l in links if l[0] == aktif_serit_idx]

        if len(bagli_hedef_seritler) > 0:
            en_dolu_hedef_sayisi = max([bolge_arac_sayilari[h] for h in bagli_hedef_seritler])
            if en_dolu_hedef_sayisi >= HEDEF_SERIT_KAPASITESI:
                hedef_tamamen_dolu = True
            elif en_dolu_hedef_sayisi >= (HEDEF_SERIT_KAPASITESI - 2):
                hedef_doluluk_carpani = 0.5

        if acil_durum_seridi != -1 and acil_durum_seridi not in saf_cikislar:
            if aktif_serit_idx != acil_durum_seridi:
                print(f"🚨 {tespit_edilen_tip} TESPİT EDİLDİ! Şerit {acil_durum_seridi} için geçiş üstünlüğü devrede!")
                aktif_serit_idx = acil_durum_seridi
                aktif_isik_durumu = "GREEN"

            faz_baslangici = su_an
            kilitli_max_sure = 25.0
            hedef_tamamen_dolu = False

        gecen_sure = su_an - faz_baslangici

        if aktif_isik_durumu == "YELLOW":
            if gecen_sure >= SARI_ISIK_SURESI:
                sonraki = (aktif_serit_idx + 1) % len(np_polygons)
                denenen = 0
                while denenen < len(np_polygons):
                    if sonraki in saf_cikislar:
                        sonraki = (sonraki + 1) % len(np_polygons);
                        denenen += 1;
                        continue
                    aday_hedefler = [l[1] for l in links if l[0] == sonraki]
                    aday_hedef_dolu = False
                    for ah in aday_hedefler:
                        if bolge_arac_sayilari[ah] >= HEDEF_SERIT_KAPASITESI: aday_hedef_dolu = True
                    if bolge_arac_sayilari[sonraki] > 0 and not aday_hedef_dolu: break
                    sonraki = (sonraki + 1) % len(np_polygons);
                    denenen += 1

                aktif_serit_idx = sonraki
                aktif_isik_durumu = "GREEN"
                faz_baslangici, son_dolu_zaman = su_an, su_an
                kilitli_max_sure = TABAN_YESIL_SURESI

        elif aktif_isik_durumu == "GREEN":
            aktif_id = serit_idleri[aktif_serit_idx]
            etki_data = serit_etkileri.get(aktif_id, {"h_carp": 1.0, "l_toplam": 0, "oncekiler": []})
            aktif_h_carp = etki_data["h_carp"]
            aktif_l_sure = etki_data["l_toplam"]

            gelen_arac_sayisi, _ = hesapla_zincir_yogunlugu(aktif_id, serit_etkileri, canli_yogunluk_havuzu,
                                                            max_derinlik=3)
            gelen_arac_bonusu = gelen_arac_sayisi * ANTISIPASYON_SURE_CARPANI

            dinamik_bosluk_toleransi = BOSLUK_TOLERANSI
            if gelen_arac_sayisi > 2: dinamik_bosluk_toleransi = 4.0

            hesaplanan = (TABAN_YESIL_SURESI + aktif_l_sure) * aktif_h_carp + (
                    bolge_arac_sayilari[aktif_serit_idx] * ARAC_BASINA_EK_SURE) + gelen_arac_bonusu
            anlik_hedef_sure = hesaplanan * hedef_doluluk_carpani

            if anlik_hedef_sure > kilitli_max_sure: kilitli_max_sure = anlik_hedef_sure
            kilitli_max_sure = min(kilitli_max_sure, MUTLAK_MAKSIMUM_SURE)
            if bolge_arac_sayilari[aktif_serit_idx] > 0: son_dolu_zaman = su_an

            sure_doldu_mu = gecen_sure >= kilitli_max_sure
            bosluktan_tahliye_mi = (bolge_arac_sayilari[aktif_serit_idx] == 0) and (
                    (su_an - son_dolu_zaman) >= dinamik_bosluk_toleransi)
            diger_arac_var_mi = sum(bolge_arac_sayilari) - bolge_arac_sayilari[aktif_serit_idx] > 0

            if (sure_doldu_mu or bosluktan_tahliye_mi or hedef_tamamen_dolu) and diger_arac_var_mi:
                aktif_isik_durumu = "YELLOW"
                faz_baslangici = su_an

        sync_data = {
            "lanes": [],
            "acil_durum_var_mi": bool(acil_durum_seridi != -1),
            "arac_tipi": tespit_edilen_tip
        }

        for i, lane_id in enumerate(serit_idleri):
            if i in saf_cikislar:
                color = "#FFA500"
            else:
                color = "#00FF00" if (i == aktif_serit_idx and aktif_isik_durumu == "GREEN") else (
                    "#FFFF00" if i == aktif_serit_idx else "#FF0000")
            sync_data["lanes"].append({"id": lane_id, "color": color, "count": bolge_arac_sayilari[i]})
        try:
            sock.sendto(json.dumps(sync_data).encode('utf-8'), (UDP_IP, UDP_PORT))
        except:
            pass

        overlay = frame.copy()
        hovered_lane_idx = -1
        for i, pts in enumerate(np_polygons):
            if cv2.pointPolygonTest(pts, (float(mouse_hover_pos[0]), float(mouse_hover_pos[1])), False) >= 0:
                hovered_lane_idx = i
                break

        for i, pts in enumerate(np_polygons):
            if i in saf_cikislar:
                dolgu = (0, 165, 255)
            else:
                if i == aktif_serit_idx:
                    dolgu = (0, 255, 0) if aktif_isik_durumu == "GREEN" else (0, 255, 255)
                else:
                    dolgu = (0, 0, 255)

            alpha = 0.6 if i == hovered_lane_idx else 0.35
            temp_overlay = overlay.copy()
            cv2.fillPoly(temp_overlay, [pts], dolgu)
            cv2.addWeighted(temp_overlay, alpha, overlay, 1 - alpha, 0, overlay)
            cv2.polylines(overlay, [pts], True, dolgu, 2)

        for link_idx, (idx1, idx2) in enumerate(links):
            if hovered_lane_idx == idx1 or hovered_lane_idx == idx2:
                ok_rengi = OK_RENKLERI[idx2 % len(OK_RENKLERI)]
                cv2.arrowedLine(overlay, serit_merkezleri[idx1], serit_merkezleri[idx2], ok_rengi, 4, tipLength=0.06)

        for (box, s_idx, tip) in yolo_kutu_listesi:
            if s_idx == hovered_lane_idx and hovered_lane_idx != -1:
                renk = (0, 0, 255) if tip in ["AMBULANS", "ITFAIYE"] else (255, 255, 255)
                kutu_kalinlik = 3 if tip in ["AMBULANS", "ITFAIYE"] else 2
                cv2.rectangle(overlay, (box[0], box[1]), (box[2], box[3]), renk, kutu_kalinlik)
                yazi_boyutu = 0.5 if tip in ["AMBULANS", "ITFAIYE"] else 0.4
                yazi_kalinlik = 2 if tip in ["AMBULANS", "ITFAIYE"] else 1
                cv2.putText(overlay, tip, (box[0], max(10, box[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, yazi_boyutu, renk,
                            yazi_kalinlik)

        for i, pts in enumerate(np_polygons):
            if i not in saf_cikislar:
                if i == aktif_serit_idx and aktif_isik_durumu == "GREEN":
                    kalan = max(0, kilitli_max_sure - gecen_sure)
                    cv2.putText(overlay, f"{kalan:.1f}s", (serit_merkezleri[i][0] - 25, serit_merkezleri[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
                    cv2.putText(overlay, f"{kalan:.1f}s", (serit_merkezleri[i][0] - 25, serit_merkezleri[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                elif i == aktif_serit_idx and aktif_isik_durumu == "YELLOW":
                    kalan = max(0, SARI_ISIK_SURESI - gecen_sure)
                    cv2.putText(overlay, f"{kalan:.1f}s", (serit_merkezleri[i][0] - 25, serit_merkezleri[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
                    cv2.putText(overlay, f"{kalan:.1f}s", (serit_merkezleri[i][0] - 25, serit_merkezleri[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                else:
                    cv2.putText(overlay, "BEKLIYOR", (serit_merkezleri[i][0] - 40, serit_merkezleri[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
                    cv2.putText(overlay, "BEKLIYOR", (serit_merkezleri[i][0] - 40, serit_merkezleri[i][1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            if i == hovered_lane_idx:
                etki_data = serit_etkileri.get(serit_idleri[i],
                                               {"h_durum": "Güneşli", "h_carp": 1.0, "levhalar": [], "l_toplam": 0,
                                                "oncekiler": []})

                g_arac, zincir_detaylari = hesapla_zincir_yogunlugu(serit_idleri[i], serit_etkileri,
                                                                    canli_yogunluk_havuzu, max_derinlik=3)

                info_lines = [
                    f"ID: {serit_idleri[i]}",
                    f"Toplam Yogunluk: {bolge_arac_sayilari[i] + g_arac} Arac",
                    "-" * 30
                ]

                if acil_durum_seridi == i:
                    ikon = "🚑" if tespit_edilen_tip == "AMBULANS" else "🚒"
                    info_lines.append(f"{ikon} {tespit_edilen_tip} TESPITI: MUTLAK YESIL YANIYOR!")
                    info_lines.append("-" * 30)

                info_lines.append("🧮 HESAPLAMA OZETI:")
                info_lines.append(f"Taban: 5.0s | Levha: {etki_data['l_toplam']:+}s | Hava: x{etki_data['h_carp']}")
                info_lines.append(f"Kendi Araci ({bolge_arac_sayilari[i]}): +{bolge_arac_sayilari[i] * 2.0:.1f}s")

                if g_arac > 0:
                    info_lines.append(f"Zincir Trafik ({g_arac}): +{g_arac * 1.5:.1f}s")
                    for detay in zincir_detaylari:
                        info_lines.append(detay)
                else:
                    info_lines.append(f"Zincir Trafik (0): +0.0s")

                info_lines.append("-" * 30)

                hesaplanan = (TABAN_YESIL_SURESI + etki_data['l_toplam']) * etki_data['h_carp'] + (
                        bolge_arac_sayilari[i] * ARAC_BASINA_EK_SURE) + (g_arac * ANTISIPASYON_SURE_CARPANI)
                anlik_hedef_sure = hesaplanan * hedef_doluluk_carpani

                info_lines.append(f"= HEDEF SURE: {anlik_hedef_sure:.1f}s")
                if hedef_doluluk_carpani < 1.0:
                    info_lines.append(f"(Darbogaz Kapasite Nedeniyle %{int(hedef_doluluk_carpani * 100)} Uygulandi)")

                if i in saf_cikislar:
                    info_lines.append(f"Tip: CIKIS | Kapasite: {bolge_arac_sayilari[i]}/{HEDEF_SERIT_KAPASITESI}")
                else:
                    if i == aktif_serit_idx:
                        info_lines.append(f"Tip: GIRIS | Isik: {'YESIL' if aktif_isik_durumu == 'GREEN' else 'SARI'}")
                    else:
                        info_lines.append("Tip: GIRIS | Isik: KIRMIZI")

                draw_rich_hover_info(overlay, mouse_hover_pos[0] + 15, mouse_hover_pos[1] + 15, info_lines)

        cv2.imshow(window_title, overlay)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()