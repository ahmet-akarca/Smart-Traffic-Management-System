using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Windows;
using Microsoft.Web.WebView2.Core;

namespace MapApp
{
    public class NoktaModel
    {
        public double lat { get; set; }
        public double lng { get; set; }
    }

    public class LevhaModel
    {
        public string Ikon { get; set; } = string.Empty;
        public string Ad { get; set; } = string.Empty;
        public int Sure { get; set; } = 0;
    }

    public class AdresModel
    {
        public string Il { get; set; } = string.Empty;
        public string Ilce { get; set; } = string.Empty;
        public string Mahalle { get; set; } = string.Empty;
        public string Cadde { get; set; } = string.Empty;
        public string Sokak { get; set; } = string.Empty;
        public string BinaNo { get; set; } = string.Empty;
    }

    public class SeritModel
    {
        public string Id { get; set; } = string.Empty;
        public string KameraId { get; set; } = "KAMERA_1";
        public string Isim { get; set; } = string.Empty;
        public int IsikModu { get; set; } = 0;
        public string HavaDurumu { get; set; } = "☀️ Güneşli";
        public List<LevhaModel> Levhalar { get; set; } = new List<LevhaModel>();
        public List<NoktaModel> Noktalar { get; set; } = new List<NoktaModel>();
        public AdresModel Adres { get; set; } = new AdresModel();
        public List<string> OncekiSeritler { get; set; } = new List<string>();
        public List<string> SonrakiSeritler { get; set; } = new List<string>();
    }

    public partial class MainWindow : Window
    {
        private string veriDosyasiYolu = "seritler.json";
        private string canliYogunlukDosyaYolu = "canli_yogunluk.json";
        private List<string> aktifSeritIdListesi = new List<string>();
        private Dictionary<string, Process> aktifPythonSurecleri = new Dictionary<string, Process>();

        private Dictionary<string, int> anlikYogunlukHaritasi = new Dictionary<string, int>();
        private readonly object yogunlukLock = new object();

        // --- YENİ EKLENEN: Python'un çökme/kapanma durumunu takip eden sayaç ---
        private DateTime sonGuncellemeZamani = DateTime.Now;

        public MainWindow()
        {
            InitializeComponent();
            InitializeWebView();
            BaslatCanliVeriDinleyici();
            BaslatYogunlukKaydedici();
            this.Closing += MainWindow_Closing;
        }

        private async void InitializeWebView()
        {
            await webView.EnsureCoreWebView2Async(null);
            webView.CoreWebView2.WebMessageReceived += OnWebMessageReceived;
            webView.CoreWebView2.NavigationCompleted += CoreWebView2_NavigationCompleted;

            string htmlPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "map.html");
            webView.CoreWebView2.Settings.AreDevToolsEnabled = true;
            webView.CoreWebView2.Navigate($"file:///{htmlPath}");
        }

        private async void CoreWebView2_NavigationCompleted(object? sender, CoreWebView2NavigationCompletedEventArgs e)
        {
            if (File.Exists(veriDosyasiYolu))
            {
                string jsonVeri = File.ReadAllText(veriDosyasiYolu);
                var kayitliSeritler = JsonSerializer.Deserialize<List<SeritModel>>(jsonVeri);
                if (kayitliSeritler != null)
                {
                    foreach (var serit in kayitliSeritler)
                    {
                        if (!aktifSeritIdListesi.Contains(serit.Id))
                        {
                            aktifSeritIdListesi.Add(serit.Id);
                        }
                    }
                    PythonSurecleriniYonet(kayitliSeritler);
                }
                string jsKomutu = $"TopluSeritYukle({jsonVeri});";
                await webView.CoreWebView2.ExecuteScriptAsync(jsKomutu);
            }
        }

        private void PythonSurecleriniYonet(List<SeritModel> seritler)
        {
            var benzersizKameralar = seritler.Select(s => s.KameraId).Distinct().ToList();

            foreach (var kameraId in benzersizKameralar)
            {
                if (!aktifPythonSurecleri.ContainsKey(kameraId))
                {
                    try
                    {
                        Process startPython = new Process();
                        startPython.StartInfo.FileName = "python";
                        string videoDosyasi = kameraId == "KAMERA_2" ? "vid2.mp4" : "4corner2.mp4";
                        startPython.StartInfo.Arguments = $"main.py --camera {kameraId} --video {videoDosyasi}";
                        startPython.StartInfo.UseShellExecute = true;
                        startPython.StartInfo.CreateNoWindow = false;
                        startPython.Start();
                        aktifPythonSurecleri.Add(kameraId, startPython);
                    }
                    catch (Exception ex)
                    {
                        System.Windows.MessageBox.Show($"{kameraId} yapay zeka süreci başlatılırken hata oluştu: {ex.Message}");
                    }
                }
            }
        }

        private void MainWindow_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
        {
            foreach (var p in aktifPythonSurecleri.Values)
            {
                try { if (!p.HasExited) p.Kill(); } catch { }
            }
        }

