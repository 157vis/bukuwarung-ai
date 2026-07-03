"""Landing page marketing laris.AI — layout Bootstrap grid, single-page solid."""

from __future__ import annotations

import textwrap

import streamlit as st
import streamlit.components.v1 as components

from brand import APP_NAME, APP_TAGLINE

_HERO_STATS = [
    ("100%", "Gratis coba demo publik"),
    ("< 30s", "Waktu catat transaksi via WA"),
    ("24/7", "AI menyala otomatis"),
    ("Multi-Tenant", "RLS per toko"),
]

# Domain publik: landing statis & dashboard Streamlit.
#
# NOTE:
# `app.larisai.my.id` sempat tidak stabil (503). Untuk menjaga CTA "Masuk"
# tetap berfungsi, sementara diarahkan ke domain Railway yang terbukti hidup.
# Nanti cukup ganti kembali APP_DOMAIN ke custom domain app saat sudah sehat.
LANDING_DOMAIN = "https://www.larisai.my.id"
APP_DOMAIN = "https://larisai.my.id"

_INLINE_LANDING_CSS = """
.laris-landing { font-family: "Public Sans", system-ui, sans-serif; color:#1c252e; background:#f9fafb; }
.laris-landing a { text-decoration:none; }
.laris-landing .laris-section-inner { max-width:1140px; margin:0 auto; padding:0 1.25rem; }
.laris-landing .btn { display:inline-flex; align-items:center; gap:.5rem; padding:.6rem 1.1rem; border-radius:.5rem; font-weight:600; border:1px solid transparent; line-height:1; }
.laris-landing .btn-lg { padding:.85rem 1.4rem; font-size:1rem; }
.laris-landing .btn-solid { background:#00a76f; color:#fff; border-color:#00a76f; box-shadow:0 6px 16px rgba(0,167,111,.25); }
.laris-landing .btn-ghost { background:rgba(255,255,255,.85); color:#1c252e; border-color:#e6eaee; }
.laris-navbar { position:sticky; top:0; z-index:50; background:rgba(255,255,255,.92); border-bottom:1px solid rgba(28,37,46,.06); }
.laris-navbar-inner { max-width:1140px; margin:0 auto; padding:.85rem 1.25rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; }
.laris-navbar-brand { display:inline-flex; align-items:center; gap:.55rem; color:#1c252e; font-weight:700; font-size:1.05rem; }
.laris-brand-dot { width:22px; height:22px; border-radius:6px; background:linear-gradient(135deg,#00a76f,#007867); display:inline-block; }
.laris-navbar-links { gap:1.5rem; }
.laris-navbar-links a { color:#454f5b; font-weight:500; font-size:.92rem; }
.laris-hero { background:linear-gradient(94.82deg,#ffe9d5 1.11%,#c8fad6 99.11%); padding:4.5rem 1.25rem; }
.laris-hero-inner { max-width:1140px; margin:0 auto; display:grid; grid-template-columns:1.3fr 1fr; gap:3rem; align-items:center; }
.laris-h1 { font-size:clamp(2rem,4.5vw,3.4rem); font-weight:800; letter-spacing:-.02em; line-height:1.1; margin:.5rem 0 1rem; }
.laris-h1-accent { background:linear-gradient(90deg,#00a76f,#007867); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.laris-lead { font-size:1.05rem; color:#454f5b; max-width:560px; margin-bottom:1.75rem; line-height:1.6; }
.laris-pill { display:inline-block; background:rgba(255,255,255,.6); color:#007867; padding:.35rem .85rem; border-radius:999px; font-weight:600; font-size:.8rem; text-transform:uppercase; border:1px solid rgba(0,167,111,.15); }
.laris-pill-soft { background:#c8fad6; color:#007867; }
.laris-hero-cta, .laris-hero-meta { display:flex; flex-wrap:wrap; gap:.75rem; }
.laris-hero-meta { gap:1rem; font-size:.85rem; color:#454f5b; margin-top:1rem; }
.laris-phone-frame { background:#fff; border-radius:1.25rem; padding:1rem; max-width:360px; margin-left:auto; border:1px solid rgba(28,37,46,.06); box-shadow:0 30px 60px rgba(28,37,46,.18); }
.laris-phone-header { display:flex; align-items:center; gap:.5rem; padding-bottom:.75rem; border-bottom:1px dashed rgba(28,37,46,.1); }
.laris-phone-dots span { display:inline-block; width:8px; height:8px; border-radius:50%; background:#d9dde2; margin-right:3px; }
.laris-phone-body { padding-top:.85rem; display:flex; flex-direction:column; gap:.6rem; font-size:.85rem; }
.laris-msg { padding:.6rem .85rem; border-radius:1rem; max-width:85%; line-height:1.4; }
.laris-msg-user { background:#d4f1d4; align-self:flex-end; border-bottom-right-radius:.25rem; }
.laris-msg-bot { background:#f4f6f8; align-self:flex-start; border-bottom-left-radius:.25rem; }
.laris-stats { background:#fff; border-block:1px solid rgba(28,37,46,.06); padding:1.5rem 0; }
.laris-stats-inner { max-width:1140px; margin:0 auto; padding:0 1.25rem; display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; }
.laris-stat-item { display:flex; flex-direction:column; align-items:center; text-align:center; gap:.25rem; }
.laris-stat-value { font-size:1.5rem; font-weight:800; color:#007867; }
.laris-stat-label { font-size:.85rem; color:#637381; }
.laris-section-head { text-align:center; max-width:720px; margin:0 auto 2.5rem; }
.laris-section-head h2 { font-size:clamp(1.5rem,3vw,2.2rem); font-weight:800; line-height:1.2; margin:.5rem 0; }
.laris-section-head p { color:#637381; font-size:1rem; }
.laris-features { padding:4.5rem 1.25rem; background:#f9fafb; }
.laris-features-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1.25rem; }
.laris-feature-card { background:#fff; border:1px solid rgba(28,37,46,.06); border-radius:1rem; padding:1.5rem; box-shadow:0 4px 12px rgba(28,37,46,.04); }
.laris-feature-icon { width:48px; height:48px; border-radius:12px; background:#c8fad6; color:#007867; display:inline-flex; align-items:center; justify-content:center; font-size:1.35rem; margin-bottom:1rem; }
.laris-feature-card h4 { font-size:1.05rem; font-weight:700; margin:0 0 .4rem; }
.laris-feature-card p { color:#637381; font-size:.92rem; line-height:1.55; margin:0; }
.laris-3d-lab { padding:4.5rem 1.25rem; background:linear-gradient(180deg,#f9fafb 0%,#ffffff 100%); }
.laris-3d-alur { padding:4.5rem 1.25rem; background:linear-gradient(180deg,#ffffff 0%,#f1f5f9 100%); }
.laris-3d-stok { padding:4.5rem 1.25rem; background:linear-gradient(180deg,#f1f5f9 0%,#fef9c3 100%); }
.laris-3d-omzet { padding:4.5rem 1.25rem; background:linear-gradient(180deg,#fef9c3 0%,#0c4a6e 10%,#082f49 100%); color:#fff; }
.laris-3d-omzet .laris-section-head h2,
.laris-3d-omzet .laris-section-head p { color:#fff; }
.laris-3d-omzet .laris-pill-soft { background:rgba(103,232,249,.18); color:#67e8f9; }
.laris-3d-frame { width:100%; height:520px; border-radius:1.25rem; overflow:hidden; box-shadow:0 18px 40px rgba(15,23,42,.18); background:#0f172a; }
.laris-3d-frame-dark { background:#0f172a; }
.laris-3d-frame-warm { background:#fef3c7; }
.laris-3d-frame-cool { background:#0c4a6e; }
.laris-3d-frame iframe { width:100%; height:100%; border:0; display:block; }
.laris-3d-caption { text-align:center; font-size:.85rem; color:#6b7280; margin-top:.85rem; }
.laris-3d-omzet .laris-3d-caption { color:rgba(255,255,255,.75); }
@media (max-width: 768px) { .laris-3d-frame { height:420px; } }
.laris-flow { padding:4.5rem 1.25rem; background:#fff; }
.laris-flow-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:1.25rem; }
.laris-flow-item { background:#f9fafb; border:1px solid rgba(28,37,46,.06); border-radius:1rem; padding:1.25rem; text-align:center; }
.laris-flow-step { position:relative; width:72px; height:72px; border-radius:50%; margin:.25rem auto 1rem; background:linear-gradient(135deg,#00a76f,#007867); color:#fff; display:flex; align-items:center; justify-content:center; }
.laris-flow-step span { position:absolute; top:4px; right:4px; background:#fff; color:#007867; font-weight:800; font-size:.65rem; padding:2px 6px; border-radius:999px; }
.laris-flow-step i { font-size:1.5rem; }
.laris-flow-item h5 { font-size:.98rem; font-weight:700; margin:.5rem 0 .4rem; }
.laris-flow-item p { font-size:.85rem; color:#637381; line-height:1.5; margin:0; }
.laris-cta { padding:4rem 1.25rem; background:linear-gradient(180deg,#f9fafb 0%,#f4f6f8 100%); }
.laris-cta-card { background:linear-gradient(94.82deg,#c8fad6 1.11%,#ffe9d5 99.11%); border-radius:1.25rem; padding:2.5rem; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1.5rem; border:1px solid rgba(0,167,111,.18); }
.laris-cta-card h2 { font-size:clamp(1.4rem,2.5vw,1.9rem); font-weight:800; margin:.5rem 0; }
.laris-footer { background:#1c252e; color:#fff; padding-top:2.5rem; }
.laris-footer-inner { display:grid; grid-template-columns:2fr 1fr 1fr; gap:2rem; padding-bottom:2rem; }
.laris-footer-col { display:flex; flex-direction:column; gap:.5rem; }
.laris-footer-col a { color:rgba(255,255,255,.75); font-size:.9rem; }
.laris-footer .text-muted { color:rgba(255,255,255,.55) !important; }
@media (max-width: 992px) {
  .laris-hero-inner { grid-template-columns:1fr; text-align:center; }
  .laris-lead { margin-left:auto; margin-right:auto; }
  .laris-hero-cta, .laris-hero-meta { justify-content:center; }
  .laris-phone-frame { margin:0 auto; }
  .laris-stats-inner, .laris-features-grid, .laris-flow-grid { grid-template-columns:repeat(2,1fr); }
  .laris-footer-inner { grid-template-columns:1fr 1fr; }
}
@media (max-width: 576px) {
  .laris-hero { padding:3rem 1rem; }
  .laris-features, .laris-flow, .laris-cta { padding:3rem 1rem; }
  .laris-features-grid, .laris-flow-grid { grid-template-columns:1fr; }
  .laris-stats-inner { grid-template-columns:1fr 1fr; }
  .laris-cta-card { padding:1.5rem; }
}
"""


