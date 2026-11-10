import * as Location from 'expo-location';
import * as Speech from 'expo-speech';
import { useEffect, useRef, useState } from 'react';
import { Keyboard, StyleSheet, Text, TextInput, TouchableOpacity, Vibration, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { WebView } from 'react-native-webview';

export default function Index() {
  const webviewRef = useRef<WebView>(null);
  
  // HAFIZA ÇİPİ (React'in kafasının karışmasını engeller)
  const acilDurumHafizasi = useRef(false); 

  const [rotaBilgisi, setRotaBilgisi] = useState({ mesafe: '0.0', dakika: '0' });
  const [hedefSecildi, setHedefSecildi] = useState(false);
  const [aramaMetni, setAramaMetni] = useState('');
  const [pusulaAcisi, setPusulaAcisi] = useState(0);
  const [acilDurum, setAcilDurum] = useState(false); 

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;

      await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.High, timeInterval: 1000, distanceInterval: 1 },
        (location) => {
          const lat = location.coords.latitude;
          const lon = location.coords.longitude;
          if (webviewRef.current) {
            webviewRef.current.injectJavaScript(`GpsGuncelle(${lat}, ${lon}); true;`);
          }
        }
      );

      await Location.watchHeadingAsync((headingObj) => {
        const aci = headingObj.trueHeading >= 0 ? headingObj.trueHeading : headingObj.magHeading;
        if (aci >= 0) {
          setPusulaAcisi(Math.round(aci)); 
          if (webviewRef.current) {
            webviewRef.current.injectJavaScript(`
              if(typeof window.YumusatilmisDondur === 'function') {
                  window.YumusatilmisDondur(${aci});
              }
              true;
            `);
          }
        }
      });
    })();
  }, []);

  const onMessage = (event: any) => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.tip === "ROTA_BILGISI") {
        setRotaBilgisi({ mesafe: data.mesafe, dakika: data.dakika });
        setHedefSecildi(true);
        
        // 🚨 KOKPİT ALARM SİSTEMİ TETİKLEYİCİSİ
        if (data.acilDurum === true && acilDurumHafizasi.current === false) {
            acilDurumHafizasi.current = true; 
            setAcilDurum(true); 
            
            // 1. AŞAMA: TİTREŞİM (Toplam 2.2 saniye sürecek)
            Vibration.vibrate([0, 600, 200, 600, 200, 600]); 
            
            // 2. AŞAMA: SESLİ UYARI (Titreşim tamamen bittikten 2.5 saniye sonra devreye girer)
            setTimeout(() => {
              Speech.speak("Dikkat! Ambulans yaklaşıyor. Lütfen fermuar sistemi uygulayarak yol verin.", {
                language: 'tr-TR', 
                rate: 0.9,         
                pitch: 1.1         
              });
            }, 2500); 
            
        } else if (data.acilDurum === false && acilDurumHafizasi.current === true) {
            // Tehlike geçtiğinde sistemi sıfırla
            acilDurumHafizasi.current = false;
            setAcilDurum(false);
            Speech.stop(); // Eğer konuşma bitmediyse hemen sustur
        }
      }
    } catch (error) {}
  };

  const adresAra = async () => {
    if (aramaMetni.length < 3) return;
    Keyboard.dismiss();
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${aramaMetni}&limit=1`);
      const data = await response.json();
      if (data && data.length > 0) {
        const lat = data[0].lat;
        const lon = data[0].lon;
        webviewRef.current?.injectJavaScript(`DistanHedefBelirle(${lat}, ${lon}); true;`);
      } else {
        alert("Adres bulunamadı, lütfen daha detaylı yazın.");
      }
    } catch (err) {
      console.log("Arama hatası: ", err);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      
      <View style={styles.radarContainer}>
        <Text style={styles.radarText}>Sensör Açısı: {pusulaAcisi}°</Text>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Cadde, sokak veya mekan arayın..."
          placeholderTextColor="#8e8e93"
          value={aramaMetni}
          onChangeText={setAramaMetni}
          onSubmitEditing={adresAra}
        />
        <TouchableOpacity style={styles.searchButton} onPress={adresAra}>
          <Text style={styles.searchButtonText}>Ara</Text>
        </TouchableOpacity>
      </View>

      <WebView 
        ref={webviewRef}
        style={styles.map} 
        source={{ uri: 'https://1ef8-88-240-170-16.ngrok-free.app' }} /* NGROK LINKIN */
        onMessage={onMessage} 
        javaScriptEnabled={true}
        domStorageEnabled={true}
        scrollEnabled={false} 
        bounces={false}
        overScrollMode="never"
        scalesPageToFit={false}
        setBuiltInZoomControls={false} 
      />
      
      {/* 🚨 DİNAMİK ALT PANEL (Fermuar Sistemi Yazısı Eklendi) */}
      {hedefSecildi && (
        <View style={styles.panel}>
          <View style={styles.panelRow}>
            <Text style={[styles.timeText, acilDurum && { color: '#ff453a' }]}>
              <Text style={styles.timeNumber}>{rotaBilgisi.dakika}</Text> dk
            </Text>
            <Text style={styles.distanceText}>({rotaBilgisi.mesafe} km)</Text>
          </View>
          
          {/* Acil duruma göre değişen ve büyüyen devasa uyarı metni */}
          <Text style={[styles.etaText, acilDurum && styles.emergencyText]}>
            {acilDurum 
              ? "🚨 GEÇİŞ ÜSTÜNLÜĞÜ\nLÜTFEN FERMUAR SİSTEMİ UYGULAYIN!" 
              : "Yapay Zeka & Şerit Destekli Tahmini Süre"}
          </Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#1c1c1e' },
  map: { flex: 1 },
  radarContainer: { position: 'absolute', top: 10, left: 20, zIndex: 99, backgroundColor: 'rgba(255, 38, 0, 0.8)', padding: 5, borderRadius: 8 },
  radarText: { color: 'white', fontWeight: 'bold' },
  searchContainer: { position: 'absolute', top: 50, left: 20, right: 20, zIndex: 10, flexDirection: 'row', backgroundColor: '#2c2c2e', borderRadius: 12, shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 5, elevation: 5 },
  searchInput: { flex: 1, color: '#fff', paddingHorizontal: 15, paddingVertical: 12, fontSize: 16 },
  searchButton: { backgroundColor: '#0a84ff', paddingHorizontal: 20, justifyContent: 'center', borderTopRightRadius: 12, borderBottomRightRadius: 12 },
  searchButtonText: { color: '#fff', fontWeight: 'bold' },
  
  panel: { backgroundColor: '#2c2c2e', padding: 20, borderTopLeftRadius: 20, borderTopRightRadius: 20 },
  panelRow: { flexDirection: 'row', alignItems: 'baseline', marginBottom: 5 },
  timeText: { color: '#32d74b', fontSize: 24, fontWeight: 'bold' },
  timeNumber: { fontSize: 36, fontWeight: '900' },
  distanceText: { color: '#8e8e93', fontSize: 18, marginLeft: 10, fontWeight: '600' },
  etaText: { color: '#0a84ff', fontSize: 14, fontWeight: '500' },
  
  // 🚨 YENİ: Ekranda beliren acil durum uyarı tasarımı (Büyük, kalın ve çok satırlı)
  emergencyText: {
    color: '#ff453a',
    fontSize: 18,
    fontWeight: '900',
    marginTop: 8,
    lineHeight: 24,
    textAlign: 'center',
    textShadowColor: 'rgba(255, 69, 58, 0.3)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 4
  }
});