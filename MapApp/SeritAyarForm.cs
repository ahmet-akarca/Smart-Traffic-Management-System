using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using System.Linq;

namespace MapApp
{
    public class TrafikLevhasi
    {
        public string Kategori { get; set; } = string.Empty;
        public string Ad { get; set; } = string.Empty;
        public int VarsayilanSureEtkisi { get; set; } = 0;
        public string Ikon { get; set; } = string.Empty;
    }

    [System.Runtime.Versioning.SupportedOSPlatform("windows")]
    public partial class SeritAyarForm : Form
    {
        private Panel? pnlNav, pnlGenel, pnlKonum, pnlZincir;
        private Button? btnTabGenel, btnTabKonum, btnTabZincir;

        public TextBox txtSeritIsmi = new TextBox();
        public TextBox txtSeritId = new TextBox();

        private Button? btnIsikModu, btnHavaDurumu, btnLevhaEkle, btnKaydet, btnSil;
        private FlowLayoutPanel? flpLevhalar, flpZincirler;

        private ComboBox? cmbIl, cmbIlce, cmbMahalle, cmbCadde, cmbSokak;
        private TextBox? txtBinaNo;

        private RadioButton? rbOnune, rbArkasina;
        private TextBox? txtZincirId;

        public string GirilenSeritIsmi { get; private set; } = string.Empty;
        public string GirilenSeritId { get; private set; } = string.Empty;
        public int SecilenIsikModu { get; set; } = 0;
        public string SecilenHava { get; set; } = "☀️ Güneşli";
        public List<TrafikLevhasi> SecilenLevhalar { get; private set; } = new List<TrafikLevhasi>();

        public AdresModel GirilenAdres { get; private set; } = new AdresModel();
        public List<string> OncekiSeritler { get; private set; } = new List<string>();
        public List<string> SonrakiSeritler { get; private set; } = new List<string>();

        public bool OnaylandiMi { get; private set; } = false;
        public bool SeritSilindiMi { get; private set; } = false;

        public SeritAyarForm()
        {
            this.Text = "Şerit Yöneticisi (Akıllı Ağ)";
            this.Width = 420;
            this.Height = 650;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(30, 30, 30);
            this.TopMost = true;

            BilesenleriOlustur();
        }

        public void VerileriYukle(string isim, string id, int isikModu, string hava, List<TrafikLevhasi> levhalar, AdresModel adres, List<string> oncekiler, List<string> sonrakiler)
        {
            txtSeritIsmi.Text = isim;
            txtSeritId.Text = id;
            SecilenIsikModu = isikModu;
            string[] modlar = { "Otomatik", "Yeşil", "Sarı", "Kırmızı" };
            if (btnIsikModu != null) btnIsikModu.Text = $"🚦 Işık Modu: {modlar[SecilenIsikModu]}";
            SecilenHava = hava;
            if (btnHavaDurumu != null) btnHavaDurumu.Text = $"☁️ Hava: {SecilenHava}";

            SecilenLevhalar = new List<TrafikLevhasi>(levhalar);
            LevhalariCiz();

            if (adres != null)
            {
                if (cmbIl != null) cmbIl.Text = adres.Il;
                if (cmbIlce != null) cmbIlce.Text = adres.Ilce;
                if (cmbMahalle != null) cmbMahalle.Text = adres.Mahalle;
                if (cmbCadde != null) cmbCadde.Text = adres.Cadde;
                if (cmbSokak != null) cmbSokak.Text = adres.Sokak;
                if (txtBinaNo != null) txtBinaNo.Text = adres.BinaNo;
            }

            if (oncekiler != null) OncekiSeritler = new List<string>(oncekiler);
            if (sonrakiler != null) SonrakiSeritler = new List<string>(sonrakiler);
            ZincirleriCiz();
        }