def _navbar_html() -> str:
    return f"""
    <div class="laris-navbar">
      <div class="laris-navbar-inner">
        <a href="#" class="laris-navbar-brand">
          <span class="laris-brand-dot"></span>
          <strong>{APP_NAME}</strong>
          <small class="text-muted ms-2">{APP_TAGLINE}</small>
        </a>
        <nav class="laris-navbar-links d-none d-md-flex">
          <a href="#fitur">Fitur</a>
          <a href="#alur">Alur</a>
          <a href="{LANDING_DOMAIN}/artikel/cara-mencatat-keuangan-warung/" target="_blank" rel="noopener">Artikel</a>
          <a href="#cta">Mulai</a>
        </nav>
        <div class="laris-navbar-cta d-flex gap-2">
          <a href="{APP_DOMAIN}/?demo=1" target="_blank" rel="noopener" class="btn btn-ghost">Demo</a>
          <a href="{APP_DOMAIN}/?login=1" target="_blank" rel="noopener" class="btn btn-solid">Masuk</a>
        </div>
      </div>
    </div>
    """


def _hero_html() -> str:
    return f"""
    <section class="laris-hero">
      <div class="laris-hero-inner">
        <span class="laris-pill">🚀 UMKM-First · Multi-Agent</span>
        <h1 class="laris-h1">Catat jualan lewat <span class="laris-h1-accent">WhatsApp</span>,<br/>dashboard otomatis terisi.</h1>
        <p class="laris-lead">
          laris.AI adalah partner AI untuk toko, warung, dan UMKM Indonesia.
          Cukup kirim pesan <em>"jual kopi 50rb"</em>, Admin AI langsung catat ke Buku Kas,
          Logistik AI pantau stok, dan Dashboard Dasher Anda terisi secara real-time.
        </p>
        <div class="laris-hero-cta">
          <a href="{APP_DOMAIN}/?demo=1" target="_blank" rel="noopener" class="btn btn-solid btn-lg">
            <i class="ti ti-flask"></i> Buka Dashboard Demo
          </a>
          <a href="{LANDING_DOMAIN}/artikel/cara-mencatat-keuangan-warung/" target="_blank" rel="noopener" class="btn btn-ghost btn-lg">
            <i class="ti ti-news"></i> Baca Artikel UMKM
          </a>
          <a href="{APP_DOMAIN}/?login=1" target="_blank" rel="noopener" class="btn btn-ghost btn-lg">
            <i class="ti ti-login"></i> Masuk Akun
          </a>
        </div>
        <div class="laris-hero-meta">
          <span>✅ Setup gratis via Supabase</span>
          <span>✅ RLS Multi-Tenant aman</span>
          <span>✅ AI Groq & OpenRouter</span>
        </div>
      </div>
      <div class="laris-hero-visual d-none d-lg-block">
        <div class="laris-phone-frame">
          <div class="laris-phone-header">
            <div class="laris-phone-dots"><span></span><span></span><span></span></div>
            <small>WA Owner · Catat Transaksi</small>
          </div>
          <div class="laris-phone-body">
            <div class="laris-msg laris-msg-user">jual kopi 50rb, indomie 5 bungkus</div>
            <div class="laris-msg laris-msg-bot">
              ✅ <strong>2 transaksi</strong> tercatat.<br/>
              • Kopi · Rp50.000<br/>
              • Indomie x5 · Rp17.500
            </div>
            <div class="laris-msg laris-msg-user">stok mie tinggal berapa?</div>
            <div class="laris-msg laris-msg-bot">
              📦 Mie Instan: <strong>18 pcs</strong>.<br/>
              Saran restock: <strong>6 dus</strong>.
            </div>
          </div>
        </div>
      </div>
    </section>
    """


