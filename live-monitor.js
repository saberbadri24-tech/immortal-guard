/* Immortal Guard X — live opportunity and receipt monitor.
   Read-only: discovers opportunities, verifies public wallet activity, and queues owner review.
   No seed phrase, private key, automatic claim, or automatic transfer. */

(function () {
  const API = 'https://tonapi.io/v2';
  const REFRESH = 60000;
  const MAIN_KEY = 'ig_main_ton_address';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (m) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]);
    });
  }

  function short(a) {
    return a && a.length > 18 ? a.slice(0, 9) + '…' + a.slice(-7) : (a || '—');
  }

  function ton(n) {
    return (Number(n || 0) / 1e9).toFixed(9);
  }

  async function get(path) {
    const r = await fetch(API + path, { cache: 'no-store' });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }

  function panel() {
    if (document.getElementById('ig-live-monitor')) return;
    const host = document.getElementById('ton-transfer');
    if (!host) return;
    const el = document.createElement('section');
    el.id = 'ig-live-monitor';
    el.className = 'card';
    el.style.marginTop = '14px';
    el.innerHTML =
      '<h2>⚡ پایش زنده گارد</h2>' +
      '<div id="ig-live-status" class="notice">در انتظار اتصال کیف دریافت...</div>' +
      '<div id="ig-live-assets" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px;margin-top:12px"></div>' +
      '<div id="ig-live-opportunities" class="transfer-status" style="margin-top:12px"></div>' +
      '<div class="transfer-status">گارد فرصت‌ها را خودکار پیدا و دسته‌بندی می‌کند؛ Claimهای نیازمند امضا، KYC یا CAPTCHA فقط به صف تأیید مالک می‌روند.</div>';
    host.parentNode.insertBefore(el, host.nextSibling);
  }

  function status(html, ok) {
    const el = document.getElementById('ig-live-status');
    if (!el) return;
    el.className = ok ? 'transfer-status success' : 'notice';
    el.innerHTML = html;
  }

  async function scanWallet() {
    panel();
    const wallet = window.tonWallet;
    const address = wallet && wallet.account && wallet.account.address;
    if (!address) {
      status('کیف دریافت هنوز متصل نیست. برای پایش زنده، کیف دریافت را با TON Connect وصل کن.', false);
      return;
    }

    status('در حال بررسی زنده موجودی و دارایی‌ها…', false);
    try {
      const account = await get('/accounts/' + encodeURIComponent(address));
      const jets = await get('/accounts/' + encodeURIComponent(address) + '/jettons');
      const list = Array.isArray(jets.balances) ? jets.balances : [];
      const assets = [
        '<div class="card"><div class="chip">TON MAINNET</div><h3>TON</h3><div class="score">' +
        esc(ton(account.balance)) + '</div><p>موجودی زنده</p></div>'
      ];

      list.slice(0, 24).forEach(function (x) {
        const meta = x.jetton || {};
        const decimals = Number(meta.decimals == null ? 9 : meta.decimals);
        const value = Number(x.balance || 0) / Math.pow(10, decimals);
        const symbol = meta.symbol || meta.name || 'JETTON';
        assets.push(
          '<div class="card"><div class="chip">JETTON</div><h3>' +
          esc(symbol) + '</h3><div class="score">' +
          esc(value.toLocaleString(undefined, { maximumFractionDigits: 6 })) +
          '</div><p>' + esc(meta.name || '') + '</p></div>'
        );
      });

      document.getElementById('ig-live-assets').innerHTML = assets.join('');
      status(
        'پایش زنده فعال است · کیف: <b>' + esc(short(address)) +
        '</b> · TON: <b>' + esc(ton(account.balance)) +
        '</b> · Jettonها: <b>' + list.length + '</b> · ' +
        new Date().toLocaleTimeString('fa-IR'),
        true
      );
      scanOpportunities();
    } catch (e) {
      status('پایش زنده با خطا روبه‌رو شد: <b>' + esc(e.message || e) + '</b>', false);
    }
  }

  function scanOpportunities() {
    const box = document.getElementById('ig-live-opportunities');
    if (!box || !Array.isArray(window.data)) return;

    const candidates = window.data
      .filter(function (x) {
        return x && x.url && /^https:\/\//i.test(x.url) &&
          x.status !== 'blocked' && Number(x.score || 0) >= 60;
      })
      .sort(function (a, b) { return Number(b.score || 0) - Number(a.score || 0); })
      .slice(0, 12);

    box.innerHTML =
      '<b>صف بررسی فرصت‌های فعال:</b> ' + candidates.length +
      ' · فرصت تکراری یا مسدود حذف می‌شود.' +
      '<div style="display:flex;gap:7px;flex-wrap:wrap;margin-top:9px">' +
      candidates.slice(0, 6).map(function (x) {
        return '<a class="btn" href="' + esc(x.url) +
          '" target="_blank" rel="noopener noreferrer">بررسی ' +
          esc(x.title).slice(0, 40) + ' ↗</a>';
      }).join('') + '</div>';
  }

  window.IGLiveMonitor = { scanWallet: scanWallet, scanOpportunities: scanOpportunities };

  function start() {
    panel();
    setTimeout(scanWallet, 1200);
    setInterval(scanWallet, REFRESH);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();