        private void BilesenleriOlustur()
        {
            // 1. NAVİGASYON BARI
            pnlNav = new Panel { Dock = DockStyle.Top, Height = 45, BackColor = Color.FromArgb(45, 45, 48) };

            btnTabGenel = OlusturNavButonu("⚙️ Genel", 0, true);
            btnTabGenel.Click += (s, e) => SekmeDegistir(0);

            btnTabKonum = OlusturNavButonu("📍 Konum", 135, false);
            btnTabKonum.Click += (s, e) => SekmeDegistir(1);

            btnTabZincir = OlusturNavButonu("🔗 Zincir Ağı", 270, false);
            btnTabZincir.Click += (s, e) => SekmeDegistir(2);

            pnlNav.Controls.AddRange(new Control[] { btnTabGenel, btnTabKonum, btnTabZincir });
            this.Controls.Add(pnlNav);

            // 2. İÇERİK PANELLERİ
            Panel pnlContainer = new Panel { Dock = DockStyle.Fill, BackColor = Color.FromArgb(30, 30, 30) };
            this.Controls.Add(pnlContainer);
            this.Controls.SetChildIndex(pnlNav, 0);

            pnlGenel = new Panel { Dock = DockStyle.Fill, Visible = true };
            pnlKonum = new Panel { Dock = DockStyle.Fill, Visible = false };
            pnlZincir = new Panel { Dock = DockStyle.Fill, Visible = false };

            pnlContainer.Controls.AddRange(new Control[] { pnlGenel, pnlKonum, pnlZincir });

            // --- TAB 1: GENEL AYARLAR ---
            int yGenel = 50; // Yukarıdan 25px ferah boşluk
            pnlGenel.Controls.Add(new Label { Text = "Şerit İsmi", ForeColor = Color.LightGray, Top = yGenel, Left = 20, AutoSize = true, Font = new Font("Segoe UI", 9) });
            txtSeritIsmi = OlusturModernTextBox(yGenel += 20, 20, 360);
            pnlGenel.Controls.Add(txtSeritIsmi);

            pnlGenel.Controls.Add(new Label { Text = "Python Şerit ID", ForeColor = Color.LightGray, Top = yGenel += 45, Left = 20, AutoSize = true, Font = new Font("Segoe UI", 9) });
            txtSeritId = OlusturModernTextBox(yGenel += 20, 20, 360);
            txtSeritId.ForeColor = Color.White;
            txtSeritId.ReadOnly = false;
            pnlGenel.Controls.Add(txtSeritId);

            btnIsikModu = OlusturAksiyonButonu("🚦 Işık Modu: Otomatik", yGenel += 45, Color.FromArgb(0, 122, 255));
            btnIsikModu.Click += (s, e) => { SecilenIsikModu = (SecilenIsikModu + 1) % 4; string[] modlar = { "Otomatik", "Yeşil", "Sarı", "Kırmızı" }; btnIsikModu.Text = $"🚦 Işık Modu: {modlar[SecilenIsikModu]}"; };
            pnlGenel.Controls.Add(btnIsikModu);

            btnHavaDurumu = OlusturAksiyonButonu("☀️ Hava: Güneşli", yGenel += 50, Color.FromArgb(255, 149, 0));
            btnHavaDurumu.Click += (s, e) => { string[] havalar = { "☀️ Güneşli", "🌧️ Yağmurlu", "❄️ Karlı", "🌫️ Sisli" }; int idx = Array.IndexOf(havalar, SecilenHava); SecilenHava = havalar[(idx + 1) % havalar.Length]; btnHavaDurumu.Text = $"☁️ Hava: {SecilenHava}"; };
            pnlGenel.Controls.Add(btnHavaDurumu);

            flpLevhalar = new FlowLayoutPanel { Top = yGenel += 55, Left = 20, Width = 360, Height = 145, BackColor = Color.FromArgb(40, 40, 42), AutoScroll = true, Padding = new Padding(5) };
            pnlGenel.Controls.Add(flpLevhalar);

            btnLevhaEkle = OlusturAksiyonButonu("➕ Kütüphaneden Levha Ekle", yGenel += 160, Color.FromArgb(52, 199, 89));
            btnLevhaEkle.Click += (s, e) => { using (var lf = new LevhaSecimForm()) { if (lf.ShowDialog(this) == DialogResult.OK) { SecilenLevhalar.Add(lf.SecilenLevha); LevhalariCiz(); } } };
            pnlGenel.Controls.Add(btnLevhaEkle);

            // --- TAB 2: KONUM (ADRES) DÜZELTİLDİ ---
            int lblX = 20, inputX = 20, inputW = 360;
            int yKonum = 50; // Çakışmayı önleyen üst başlangıç marjı

            pnlKonum.Controls.Add(new Label { Text = "İl", ForeColor = Color.DarkGray, Top = yKonum, Left = lblX, AutoSize = true, Font = new Font("Segoe UI", 9) });
            cmbIl = OlusturModernComboBox(yKonum += 20, inputX, inputW);
            pnlKonum.Controls.Add(cmbIl);

            pnlKonum.Controls.Add(new Label { Text = "İlçe", ForeColor = Color.DarkGray, Top = yKonum += 45, Left = lblX, AutoSize = true, Font = new Font("Segoe UI", 9) });
            cmbIlce = OlusturModernComboBox(yKonum += 20, inputX, inputW);
            pnlKonum.Controls.Add(cmbIlce);

            pnlKonum.Controls.Add(new Label { Text = "Mahalle", ForeColor = Color.DarkGray, Top = yKonum += 45, Left = lblX, AutoSize = true, Font = new Font("Segoe UI", 9) });
            cmbMahalle = OlusturModernComboBox(yKonum += 20, inputX, inputW);
            pnlKonum.Controls.Add(cmbMahalle);

            pnlKonum.Controls.Add(new Label { Text = "Cadde", ForeColor = Color.DarkGray, Top = yKonum += 45, Left = lblX, AutoSize = true, Font = new Font("Segoe UI", 9) });
            cmbCadde = OlusturModernComboBox(yKonum += 20, inputX, inputW);
            pnlKonum.Controls.Add(cmbCadde);

            pnlKonum.Controls.Add(new Label { Text = "Sokak", ForeColor = Color.DarkGray, Top = yKonum += 45, Left = lblX, AutoSize = true, Font = new Font("Segoe UI", 9) });
            cmbSokak = OlusturModernComboBox(yKonum += 20, inputX, inputW);
            pnlKonum.Controls.Add(cmbSokak);

            pnlKonum.Controls.Add(new Label { Text = "Bina / Kapı No", ForeColor = Color.DarkGray, Top = yKonum += 45, Left = lblX, AutoSize = true, Font = new Font("Segoe UI", 9) });
            txtBinaNo = OlusturModernTextBox(yKonum += 20, inputX, 150);
            pnlKonum.Controls.Add(txtBinaNo);

            // --- TAB 3: ZİNCİR BAĞLANTILARI ---
            int yZincir = 50; // Üst boşluk
            rbOnune = new RadioButton { Text = "Bu Şeridin ÖNÜNE Ekle (Bu şeride giren araçlar)", ForeColor = Color.White, Top = yZincir, Left = 20, AutoSize = true, Checked = true, Font = new Font("Segoe UI", 9) };
            rbArkasina = new RadioButton { Text = "Bu Şeridin ARKASINA Ekle (Bu şeritten çıkan araçlar)", ForeColor = Color.White, Top = yZincir += 35, Left = 20, AutoSize = true, Font = new Font("Segoe UI", 9) };
            pnlZincir.Controls.Add(rbOnune); pnlZincir.Controls.Add(rbArkasina);

            pnlZincir.Controls.Add(new Label { Text = "Bağlanacak Şerit ID:", ForeColor = Color.LightGray, Top = yZincir += 45, Left = 20, AutoSize = true, Font = new Font("Segoe UI", 9) });
            txtZincirId = OlusturModernTextBox(yZincir += 20, 20, 270);
            pnlZincir.Controls.Add(txtZincirId);

            Button btnZincirEkle = new Button { Text = "➕ Ekle", Top = yZincir, Left = 300, Width = 80, Height = 28, BackColor = Color.FromArgb(0, 122, 255), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 9, FontStyle.Bold), Cursor = Cursors.Hand };
            btnZincirEkle.FlatAppearance.BorderSize = 0;
            btnZincirEkle.Click += BtnZincirEkle_Click;
            pnlZincir.Controls.Add(btnZincirEkle);