def _stats_html() -> str:
    cards = "".join(
        f'<div class="laris-stat-item"><span class="laris-stat-value">{v}</span>'
        f'<span class="laris-stat-label">{l}</span></div>'
        for v, l in _HERO_STATS
    )
    return f'<section class="laris-stats"><div class="laris-stats-inner">{cards}</div></section>'


def _features_html() -> str:
    return f"""
    <section class="laris-features" id="fitur">
      <div class="laris-section-inner">
        <div class="laris-section-head">
          <span class="laris-pill laris-pill-soft">Kenapa laris.AI?</span>
          <h2>Semua yang UMKM butuhkan, dalam satu platform.</h2>
          <p>Catat, lihat, dan ambil keputusan lebih cepat dengan AI Multi-Agent.</p>
        </div>
        <div class="laris-features-grid">
            <div class="laris-feature-card">
                <div class="laris-feature-icon"><i class="ti ti-brand-whatsapp"></i></div>
                <h4>Catat via WhatsApp</h4>
                <p>Kirim pesan seperti 'jual kopi 50rb' lewat WA — AI langsung catat ke Buku Kas.</p>
            </div>

            <div class="laris-feature-card">
                <div class="laris-feature-icon"><i class="ti ti-robot"></i></div>
                <h4>Asisten Multi-Agent</h4>
                <p>Admin AI kelola ringkasan & stok. Logistik AI kasih rekomendasi PO otomatis.</p>
            </div>

            <div class="laris-feature-card">
                <div class="laris-feature-icon"><i class="ti ti-chart-bar"></i></div>
                <h4>Dashboard Real-Time</h4>
                <p>Pantau omzet, laba, dan stok UMKM di satu layar Dasher yang modern.</p>
            </div>

            <div class="laris-feature-card">
                <div class="laris-feature-icon"><i class="ti ti-shield-check"></i></div>
                <h4>Multi-Tenant Aman</h4>
                <p>RLS Supabase: tiap toko hanya lihat data sendiri. Owner tenang.</p>
            </div>

            <div class="laris-feature-card">
                <div class="laris-feature-icon"><i class="ti ti-bolt"></i></div>
                <h4>Auto-Restock</h4>
                <p>AI kasih peringatan ketika stok produk menyentuh ambang minimum.</p>
            </div>

            <div class="laris-feature-card">
                <div class="laris-feature-icon"><i class="ti ti-report-money"></i></div>
                <h4>Laporan KUR</h4>
                <p>Ringkasan otomatis untuk pengajuan Kredit Usaha Rakyat ke bank.</p>
            </div>
        </div>
      </div>
    </section>
    """