        private async void BaslatCanliVeriDinleyici()
        {
            try
            {
                using UdpClient udpClient = new UdpClient(5005);
                while (true)
                {
                    var result = await udpClient.ReceiveAsync();
                    string jsonPaket = Encoding.UTF8.GetString(result.Buffer);

                    try
                    {
                        using JsonDocument doc = JsonDocument.Parse(jsonPaket);
                        if (doc.RootElement.TryGetProperty("lanes", out JsonElement lanes))
                        {
                            lock (yogunlukLock)
                            {
                                sonGuncellemeZamani = DateTime.Now; // Veri geldikçe sayacı sıfırla
                                foreach (var lane in lanes.EnumerateArray())
                                {
                                    string id = lane.GetProperty("id").GetString() ?? "";
                                    int count = lane.GetProperty("count").GetInt32();
                                    anlikYogunlukHaritasi[id] = count;
                                }
                            }
                        }
                    }
                    catch { }

                    await Dispatcher.InvokeAsync(async () =>
                    {
                        if (webView.CoreWebView2 != null)
                        {
                            string jsKomutu = $"TopluCanliVeriGuncelle({jsonPaket});";
                            await webView.CoreWebView2.ExecuteScriptAsync(jsKomutu);
                        }
                    });
                }
            }
            catch { }
        }

        private async void BaslatYogunlukKaydedici()
        {
            await System.Threading.Tasks.Task.Run(async () =>
            {
                bool timeoutTetiklendi = false; // JavaScript'e sadece 1 kez sinyal yollamak için
                while (true)
                {
                    try
                    {
                        string jsonCikti;
                        bool kopuklukVar = false;

                        lock (yogunlukLock)
                        {
                            // Python'dan 2.5 saniyedir haber alınamıyorsa sistemi sıfırla!
                            if ((DateTime.Now - sonGuncellemeZamani).TotalSeconds > 2.5)
                            {
                                anlikYogunlukHaritasi.Clear();
                                kopuklukVar = true;
                            }
                            else
                            {
                                timeoutTetiklendi = false; // Bağlantı geri gelirse tetikleyiciyi kur
                            }
                            jsonCikti = JsonSerializer.Serialize(anlikYogunlukHaritasi, new JsonSerializerOptions { WriteIndented = true });
                        }

                        File.WriteAllText(canliYogunlukDosyaYolu, jsonCikti);

                        // Eğer koptuysa ve arayüze henüz haber verilmediyse:
                        if (kopuklukVar && !timeoutTetiklendi)
                        {
                            timeoutTetiklendi = true;
                            await Dispatcher.InvokeAsync(async () =>
                            {
                                if (webView.CoreWebView2 != null)
                                {
                                    // Arayüzdeki bütün ışıkları griye çeken özel JS fonksiyonunu tetikle
                                    await webView.CoreWebView2.ExecuteScriptAsync("BaglantiKoptuSifirla();");
                                }
                            });
                        }
                    }
                    catch { }

                    await System.Threading.Tasks.Task.Delay(1000);
                }
            });
        }

        private async void OnWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                string jsonMesaj = e.WebMessageAsJson;
                using JsonDocument doc = JsonDocument.Parse(jsonMesaj);
                JsonElement root = doc.RootElement;
                string mesajTipi = root.GetProperty("type").GetString() ?? "";