            flpZincirler = new FlowLayoutPanel { Top = yZincir += 50, Left = 20, Width = 360, Height = 285, BackColor = Color.FromArgb(40, 40, 42), AutoScroll = true, Padding = new Padding(5) };
            pnlZincir.Controls.Add(flpZincirler);

            // 3. ALT PANEL (KAYDET VE SİL)
            Panel pnlAlt = new Panel { Dock = DockStyle.Bottom, Height = 100, BackColor = Color.FromArgb(25, 25, 25) };

            btnKaydet = OlusturAksiyonButonu("✔ Tüm Ayarları Kaydet ve Uygula", 15, Color.FromArgb(0, 122, 255));
            btnKaydet.Click += BtnKaydet_Click;
            pnlAlt.Controls.Add(btnKaydet);

            btnSil = OlusturAksiyonButonu("🗑️ Şeridi Tamamen Sil", 55, Color.FromArgb(255, 59, 48));
            btnSil.Click += (s, e) => {
                if (System.Windows.Forms.MessageBox.Show("Bu şeridi ve içindeki tüm verileri silmek istediğinize emin misiniz?", "Şeridi Sil", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes)
                { SeritSilindiMi = true; this.Close(); }
            };
            pnlAlt.Controls.Add(btnSil);

            this.Controls.Add(pnlAlt);
        }