def _3d_lab_html() -> str:
    """Section 3D interaktif — butuh file /static/laris-3d/koin_3d.html di hosting."""
    return """
    <section class="laris-3d-lab" id="3d">
      <div class="laris-section-inner">
        <div class="laris-section-head">
          <span class="laris-pill laris-pill-soft">Lab Pengetahuan 3D</span>
          <h2>Belajar Bisnis UMKM dengan Visual Interaktif.</h2>
          <p>Drag untuk memutar · Scroll untuk zoom · Klik koin untuk melihat insight dari data UMKM.</p>
        </div>
        <div class="laris-3d-frame">
          <iframe src="/laris-3d/koin_3d.html" title="Koin Pengetahuan UMKM 3D" loading="lazy"></iframe>
        </div>
        <p class="laris-3d-caption">Snippet ringan &lt; 200KB · Three.js via CDN · tidak mengganggu loading landing.</p>
      </div>
    </section>
    """


def _3d_alur_html() -> str:
    """Section diagram alur 3D — butuh file /static/laris-3d/alur_3d.html."""
    return """
    <section class="laris-3d-alur" id="alur-3d">
      <div class="laris-section-inner">
        <div class="laris-section-head">
          <span class="laris-pill laris-pill-soft">Alur Data 3D</span>
          <h2>Lihat data mengalir dari chat WhatsApp ke dashboard bisnis Anda.</h2>
          <p>Drag untuk memutar · Scroll untuk zoom · Klik node untuk melihat penjelasan tiap tahap.</p>
        </div>
        <div class="laris-3d-frame laris-3d-frame-dark">
          <iframe src="/laris-3d/alur_3d.html" title="Alur Data UMKM 3D" loading="lazy"></iframe>
        </div>
        <p class="laris-3d-caption">4 node · 3 jalur data · ~120 partikel hidup. Bukti teknis alur AI multi-agent laris.AI.</p>
      </div>
    </section>
    """