                if (mesajTipi == "drawPolygon")
                {
                    string pointsJson = root.GetProperty("points").GetRawText();

                    await this.Dispatcher.InvokeAsync(async () =>
                    {
                        SeritAyarForm ayarFormu = new SeritAyarForm();
                        ayarFormu.ShowDialog();

                        if (ayarFormu.OnaylandiMi)
                        {
                            string seritIsmi = ayarFormu.GirilenSeritIsmi;
                            int isikModu = ayarFormu.SecilenIsikModu;
                            string havaDurumu = ayarFormu.SecilenHava;

                            List<LevhaModel> secilenLevhalar = new List<LevhaModel>();
                            foreach (var l in ayarFormu.SecilenLevhalar)
                            {
                                secilenLevhalar.Add(new LevhaModel { Ikon = l.Ikon, Ad = l.Ad, Sure = l.VarsayilanSureEtkisi });
                            }

                            string seritId = string.IsNullOrWhiteSpace(ayarFormu.GirilenSeritId)
                                                ? "MANUEL_" + Guid.NewGuid().ToString("N").Substring(0, 6)
                                                : ayarFormu.GirilenSeritId;

                            aktifSeritIdListesi.Add(seritId);
                            string atananKameraId = "KAMERA_1";
                            if (seritId.StartsWith("KAMERA_2_") || seritId.Contains("_KAMERA_2_")) atananKameraId = "KAMERA_2";

                            List<SeritModel> mevcutSeritler = GeriyeDonukSeritleriYukle();
                            var noktalar = JsonSerializer.Deserialize<List<NoktaModel>>(pointsJson);

                            if (noktalar != null)
                            {
                                mevcutSeritler.RemoveAll(s => s.Id == seritId);
                                mevcutSeritler.Add(new SeritModel
                                {
                                    Id = seritId,
                                    KameraId = atananKameraId,
                                    Isim = seritIsmi,
                                    IsikModu = isikModu,
                                    HavaDurumu = havaDurumu,
                                    Levhalar = secilenLevhalar,
                                    Noktalar = noktalar,
                                    Adres = ayarFormu.GirilenAdres,
                                    OncekiSeritler = new List<string>(ayarFormu.OncekiSeritler),
                                    SonrakiSeritler = new List<string>(ayarFormu.SonrakiSeritler)
                                });
                            }

                            File.WriteAllText(veriDosyasiYolu, JsonSerializer.Serialize(mevcutSeritler, new JsonSerializerOptions { WriteIndented = true }));
                            PythonSurecleriniYonet(mevcutSeritler);

                            string guncelJson = File.ReadAllText(veriDosyasiYolu);
                            await webView.CoreWebView2.ExecuteScriptAsync($"TopluSeritYukle({guncelJson});");
                        }
                    });
                }
                else if (mesajTipi == "editLane")
                {
                    string seritId = root.GetProperty("id").GetString() ?? "";
                    List<SeritModel> mevcutSeritler = GeriyeDonukSeritleriYukle();
                    var secilenSerit = mevcutSeritler.Find(s => s.Id == seritId);

                    if (secilenSerit != null)
                    {
                        await this.Dispatcher.InvokeAsync(async () =>
                        {
                            SeritAyarForm ayarFormu = new SeritAyarForm();
                            List<TrafikLevhasi> formLevhalari = new List<TrafikLevhasi>();
                            foreach (var l in secilenSerit.Levhalar)
                            {
                                formLevhalari.Add(new TrafikLevhasi { Ad = l.Ad, Ikon = l.Ikon, VarsayilanSureEtkisi = l.Sure });
                            }

                            ayarFormu.VerileriYukle(secilenSerit.Isim, secilenSerit.Id, secilenSerit.IsikModu, secilenSerit.HavaDurumu,
                                formLevhalari, secilenSerit.Adres, secilenSerit.OncekiSeritler, secilenSerit.SonrakiSeritler);

                            ayarFormu.ShowDialog();

                            if (ayarFormu.SeritSilindiMi)
                            {
                                mevcutSeritler.Remove(secilenSerit);
                                File.WriteAllText(veriDosyasiYolu, JsonSerializer.Serialize(mevcutSeritler, new JsonSerializerOptions { WriteIndented = true }));
                                aktifSeritIdListesi.Remove(secilenSerit.Id);
                                string guncelJson = JsonSerializer.Serialize(mevcutSeritler);
                                await webView.CoreWebView2.ExecuteScriptAsync($"TopluSeritYukle({guncelJson});");
                            }
                            else if (ayarFormu.OnaylandiMi)
                            {
                                secilenSerit.Isim = ayarFormu.GirilenSeritIsmi;
                                secilenSerit.Id = ayarFormu.GirilenSeritId;
                                secilenSerit.IsikModu = ayarFormu.SecilenIsikModu;
                                secilenSerit.HavaDurumu = ayarFormu.SecilenHava;
                                secilenSerit.KameraId = (secilenSerit.Id.Contains("KAMERA_2")) ? "KAMERA_2" : "KAMERA_1";
                                secilenSerit.Levhalar = ayarFormu.SecilenLevhalar.Select(l => new LevhaModel { Ikon = l.Ikon, Ad = l.Ad, Sure = l.VarsayilanSureEtkisi }).ToList();
                                secilenSerit.Adres = ayarFormu.GirilenAdres;
                                secilenSerit.OncekiSeritler = new List<string>(ayarFormu.OncekiSeritler);
                                secilenSerit.SonrakiSeritler = new List<string>(ayarFormu.SonrakiSeritler);

                                File.WriteAllText(veriDosyasiYolu, JsonSerializer.Serialize(mevcutSeritler, new JsonSerializerOptions { WriteIndented = true }));
                                string guncelJson = File.ReadAllText(veriDosyasiYolu);
                                await webView.CoreWebView2.ExecuteScriptAsync($"TopluSeritYukle({guncelJson});");
                                PythonSurecleriniYonet(mevcutSeritler);
                            }
                        });
                    }
                }
            }
            catch (Exception ex)
            {
                System.Windows.MessageBox.Show($"Hata: {ex.Message}");
            }
        }

        private List<SeritModel> GeriyeDonukSeritleriYukle()
        {
            if (File.Exists(veriDosyasiYolu))
            {
                string okunanJson = File.ReadAllText(veriDosyasiYolu);
                return JsonSerializer.Deserialize<List<SeritModel>>(okunanJson) ?? new List<SeritModel>();
            }
            return new List<SeritModel>();
        }
    }
}