        private Button OlusturNavButonu(string text, int left, bool aktif)
        {
            Button b = new Button { Text = text, Top = 0, Left = left, Width = 135, Height = 45, BackColor = aktif ? Color.FromArgb(60, 60, 65) : Color.FromArgb(45, 45, 48), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 9, FontStyle.Bold), Cursor = Cursors.Hand };
            b.FlatAppearance.BorderSize = 0;
            return b;
        }

        private TextBox OlusturModernTextBox(int top, int left, int width)
        {
            return new TextBox { Top = top, Left = left, Width = width, BackColor = Color.FromArgb(50, 50, 52), ForeColor = Color.White, Font = new Font("Segoe UI", 11), BorderStyle = BorderStyle.FixedSingle };
        }

        private ComboBox OlusturModernComboBox(int top, int left, int width)
        {
            return new ComboBox { Top = top, Left = left, Width = width, BackColor = Color.FromArgb(50, 50, 52), ForeColor = Color.White, Font = new Font("Segoe UI", 11), FlatStyle = FlatStyle.Flat, DropDownStyle = ComboBoxStyle.DropDown };
        }

        private Button OlusturAksiyonButonu(string text, int top, Color renk)
        {
            Button b = new Button { Text = text, Top = top, Left = 20, Width = 360, Height = 40, BackColor = renk, ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 10, FontStyle.Bold), Cursor = Cursors.Hand };
            b.FlatAppearance.BorderSize = 0; return b;
        }

        private void SekmeDegistir(int index)
        {
            if (pnlGenel == null || pnlKonum == null || pnlZincir == null || btnTabGenel == null || btnTabKonum == null || btnTabZincir == null) return;

            pnlGenel.Visible = index == 0;
            pnlKonum.Visible = index == 1;
            pnlZincir.Visible = index == 2;

            btnTabGenel.BackColor = index == 0 ? Color.FromArgb(70, 70, 75) : Color.FromArgb(45, 45, 48);
            btnTabKonum.BackColor = index == 1 ? Color.FromArgb(70, 70, 75) : Color.FromArgb(45, 45, 48);
            btnTabZincir.BackColor = index == 2 ? Color.FromArgb(70, 70, 75) : Color.FromArgb(45, 45, 48);
        }

        private void BtnZincirEkle_Click(object? sender, EventArgs e)
        {
            if (txtZincirId == null || rbOnune == null || rbArkasina == null) return;
            string eklenecekId = txtZincirId.Text.Trim();
            if (string.IsNullOrEmpty(eklenecekId)) return;

            if (rbOnune.Checked && !OncekiSeritler.Contains(eklenecekId)) OncekiSeritler.Add(eklenecekId);
            else if (rbArkasina.Checked && !SonrakiSeritler.Contains(eklenecekId)) SonrakiSeritler.Add(eklenecekId);

            txtZincirId.Clear();
            ZincirleriCiz();
        }

        private void ZincirleriCiz()
        {
            if (flpZincirler == null) return;
            flpZincirler.Controls.Clear();
            CizZincir(OncekiSeritler, "⬅️ Önceki:", Color.DarkCyan);
            CizZincir(SonrakiSeritler, "➡️ Sonraki:", Color.DarkOrange);
        }

        private void CizZincir(List<string> liste, string etiket, Color renk)
        {
            if (flpZincirler == null) return;
            foreach (var id in liste.ToList())
            {
                Panel pnl = new Panel { Width = 325, Height = 35, Margin = new Padding(0, 0, 0, 5), BackColor = Color.FromArgb(60, 60, 65) };
                Label lbl = new Label { Text = $"{etiket} {id}", AutoSize = true, ForeColor = renk, Location = new Point(5, 8), Font = new Font("Segoe UI", 8, FontStyle.Bold) };
                Button btnX = new Button { Text = "X", Width = 30, Height = 35, BackColor = Color.FromArgb(255, 59, 48), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Location = new Point(295, 0), Cursor = Cursors.Hand };
                btnX.FlatAppearance.BorderSize = 0;
                btnX.Click += (s, e) => { liste.Remove(id); ZincirleriCiz(); };
                pnl.Controls.Add(lbl); pnl.Controls.Add(btnX); flpZincirler.Controls.Add(pnl);
            }
        }

        private void LevhalariCiz()
        {
            if (flpLevhalar == null) return;
            flpLevhalar.Controls.Clear();
            foreach (var levha in SecilenLevhalar.ToList())
            {
                Panel pnl = new Panel { Width = 325, Height = 35, Margin = new Padding(0, 0, 0, 5), BackColor = Color.FromArgb(60, 60, 65) };
                Label lbl = new Label { Text = $"{levha.Ikon} {levha.Ad} ({levha.VarsayilanSureEtkisi}s)", AutoSize = true, ForeColor = Color.White, Location = new Point(5, 8), Font = new Font("Segoe UI", 9, FontStyle.Bold) };
                Button btnKaldir = new Button { Text = "X", Width = 30, Height = 35, BackColor = Color.FromArgb(255, 59, 48), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Location = new Point(295, 0), Cursor = Cursors.Hand };
                btnKaldir.FlatAppearance.BorderSize = 0;
                btnKaldir.Click += (s, e) => { SecilenLevhalar.Remove(levha); LevhalariCiz(); };
                pnl.Controls.Add(lbl); pnl.Controls.Add(btnKaldir); flpLevhalar.Controls.Add(pnl);
            }
        }

        private void BtnKaydet_Click(object? sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(txtSeritIsmi.Text))
            {
                System.Windows.Forms.MessageBox.Show("Şerit ismi zorunludur!", "Uyarı", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            GirilenSeritIsmi = txtSeritIsmi.Text;
            GirilenSeritId = txtSeritId.Text;

            GirilenAdres = new AdresModel
            {
                Il = cmbIl?.Text ?? "",
                Ilce = cmbIlce?.Text ?? "",
                Mahalle = cmbMahalle?.Text ?? "",
                Cadde = cmbCadde?.Text ?? "",
                Sokak = cmbSokak?.Text ?? "",
                BinaNo = txtBinaNo?.Text ?? ""
            };
            OnaylandiMi = true;
            this.Close();
        }
    }

    public class LevhaSecimForm : Form
    {
        public TrafikLevhasi SecilenLevha { get; private set; } = new TrafikLevhasi();

        public LevhaSecimForm()
        {
            this.Text = "Kapsamlı Levha Kütüphanesi";
            this.Size = new Size(440, 680);
            this.BackColor = Color.FromArgb(25, 25, 25);
            this.StartPosition = FormStartPosition.CenterParent;
            this.FormBorderStyle = FormBorderStyle.FixedToolWindow;
            this.TopMost = true;

            var mainPanel = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoScroll = true, Padding = new Padding(15) };

            var kategoriler = new Dictionary<string, List<TrafikLevhasi>>
            {
                { "⚠️ TEHLİKE UYARI İŞARETLERİ", new List<TrafikLevhasi> {
                    new TrafikLevhasi { Ad = "Sağa Tehlikeli Viraj", Ikon = "⚠️", VarsayilanSureEtkisi = 3, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Sola Tehlikeli Viraj", Ikon = "⚠️", VarsayilanSureEtkisi = 3, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Kasisli Yol", Ikon = "⚠️", VarsayilanSureEtkisi = 5, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Kaygan Yol", Ikon = "⚠️", VarsayilanSureEtkisi = 5, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Yaya Geçidi Yaklaşıyor", Ikon = "🚸", VarsayilanSureEtkisi = 8, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Okul Geçidi Yaklaşıyor", Ikon = "🚸", VarsayilanSureEtkisi = 10, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Yolda Çalışma Var", Ikon = "🚧", VarsayilanSureEtkisi = 12, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "Işıklı İşaret Cihazı (Trafik Işığı)", Ikon = "🚦", VarsayilanSureEtkisi = 2, Kategori = "Tehlike" },
                    new TrafikLevhasi { Ad = "İki Yönlü Trafik", Ikon = "↕️", VarsayilanSureEtkisi = 4, Kategori = "Tehlike" }
                }},
                { "🛑 TRAFİK TANZİM İŞARETLERİ", new List<TrafikLevhasi> {
                    new TrafikLevhasi { Ad = "DUR", Ikon = "🛑", VarsayilanSureEtkisi = 15, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Yol Ver", Ikon = "🔻", VarsayilanSureEtkisi = 8, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Taşıt Trafiğine Kapalı Yol", Ikon = "⛔", VarsayilanSureEtkisi = 99, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Girişi Olmayan Yol", Ikon = "⛔", VarsayilanSureEtkisi = 99, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Sağa Dönülmez", Ikon = "🚫", VarsayilanSureEtkisi = 0, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Sola Dönülmez", Ikon = "🚫", VarsayilanSureEtkisi = 0, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "U Dönüşü Yapılmaz", Ikon = "🚫", VarsayilanSureEtkisi = 0, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Azami Hız Sınırı 30", Ikon = "⭕", VarsayilanSureEtkisi = 8, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Azami Hız Sınırı 50", Ikon = "⭕", VarsayilanSureEtkisi = 4, Kategori = "Tanzim" },
                    new TrafikLevhasi { Ad = "Azami Hız Sınırı 70", Ikon = "⭕", VarsayilanSureEtkisi = 2, Kategori = "Tanzim" }
                }},
                { "🅿️ DURAKLAMA VE PARK ETME", new List<TrafikLevhasi> {
                    new TrafikLevhasi { Ad = "Park Etmek Yasaktır", Ikon = "🚫", VarsayilanSureEtkisi = 0, Kategori = "Park" },
                    new TrafikLevhasi { Ad = "Duraklamak ve Park Etmek Yasaktır", Ikon = "❌", VarsayilanSureEtkisi = 0, Kategori = "Park" },
                    new TrafikLevhasi { Ad = "Park Yeri", Ikon = "🅿️", VarsayilanSureEtkisi = -2, Kategori = "Park" }
                }},
                { "ℹ️ BİLGİ İŞARETLERİ", new List<TrafikLevhasi> {
                    new TrafikLevhasi { Ad = "Ana Yol", Ikon = "🔶", VarsayilanSureEtkisi = -5, Kategori = "Bilgi" },
                    new TrafikLevhasi { Ad = "Tek Yönlü Yol", Ikon = "⬆️", VarsayilanSureEtkisi = -3, Kategori = "Bilgi" },
                    new TrafikLevhasi { Ad = "Tünel", Ikon = "🚇", VarsayilanSureEtkisi = 5, Kategori = "Bilgi" },
                    new TrafikLevhasi { Ad = "Yaya Geçidi (Bilgi)", Ikon = "🚶", VarsayilanSureEtkisi = 5, Kategori = "Bilgi" }
                }}
            };

            foreach (var kat in kategoriler)
            {
                Label lblKategori = new Label { Text = kat.Key, ForeColor = Color.FromArgb(0, 190, 255), Font = new Font("Segoe UI", 10, FontStyle.Bold), AutoSize = true, Margin = new Padding(5, 15, 5, 8) };
                mainPanel.Controls.Add(lblKategori);

                foreach (var l in kat.Value)
                {
                    var btn = new Button
                    {
                        Text = $" {l.Ikon}   {l.Ad}",
                        Width = 370,
                        Height = 45,
                        Margin = new Padding(5, 0, 0, 8),
                        BackColor = Color.FromArgb(45, 45, 48),
                        ForeColor = Color.White,
                        FlatStyle = FlatStyle.Flat,
                        TextAlign = ContentAlignment.MiddleLeft,
                        Font = new Font("Segoe UI", 10, FontStyle.Regular),
                        Cursor = Cursors.Hand
                    };
                    btn.FlatAppearance.BorderSize = 0;

                    btn.MouseEnter += (s, e) => btn.BackColor = Color.FromArgb(70, 70, 75);
                    btn.MouseLeave += (s, e) => btn.BackColor = Color.FromArgb(45, 45, 48);

                    btn.Click += (s, e) => {
                        using (var sf = new SureAyarForm(l))
                        {
                            if (sf.ShowDialog(this) == DialogResult.OK)
                            {
                                SecilenLevha = sf.Levha;
                                DialogResult = DialogResult.OK;
                                Close();
                            }
                        }
                    };
                    mainPanel.Controls.Add(btn);
                }
            }
            Controls.Add(mainPanel);
        }
    }

    public class SureAyarForm : Form
    {
        public TrafikLevhasi Levha;
        public SureAyarForm(TrafikLevhasi l)
        {
            Levha = l;
            this.Text = "Süre Etkisi Ayarı";
            this.Size = new Size(280, 240);
            this.BackColor = Color.FromArgb(36, 36, 38);
            this.StartPosition = FormStartPosition.CenterParent;
            this.FormBorderStyle = FormBorderStyle.FixedToolWindow;
            this.TopMost = true;

            Label lblBaslik = new Label { Text = $"{l.Ikon} {l.Ad}", ForeColor = Color.White, Dock = DockStyle.Top, TextAlign = ContentAlignment.MiddleCenter, Height = 40, Font = new Font("Segoe UI", 11, FontStyle.Bold) };
            this.Controls.Add(lblBaslik);

            NumericUpDown num = new NumericUpDown { Top = 100, Left = 90, Width = 80, Minimum = -30, Maximum = 60, Value = l.VarsayilanSureEtkisi, Font = new Font("Segoe UI", 14, FontStyle.Bold), BackColor = Color.FromArgb(50, 50, 50), ForeColor = Color.White, TextAlign = HorizontalAlignment.Center };
            this.Controls.Add(num);

            Button btnOnay = new Button { Text = "✔ Onayla", Top = 150, Left = 40, Width = 180, Height = 40, BackColor = Color.FromArgb(52, 199, 89), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Font = new Font("Segoe UI", 10, FontStyle.Bold), Cursor = Cursors.Hand };
            btnOnay.FlatAppearance.BorderSize = 0;
            btnOnay.Click += (s, e) => { Levha.VarsayilanSureEtkisi = (int)num.Value; DialogResult = DialogResult.OK; Close(); };
            this.Controls.Add(btnOnay);
        }
    }
}