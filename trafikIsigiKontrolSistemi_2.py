import cv2
import numpy as np
import time
import os
import argparse
import socket
import json
import pyautogui
import re
from ultralytics import YOLO

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager

parser = argparse.ArgumentParser(description="Otonom Kamera Sureci (Backend Modu)")
parser.add_argument("--camera", type=str, default="KAMERA_1", help="Calistirilacak Kamera ID")
parser.add_argument("--video", type=str, default="4corner2.mp4", help="Islenecek Video")
parser.add_argument("--data_dir", type=str,
                    default=r"D:\pyTorch_egitimDosyalari\MapApp\MapApp\bin\Debug\net8.0-windows",
                    help="C# JSON klasoru")
args = parser.parse_args()

UDP_IP = "host.docker.internal"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

ACIL_TIP_ONCELIGI = ["YOK", "AMBULANS", "ITFAIYE", "YAKLASAN_ITFAIYE", "ITFAIYE_HAFIZASI"]


# =========================================================================
# WOKWI'NIN GÖLGE DOM (SHADOW DOM) AĞACINI DELİP GEÇEN ZIRHLI SINIF
# =========================================================================
class WokwiDinleyici:
    def __init__(self, proje_url):
        print("\n[SELENIUM] Wokwi arayuzu Microsoft Edge uzerinden baslatiliyor...")
        edge_options = Options()

        self.driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=edge_options)
        self.driver.get(proje_url)
        print("[SELENIUM] Wokwi Acildi! Lutfen Edge ekranindan PLAY butonuna bas.")
        time.sleep(5)

    def terminal_oku(self):
        try:
            js_script = """
            function extractTerminal(root) {
                if (!root) return '';
                if (root.classList && root.classList.contains('xterm-rows')) {
                    return root.innerText;
                }
                if (root.shadowRoot) {
                    let res = extractTerminal(root.shadowRoot);
                    if (res) return res;
                }
                if (root.children) {
                    for (let child of root.children) {
                        let res = extractTerminal(child);
                        if (res) return res;
                    }
                }
                return '';
            }
            var text = extractTerminal(document.body);
            if (!text || text.trim() === '') {
                text = document.body.innerText;
            }
            return text;
            """
            js_text = self.driver.execute_script(js_script)

            if js_text and len(js_text.strip()) > 0:
                tum_satirlar = js_text.split('\n')
                return [s.strip() for s in tum_satirlar[-30:] if s.strip() != ""]
            return []
        except:
            return []


def hesapla_zincir_durumu(baslangic_id, etki_sozlugu, canli_durum_havuzu, max_derinlik=3, visited=None):
    if visited is None: visited = set()
    toplam_gelen_arac = 0
    en_oncelikli_acil_tipi = "YOK"
    detaylar = []

    if not isinstance(canli_durum_havuzu, dict): canli_durum_havuzu = {}
    oncekiler = etki_sozlugu.get(baslangic_id, {}).get("oncekiler", [])
    if not isinstance(oncekiler, list): oncekiler = []

    for oid in oncekiler:
        if oid not in visited:
            visited.add(oid)
            gelen_detay = canli_durum_havuzu.get(oid)
            if not isinstance(gelen_detay, dict): gelen_detay = {}

            arac = gelen_detay.get("count", 0)
            if not isinstance(arac, (int, float)): arac = 0

            zincir_acil = gelen_detay.get("emergency_type", "YOK")
            if zincir_acil not in ACIL_TIP_ONCELIGI: zincir_acil = "YOK"

            toplam_gelen_arac += arac
            if ACIL_TIP_ONCELIGI.index(zincir_acil) > ACIL_TIP_ONCELIGI.index(en_oncelikli_acil_tipi):
                en_oncelikli_acil_tipi = zincir_acil

            if max_derinlik > 1:
                alt_toplam_arac, alt_acil_tipi, _ = hesapla_zincir_durumu(oid, etki_sozlugu, canli_durum_havuzu,
                                                                          max_derinlik - 1, visited)
                toplam_gelen_arac += alt_toplam_arac
                if ACIL_TIP_ONCELIGI.index(alt_acil_tipi) > ACIL_TIP_ONCELIGI.index(en_oncelikli_acil_tipi):
                    en_oncelikli_acil_tipi = alt_acil_tipi

    return toplam_gelen_arac, en_oncelikli_acil_tipi, detaylar


