# Hafif ve hızlı bir Python 3.10 sürümü kullanıyoruz
FROM python:3.10-slim

# Docker'ın içindeki çalışma klasörümüz
WORKDIR /app

# Görüntü işleme (OpenCV) için gereken kritik Linux kütüphanelerini kuruyoruz
# YENİ STANDART: libgl1-mesa-glx yerine güncel olan libgl1 kullanıyoruz
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Kütüphane listesini kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# YOLO modellerini (yolo11n.pt, best.pt) ve Python kodumuzu içeri kopyala
COPY . .

# Konteyner çalıştığında yapacağı standart hiçbir şey yok, komutu docker-compose'dan vereceğiz.
CMD ["python", "--version"]