def _3d_stok_html() -> str:
    """Section rak stok 3D — butuh file /static/laris-3d/stok_3d.html."""
    return """
    <section class="laris-3d-stok" id="stok-3d">
      <div class="laris-section-inner">
        <div class="laris-section-head">
          <span class="laris-pill laris-pill-soft">Rak Stok 3D</span>
          <h2>Pantau stok UMKM dari sudut manapun.</h2>
          <p>Drag untuk memutar · Scroll untuk zoom · Klik kotak untuk lihat detail barang & status stok.</p>
        </div>
        <div class="laris-3d-frame laris-3d-frame-warm">
          <iframe src="/laris-3d/stok_3d.html" title="Rak Stok UMKM 3D" loading="lazy"></iframe>
        </div>
        <p class="laris-3d-caption">60 slot produk · 4 kategori · highlight otomatis untuk stok menipis.</p>
      </div>
    </section>
    """


def _3d_omzet_html() -> str:
    """Section grafik omzet 3D — butuh file /static/laris-3d/omzet_3d.html."""
    return """
    <section class="laris-3d-omzet" id="omzet-3d">
      <div class="laris-section-inner">
        <div class="laris-section-head">
          <span class="laris-pill laris-pill-soft">Grafik Omzet 3D</span>
          <h2>Visualisasikan omzet bisnis Anda dalam 3D.</h2>
          <p>Drag untuk memutar · Scroll untuk zoom · Toggle 7/30 hari · Klik bar untuk lihat nominal.</p>
        </div>
        <div class="laris-3d-frame laris-3d-frame-cool">
          <iframe src="/laris-3d/omzet_3d.html" title="Grafik Omzet UMKM 3D" loading="lazy"></iframe>
        </div>
        <p class="laris-3d-caption">Animasi bar tumbuh · 7 & 30 hari · statistik otomatis (total, rata-rata, puncak, tren).</p>
      </div>
    </section>
    """