def main():
    video_path = args.video
    target_camera_id = args.camera

    # ⚠️ KENDİ WOKWI LİNKİNİ BURAYA YAPIŞTIRMAYI UNUTMA!
    wokwi_dinleyici = WokwiDinleyici("https://wokwi.com/projects/472270602733740033")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"\n[KRITIK HATA] {target_camera_id} BASLATILAMADI!")
        time.sleep(15)
        return

    # ==============================================================================================
    # TAM DOSYA YOLLARI
    # ==============================================================================================
    poly_file = os.path.join(args.data_dir, f"{target_camera_id}_polygons.json")
    canli_yogunluk_yolu = r"D:\pyTorch_egitimDosyalari\MapApp\MapApp\bin\Debug\net8.0-windows\canli_yogunluk.json"
    json_yolu = r"D:\pyTorch_egitimDosyalari\MapApp\MapApp\bin\Debug\net8.0-windows\seritler.json"
    # ==============================================================================================

    while True:
        if not os.path.exists(poly_file):
            time.sleep(2)
            continue
        try:
            with open(poly_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
                if not isinstance(saved_data, dict): saved_data = {}
                polygons_data = saved_data.get("polygons", [])
                if not isinstance(polygons_data, list): polygons_data = []
            if len(polygons_data) > 0: break
        except:
            pass
        time.sleep(2)

    np_polygons = [np.array(p["points"], np.int32) for p in polygons_data if isinstance(p, dict) and "points" in p]
    serit_idleri = [p.get("id", f"LANE_{i}") for i, p in enumerate(polygons_data) if isinstance(p, dict)]

    model_trafik = YOLO("yolo11s.pt")
    model_acil_durum = YOLO("best.pt")
    print(f"[{target_camera_id}] HIBRIT OTONOM SISTEM AKTIF!")

    aktif_serit_idx = 0
    aktif_isik_durumu = "GREEN"

    TABAN_YESIL_SURESI = 5.0
    ARAC_BASINA_EK_SURE = 2.0
    ANTISIPASYON_SURE_CARPANI = 1.5
    MUTLAK_MAKSIMUM_SURE = 40.0
    SARI_ISIK_SURESI = 3.0
    HEDEF_SERIT_KAPASITESI = 6
    BOSLUK_TOLERANSI = 2.0

    kilitli_max_sure = TABAN_YESIL_SURESI
    frame_count = 0
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30.0
    frame_delay = 1.0 / fps

    zaman = time.time()
    faz_baslangici = zaman
    son_dolu_zaman = zaman

    harita_ayarlari = []
    serit_etkileri = {}
    canli_durum_havuzu = {}

    ACIL_HAFIZA_SURESI = 5.0
    son_bizzat_gorulen_acil_id = None
    son_bizzat_acil_zamani = 0

    son_scada_durumu = "NORMAL"
    son_gonderilen_yogunluk = ""
    son_scada_isik = ""
    son_scada_sure = 0

    canli_sicaklik = 25
    canli_nem = 50
    son_kaydedilen_hava_durumu = ""

    while True:
        try:
            loop_start_time = time.time()

            # =================================================================
            # 1. SELENIUM ILE WOKWI'DEN CANLI VERI CEKME VE DETAYLI YAZMA
            # =================================================================
            okunan_satirlar = wokwi_dinleyici.terminal_oku()
            for satir in okunan_satirlar:
                if "YAYA_BUTON_AKTIF" in satir:
                    print("\n[SCADA DIKKAT] Yayalar gecide giris yapti! Guvenlik acildi.")
                elif "HAVA" in satir:
                    try:
                        match = re.search(r'HAVA:?\s*(-?\d+)\s*,\s*(\d+)', satir)
                        if match:
                            canli_sicaklik = int(match.group(1))
                            canli_nem = int(match.group(2))

                            print(f"[METEOROLOJI] Sicaklik: {canli_sicaklik}C, Nem: %{canli_nem}")

                            # HAVA DURUMU KÖK İKONU BELİRLEME
                            durum_ikon = "☀️ Güneşli"
                            if canli_sicaklik <= 4:
                                durum_ikon = "❄️ Karlı"
                            elif canli_nem >= 80:
                                durum_ikon = "🌧️ Yağmurlu"

                            # JSON'A YAZILACAK TELEMETRİ METNİNİ OLUŞTUR (Örn: ❄️ Karlı (-2°C, %50 Nem))
                            guncel_hava_metni = f"{durum_ikon} ({canli_sicaklik}°C, %{canli_nem} Nem)"

                            if guncel_hava_metni != son_kaydedilen_hava_durumu:
                                try:
                                    if os.path.exists(json_yolu):
                                        with open(json_yolu, "r", encoding="utf-8") as f:
                                            serit_datalari = json.load(f)

                                        if isinstance(serit_datalari, list):
                                            for s in serit_datalari:
                                                s["HavaDurumu"] = guncel_hava_metni

                                        with open(json_yolu, "w", encoding="utf-8") as f:
                                            json.dump(serit_datalari, f, ensure_ascii=False, indent=2)

                                        print(
                                            f"[SISTEM GUNCELLEMESI] seritler.json '{guncel_hava_metni}' olarak kaydedildi!")
                                        son_kaydedilen_hava_durumu = guncel_hava_metni
                                except Exception as e:
                                    print(f"[JSON YAZMA HATASI] Dosya mesgul olabilir: {e}")
                    except Exception as parse_hata:
                        pass
            # =================================================================

            if not cap.grab():
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_count = 0
                continue

            frame_count += 1
            if frame_count % 5 != 0:
                elapsed = time.time() - loop_start_time
                if elapsed < frame_delay: time.sleep(frame_delay - elapsed)
                continue

            ret, frame = cap.retrieve()
            if not ret: continue

            frame = cv2.resize(frame, (1024, 768))
            zaman = time.time()

            if frame_count % 30 == 0:
                try:
                    if os.path.exists(poly_file):
                        with open(poly_file, "r", encoding="utf-8") as f:
                            guncel_poly_data = json.load(f)
                            if not isinstance(guncel_poly_data, dict): guncel_poly_data = {}
                            yeni_polygons = guncel_poly_data.get("polygons", [])
                            if not isinstance(yeni_polygons, list): yeni_polygons = []

                        if len(yeni_polygons) > 0:
                            yeni_id_listesi = [p.get("id", f"LANE_{i}") for i, p in enumerate(yeni_polygons) if
                                               isinstance(p, dict)]
                            if serit_idleri != yeni_id_listesi:
                                polygons_data = [p for p in yeni_polygons if isinstance(p, dict) and "points" in p]
                                np_polygons = [np.array(p["points"], np.int32) for p in polygons_data]
                                serit_idleri = [p.get("id", f"LANE_{i}") for i, p in enumerate(polygons_data)]
                                aktif_serit_idx = 0
                                aktif_isik_durumu = "GREEN"
                                faz_baslangici = zaman
                                son_dolu_zaman = zaman
                except:
                    pass

                try:
                    if os.path.exists(json_yolu):
                        with open(json_yolu, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list): harita_ayarlari = data
                except:
                    pass

                if not isinstance(harita_ayarlari, list): harita_ayarlari = []
                try:
                    if os.path.exists(canli_yogunluk_yolu):
                        with open(canli_yogunluk_yolu, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, dict): canli_durum_havuzu = data
                except:
                    pass

                if not isinstance(canli_durum_havuzu, dict): canli_durum_havuzu = {}

                for ayar in harita_ayarlari:
                    if not isinstance(ayar, dict): continue

                    s_id = ayar.get("Id", "")

                    h_carp = 1.0
                    h_durum = "Güneşli"

                    if canli_sicaklik <= 4:
                        h_carp = 1.5
                        h_durum = "Karlı"
                    elif canli_nem >= 80:
                        h_carp = 1.2
                        h_durum = "Yağmurlu"

                    levhalar = ayar.get("Levhalar", [])
                    if not isinstance(levhalar, list): levhalar = []
                    l_toplam = sum([lev.get("Sure", 0) for lev in levhalar if isinstance(lev, dict)])

                    o_list = ayar.get("OncekiSeritler", [])
                    s_list = ayar.get("SonrakiSeritler", [])

                    serit_etkileri[s_id] = {
                        "h_durum": h_durum, "h_carp": h_carp, "l_toplam": l_toplam,
                        "oncekiler": o_list, "sonrakiler": s_list
                    }

            if len(np_polygons) == 0: continue

            bolge_arac_sayilari = [0] * len(np_polygons)
            serit_acil_durum_tipleri = ["YOK"] * len(np_polygons)
            yolo_kutu_listesi = []

            results_trafik = model_trafik.track(frame, persist=True, classes=[2, 3, 5, 7], device="cpu",
                                                tracker="bytetrack.yaml", verbose=False, imgsz=800, conf=0.15)
            for r in results_trafik:
                if r.boxes.id is not None:
                    boxes = r.boxes.xyxy.cpu().numpy().astype(int)
                    for box in boxes:
                        cx, cy = (box[0] + box[2]) // 2, box[3]
                        bulunan_serit = -1
                        for i, pts in enumerate(np_polygons):
                            if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                                bolge_arac_sayilari[i] += 1
                                bulunan_serit = i
                                break
                        yolo_kutu_listesi.append((box, bulunan_serit, "YOLO"))

            bizzat_görülen_acil_seridi = -1
            results_acil = model_acil_durum.predict(frame, device="cpu", verbose=False, imgsz=640, conf=0.65)
            for r in results_acil:
                if len(r.boxes) > 0:
                    boxes = r.boxes.xyxy.cpu().numpy().astype(int)
                    classes = r.boxes.cls.cpu().numpy().astype(int)
                    for box, cls_id in zip(boxes, classes):
                        cx, cy = (box[0] + box[2]) // 2, box[3]
                        for i, pts in enumerate(np_polygons):
                            if cv2.pointPolygonTest(pts, (float(cx), float(cy)), False) >= 0:
                                bizzat_görülen_acil_seridi = i
                                bizzat_tip = "AMBULANS" if cls_id == 0 else "ITFAIYE"
                                serit_acil_durum_tipleri[i] = bizzat_tip
                                yolo_kutu_listesi.append((box, i, bizzat_tip))
                                break

            if bizzat_görülen_acil_seridi != -1:
                son_bizzat_gorulen_acil_id = serit_idleri[
                    bizzat_görülen_acil_seridi] if bizzat_görülen_acil_seridi < len(serit_idleri) else None
                son_bizzat_acil_zamani = zaman

            acil_durum_var_mi_bu_frame = (bizzat_görülen_acil_seridi != -1)
            kamera_acil_tipi = "YOK"
            if acil_durum_var_mi_bu_frame and bizzat_görülen_acil_seridi < len(serit_acil_durum_tipleri):
                kamera_acil_tipi = serit_acil_durum_tipleri[bizzat_görülen_acil_seridi]

            if bizzat_görülen_acil_seridi == -1 and son_bizzat_gorulen_acil_id is not None:
                if (zaman - son_bizzat_acil_zamani) < ACIL_HAFIZA_SURESI:
                    if son_bizzat_gorulen_acil_id in serit_idleri:
                        bizzat_görülen_acil_seridi = serit_idleri.index(son_bizzat_gorulen_acil_id)
                        kamera_acil_tipi = "ITFAIYE_HAFIZASI"
                else:
                    son_bizzat_gorulen_acil_id = None

            try:
                canli_yogunluk_dict = {}
                if os.path.exists(canli_yogunluk_yolu):
                    with open(canli_yogunluk_yolu, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict): canli_yogunluk_dict = data

                for i, lane_id in enumerate(serit_idleri):
                    if i >= len(serit_acil_durum_tipleri): break
                    s_tipi = serit_acil_durum_tipleri[i]
                    if s_tipi == "YOK" and i == bizzat_görülen_acil_seridi:
                        s_tipi = "ITFAIYE_HAFIZASI"
                    canli_yogunluk_dict[lane_id] = {"count": bolge_arac_sayilari[i], "emergency_type": s_tipi}

                with open(canli_yogunluk_yolu, "w", encoding="utf-8") as f:
                    json.dump(canli_yogunluk_dict, f, ensure_ascii=False)
            except:
                pass

            hedef_acil_durum_seridi = bizzat_görülen_acil_seridi
            tespit_edilen_tip = kamera_acil_tipi

            if bizzat_görülen_acil_seridi == -1 and len(canli_durum_havuzu) > 0:
                for i, lane_id in enumerate(serit_idleri):
                    zincir_toplam_arac, zincir_acil_tipi, _ = hesapla_zincir_durumu(lane_id, serit_etkileri,
                                                                                    canli_durum_havuzu, max_derinlik=3)
                    if zincir_acil_tipi != "YOK":
                        hedef_acil_durum_seridi = i
                        tespit_edilen_tip = "YAKLASAN_" + zincir_acil_tipi
                        break

            if hedef_acil_durum_seridi != -1:
                if son_scada_durumu != "AMBULANS":
                    pyautogui.write('AMBULANS_VAR\n')
                    print("\n[SCADA GONDERILDI] -> AMBULANS_VAR (Acil Durum Protokolu Aktif!)")
                    son_scada_durumu = "AMBULANS"
            else:
                if son_scada_durumu != "NORMAL":
                    son_scada_durumu = "NORMAL"
                    son_gonderilen_yogunluk = ""
                    son_scada_isik = ""

            if son_scada_durumu == "NORMAL":
                toplam_arac = sum(bolge_arac_sayilari)
                if toplam_arac == 0:
                    guncel_yogunluk = "BOS"
                elif toplam_arac <= 3:
                    guncel_yogunluk = "AZ"
                elif toplam_arac <= 7:
                    guncel_yogunluk = "ORTA"
                else:
                    guncel_yogunluk = "YUKSEK"

                if guncel_yogunluk != son_gonderilen_yogunluk:
                    pyautogui.write(f'YOG:{guncel_yogunluk}\n')
                    print(f"[SCADA GONDERILDI] -> YOG:{guncel_yogunluk} (Trafik Yogunlugu Guncellendi)")
                    son_gonderilen_yogunluk = guncel_yogunluk

                guncel_isik = aktif_isik_durumu
                guncel_sure = int(kilitli_max_sure)

                if (guncel_isik != son_scada_isik) or (guncel_sure != son_scada_sure):
                    isik_kod = "G" if guncel_isik == "GREEN" else "Y"
                    pyautogui.write(f'TRF:{isik_kod}:{guncel_sure}\n')
                    print(f"[SCADA GONDERILDI] -> TRF:{isik_kod}:{guncel_sure} (Yeni Trafik Suresi)")
                    son_scada_isik = guncel_isik
                    son_scada_sure = guncel_sure

            hedef_doluluk_carpani = 1.0
            hedef_tamamen_dolu = False

            if aktif_serit_idx >= len(serit_idleri): aktif_serit_idx = 0
            aktif_id = serit_idleri[aktif_serit_idx] if len(serit_idleri) > 0 else ""

            bagli_hedef_idleri = serit_etkileri.get(aktif_id, {}).get("sonrakiler", [])
            bagli_hedef_seritler = [serit_idleri.index(bid) for bid in bagli_hedef_idleri if bid in serit_idleri]

            if len(bagli_hedef_seritler) > 0:
                en_dolu_hedef_sayisi = max(
                    [bolge_arac_sayilari[h] for h in bagli_hedef_seritler if h < len(bolge_arac_sayilari)])
                if en_dolu_hedef_sayisi >= HEDEF_SERIT_KAPASITESI:
                    hedef_tamamen_dolu = True
                elif en_dolu_hedef_sayisi >= (HEDEF_SERIT_KAPASITESI - 2):
                    hedef_doluluk_carpani = 0.5

            acil_gecis_durumunda_mi = False
            if hedef_acil_durum_seridi != -1:
                if aktif_serit_idx != hedef_acil_durum_seridi:
                    acil_gecis_durumunda_mi = True
                    if aktif_isik_durumu == "GREEN":
                        aktif_isik_durumu = "YELLOW"
                        faz_baslangici = zaman
                        kilitli_max_sure = SARI_ISIK_SURESI
                else:
                    aktif_isik_durumu = "GREEN"
                    faz_baslangici = zaman
                    kilitli_max_sure = 25.0
                    hedef_tamamen_dolu = False

            gecen_sure = zaman - faz_baslangici

            if aktif_isik_durumu == "YELLOW":
                if gecen_sure >= SARI_ISIK_SURESI:
                    if hedef_acil_durum_seridi != -1:
                        sonraki = hedef_acil_durum_seridi
                    else:
                        sonraki = (aktif_serit_idx + 1) % len(np_polygons)
                        denenen = 0
                        while denenen < len(np_polygons):
                            if sonraki >= len(serit_idleri): sonraki = 0
                            aday_id = serit_idleri[sonraki]
                            aday_hedefler_idleri = serit_etkileri.get(aday_id, {}).get("sonrakiler", [])
                            if not isinstance(aday_hedefler_idleri, list): aday_hedefler_idleri = []
                            aday_hedefler = [serit_idleri.index(bid) for bid in aday_hedefler_idleri if
                                             bid in serit_idleri]
                            aday_hedef_dolu = False
                            for ah in aday_hedefler:
                                if ah < len(bolge_arac_sayilari) and bolge_arac_sayilari[ah] >= HEDEF_SERIT_KAPASITESI:
                                    aday_hedef_dolu = True
                            if not aday_hedef_dolu: break
                            sonraki = (sonraki + 1) % len(np_polygons)
                            denenen += 1

                    aktif_serit_idx = sonraki
                    aktif_isik_durumu = "GREEN"
                    faz_baslangici = zaman
                    son_dolu_zaman = zaman
                    kilitli_max_sure = 25.0 if hedef_acil_durum_seridi != -1 else TABAN_YESIL_SURESI

            elif aktif_isik_durumu == "GREEN":
                etki_data = serit_etkileri.get(aktif_id, {"h_carp": 1.0, "l_toplam": 0, "oncekiler": []})
                zincir_toplam_arac, _, _ = hesapla_zincir_durumu(aktif_id, serit_etkileri, canli_durum_havuzu,
                                                                 max_derinlik=3)
                gelen_arac_bonusu = zincir_toplam_arac * ANTISIPASYON_SURE_CARPANI
                dinamik_bosluk_toleransi = 4.0 if zincir_toplam_arac > 2 else BOSLUK_TOLERANSI

                aktif_arac_sayisi = bolge_arac_sayilari[aktif_serit_idx] if aktif_serit_idx < len(
                    bolge_arac_sayilari) else 0

                hesaplanan = (TABAN_YESIL_SURESI + etki_data["l_toplam"]) * etki_data["h_carp"] + (
                            aktif_arac_sayisi * ARAC_BASINA_EK_SURE) + gelen_arac_bonusu
                anlik_hedef_sure = hesaplanan * hedef_doluluk_carpani

                if anlik_hedef_sure > kilitli_max_sure: kilitli_max_sure = anlik_hedef_sure
                kilitli_max_sure = min(kilitli_max_sure, MUTLAK_MAKSIMUM_SURE)

                if aktif_arac_sayisi > 0: son_dolu_zaman = zaman
                sure_doldu_mu = gecen_sure >= kilitli_max_sure
                bosluktan_tahliye_mi = (aktif_arac_sayisi == 0) and (
                            (zaman - son_dolu_zaman) >= dinamik_bosluk_toleransi)

                if hedef_acil_durum_seridi != -1:
                    sure_doldu_mu = False
                    bosluktan_tahliye_mi = False
                    hedef_tamamen_dolu = False

                if (sure_doldu_mu or bosluktan_tahliye_mi or hedef_tamamen_dolu) and not acil_gecis_durumunda_mi:
                    aktif_isik_durumu = "YELLOW"
                    faz_baslangici = zaman
                    kilitli_max_sure = SARI_ISIK_SURESI

            sync_data = {
                "camera_id": target_camera_id,
                "frame_count": frame_count,
                "lanes": [], "boxes": [],
                "acil_durum_var_mi": bool(hedef_acil_durum_seridi != -1),
                "arac_tipi": tespit_edilen_tip
            }

            max_len = max(len(serit_idleri), len(np_polygons))
            lane_colors_dict = {}
            lane_vehicles = {i: [] for i in range(max_len)}

            for (box, s_idx, tip) in yolo_kutu_listesi:
                if s_idx != -1 and s_idx < max_len: lane_vehicles[s_idx].append(tip)

            if hedef_acil_durum_seridi != -1 and bizzat_görülen_acil_seridi == -1:
                if hedef_acil_durum_seridi < max_len:
                    lane_vehicles[hedef_acil_durum_seridi].append(tespit_edilen_tip)

            for i, lane_id in enumerate(serit_idleri):
                if hedef_acil_durum_seridi != -1 and not acil_gecis_durumunda_mi:
                    color = "#00FF00" if i == hedef_acil_durum_seridi else "#FF0000"
                    kalan_sure = max(0.0, kilitli_max_sure - gecen_sure) if i == hedef_acil_durum_seridi else 0.0
                else:
                    color = "#00FF00" if (i == aktif_serit_idx and aktif_isik_durumu == "GREEN") else (
                        "#FFFF00" if i == aktif_serit_idx else "#FF0000")
                    kalan_sure = max(0.0, kilitli_max_sure - gecen_sure) if (i == aktif_serit_idx) else 0.0

                lane_colors_dict[i] = color
                sync_data["lanes"].append({
                    "id": lane_id,
                    "color": color,
                    "count": bolge_arac_sayilari[i] if i < len(bolge_arac_sayilari) else 0,
                    "vehicles": lane_vehicles[i] if i < max_len else [],
                    "kalan_sure": round(kalan_sure, 1)
                })

            for (box, s_idx, tip) in yolo_kutu_listesi:
                b_color = lane_colors_dict.get(s_idx, "#FFFFFF")
                sync_data["boxes"].append(
                    {"coords": [int(box[0]), int(box[1]), int(box[2]), int(box[3])], "cls": tip, "color": b_color})

            try:
                sock.sendto(json.dumps(sync_data).encode('utf-8'), (UDP_IP, UDP_PORT))
            except:
                pass

            elapsed = time.time() - loop_start_time
            if elapsed < frame_delay: time.sleep(frame_delay - elapsed)

        except Exception as e:
            pass

    cap.release()


if __name__ == "__main__":
    main()