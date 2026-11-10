🚦 Smart Traffic Management System (Akıllı Trafik Yönetim ve SCADA Sistemi)

Bu proje, bilgisayarlı görü (YOLOv11), çevrimdışı (Air-Gapped) SCADA mimarisi, gömülü sistemler (STM32/Arduino) ve çapraz platform mobil uygulamayı bir araya getiren gerçek zamanlı (Real-Time) ve otonom bir kavşak yönetim sistemidir.

Sistem; araç yoğunluğunu yapay zeka ile sayarak trafik ışık sürelerini dinamik olarak optimize eder, donanımsal sensörlerden gelen meteorolojik verilere göre çevresel adaptasyon sağlar ve acil durum araçlarına (Ambulans, İtfaiye) mutlak geçiş üstünlüğü tanır.

🌟 Temel Özellikler

Otonom Yoğunluk Optimizasyonu: YOLOv11 modeli ile gerçek zamanlı araç (otomobil, otobüs, kamyon) tespiti ve şerit bazlı dinamik süre hesaplaması.

Mutlak Geçiş Üstünlüğü (Acil Durum): Ambulans ve İtfaiye tespit edildiğinde, ilgili şeride anında geçiş üstünlüğü verilir ve mobil uygulama/SCADA üzerinden siren/çakar alarmları tetiklenir.

Air-Gapped (Çevrimdışı) SCADA Paneli: C# WPF ve WebView2 mimarisiyle, internet bağlantısından tamamen izole çalışabilen Leaflet (MOBAC) tabanlı interaktif harita arayüzü.

Hardware-in-the-Loop (HIL) Simülasyonu: Wokwi sanal donanım ortamının Gölge DOM (Shadow DOM) yapısına Selenium ile sızılarak C++, C# ve Python sistemlerinin uçtan uca haberleştirilmesi.

Meteorolojik Çevresel Adaptasyon: DHT sensörlerinden gelen gerçek zamanlı sıcaklık ve nem verilerine göre kar/yağmur durumlarının tespiti ve ışık bekleme sürelerine "Hava Çarpanı" (Multiplier) uygulanması.

IoT Mobil Kokpit (React Native): Sürücüleri "Fermuar Sistemi" için uyaran, titreşim (haptik) ve sesli asistan (akustik) destekli gerçek zamanlı mobil navigasyon arayüzü.

🏗️ Mimari ve Teknoloji Yığını (Tech Stack)

🧠 Yapay Zeka ve Backend (Python)

YOLOv11 & PyTorch: Nesne tespiti, araç sayımı ve acil durum aracı sınıflandırması.

OpenCV: Görüntü işleme, çokgen (polygon) şerit çizimi ve hedef takibi.

Docker & Docker Compose: Platform bağımsız, izole "Konteyner" üretim ortamı (Production).

Selenium: Wokwi gömülü sistem terminallerinden veri kazıma (Scraping).

🖥️ SCADA ve Frontend (C# & JS)

C# WPF & WebView2: Windows masaüstü köprü yazılımı ve arayüz barındırma.

Leaflet JS & MOBAC: OSM (OpenStreetMap) çevrimdışı (Offline) harita entegrasyonu.

UDP Sockets & JSON: Saniyede 1 güncellenen asenkron ve kayıpsız veri transferi.

⚙️ Gömülü Sistemler ve Mobil (C++ & React Native)

STM32 / Arduino (C++): Fiziksel röle (trafik ışığı) kontrolü, I2C LCD ekran yönetimi ve DHT sensör okumaları.

React Native (Expo): Çapraz platform mobil arayüz.

Expo Location & Speech: Gerçek zamanlı GPS sensör füzyonu ve metin-ses (TTS) sentezleyici.

🚀 Kurulum ve Çalıştırma

Proje, hem gerçek dünya (Production) standartları için Docker ile hem de donanım simülasyonu (HIL) testleri için Selenium entegreli script ile iki farklı modda çalıştırılabilir.

1. Docker ile Otonom AI Modu (Production)

Yapay zeka ortamını kütüphane kurmadan çalıştırmak için:

# Docker imajını derleyin ve konteyneri ayaklandırın
docker-compose up


Bu komut, trafikIsigiKontrolSistemi.py dosyasını çalıştırarak C# klasörüne anlık canli_yogunluk.json verisini yazar.

2. Wokwi Donanım Simülasyonu Modu (HIL)

C# SCADA, Gömülü Sistemler ve Yapay Zekayı aynı anda test etmek için:

# Edge tarayıcısını ve Wokwi otomasyonunu başlatan test scripti
python trafikIsigiKontrolSistemi_2.py


Not: Bu mod için selenium ve webdriver_manager kütüphanelerinin yüklü olması gerekmektedir.

3. C# SCADA Panelini Başlatma

Visual Studio üzerinden projeyi Rebuild edin veya doğrudan MapApp.exe dosyasını çalıştırın. map.html ve YerelHarita dosyalarının çıktı dizininde (bin/Debug) olduğundan emin olun.

📅 Sürüm Geçmişi (Version History)

v1.1: Çevrimdışı (Offline) SCADA Harita entegrasyonu tamamlandı. Sistem dış ağlardan izole edildi.

v1.2: Docker altyapısı (Dockerfile & Compose) ve YOLO yapay zeka entegrasyonu eklendi.

v1.3: Wokwi donanım simülasyonu (HIL) ve Selenium test entegrasyonu için ikinci otonom script eklendi.

👨‍💻 Geliştirici

Ahmet AKARCA
Bilgisayar Mühendisi & Yazılım Mühendisi 