def _flow_html() -> str:
    steps = [
        ("ti-message-circle", "01", "Owner kirim pesan WA", "Bisa bahasa sehari-hari: 'beli kopi 50rb'."),
        ("ti-robot", "02", "AI parsing transaksi", "Admin AI parsing kategori, nominal, dan tanggal."),
        ("ti-database", "03", "Tercatat di Supabase", "RLS memastikan hanya owner toko itu yang bisa lihat."),
        ("ti-chart-area", "04", "Dashboard Dasher realtime", "Statistik, AI Insight, dan Saran Restock terisi otomatis."),
    ]
    items = "".join(
        f"""
        <div class="laris-flow-item">
            <div class="laris-flow-step"><span>{n}</span><i class="ti {icon}"></i></div>
            <h5>{title}</h5>
            <p>{desc}</p>
        </div>
        """
        for icon, n, title, desc in steps
    )
    return f"""
    <section class="laris-flow" id="alur">
      <div class="laris-section-inner">
        <div class="laris-section-head">
          <span class="laris-pill laris-pill-soft">Alur kerja</span>
          <h2>Dari chat WhatsApp ke dashboard bisnis dalam 4 langkah.</h2>
          <p>Tanpa install, tanpa training — langsung pakai.</p>
        </div>
        <div class="laris-flow-grid">{items}</div>
      </div>
    </section>
    """


def _cta_html() -> str:
    return f"""
    <section class="laris-cta" id="cta">
      <div class="laris-section-inner">
        <div class="laris-cta-card">
          <div>
            <span class="laris-pill">Mulai sekarang</span>
            <h2>Siap naik kelas dengan AI?</h2>
            <p>Coba dashboard contoh publik atau masuk dengan akun toko Anda.</p>
          </div>
          <div class="laris-cta-buttons">
            <a href="{APP_DOMAIN}/?demo=1" target="_blank" rel="noopener" class="btn btn-solid btn-lg">
              <i class="ti ti-flask"></i> Buka Dashboard Demo
            </a>
            <a href="{APP_DOMAIN}/?login=1" target="_blank" rel="noopener" class="btn btn-ghost btn-lg">
              <i class="ti ti-login"></i> Masuk Akun
            </a>
          </div>
        </div>
      </div>
    </section>
    """


def _footer_html() -> str:
    return f"""
    <footer class="laris-footer">
      <div class="laris-section-inner laris-footer-inner">
        <div class="laris-footer-col">
          <strong>{APP_NAME}</strong>
          <p class="text-muted small mb-0">Partner AI untuk UMKM Indonesia.</p>
        </div>
        <div class="laris-footer-col">
          <small class="text-uppercase fw-bold text-muted">Produk</small>
          <a href="#fitur">Fitur</a>
          <a href="#alur">Alur</a>
          <a href="{APP_DOMAIN}/?demo=1" target="_blank" rel="noopener">Demo Publik</a>
          <a href="{LANDING_DOMAIN}/artikel/cara-mencatat-keuangan-warung/" target="_blank" rel="noopener">Artikel UMKM</a>
        </div>
        <div class="laris-footer-col">
          <small class="text-uppercase fw-bold text-muted">Mulai</small>
          <a href="{APP_DOMAIN}/?login=1" target="_blank" rel="noopener">Masuk</a>
          <a href="{APP_DOMAIN}/?demo=1" target="_blank" rel="noopener">Coba Demo</a>
        </div>
      </div>
      <div class="text-center text-muted small py-3">
        © 2026 {APP_NAME} — Partner Bisnis UMKM Indonesia.
      </div>
    </footer>
    """


def render_landing() -> None:
    """Beranda marketing full — 1 halaman utuh, semua HTML."""
    st.markdown(
        "<style>"
        "header[data-testid='stHeader'] { display: none !important; }"
        "footer { visibility: hidden; }"
        ".block-container { padding: 0 !important; max-width: 100% !important; }"
        "</style>",
        unsafe_allow_html=True,
    )

    parts = [
        _navbar_html(),
        _hero_html(),
        _stats_html(),
        _features_html(),
        _3d_lab_html(),
        _3d_alur_html(),
        _3d_stok_html(),
        _3d_omzet_html(),
        _flow_html(),
        _cta_html(),
        _footer_html(),
    ]
    html_content = textwrap.dedent("".join(parts))
    full_doc = f"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.47.0/tabler-icons.min.css">
  <style>{_INLINE_LANDING_CSS}</style>
</head>
<body>
  <div class="laris-landing">{html_content}</div>
</body>
</html>"""
    components.html(full_doc, height=5200, scrolling=True)


def render_landing_fallback() -> None:
    render_landing()
