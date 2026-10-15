(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  // Keep the two learning panels directly below the graph easy to discover.
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-learning-target]');
    if (!button) return;
    const panel = $(button.dataset.learningTarget);
    if (!panel) return;
    const opening = panel.hidden;
    document.querySelectorAll('[data-learning-target]').forEach(control => {
      const relatedPanel = $(control.dataset.learningTarget);
      const expanded = control === button && opening;
      control.setAttribute('aria-expanded', String(expanded));
      if (relatedPanel) relatedPanel.hidden = !expanded;
    });
  });
  const screen = $('auth-screen');
  let mode = 'signin';
  let finishAuth;
  let redrawAuthSculpture = () => {};
  let stopAuthSculpture = () => {};

  // One shared theme setting keeps the login screen and route dashboard in sync.
  const themeMedia = window.matchMedia('(prefers-color-scheme: light)');
  function updateThemeButtons() {
    const light = document.body.classList.contains('light');
    const themeColor = document.querySelector('meta[name="theme-color"]');
    if (themeColor) themeColor.content = light ? '#edf7f2' : '#0b161a';
    [['auth-theme-toggle', light], ['btn-theme', light]].forEach(([id, isLight]) => {
      const button = $(id);
      if (!button) return;
      button.textContent = isLight ? '☾' : '☼';
      button.setAttribute('aria-label', isLight ? 'Switch to dark theme' : 'Switch to light theme');
      button.title = isLight ? 'Switch to dark theme' : 'Switch to light theme';
    });
  }
  function setTheme(light, save = false) {
    document.body.classList.toggle('light', light);
    if (save) {
      try { localStorage.setItem('coolroute-theme', light ? 'light' : 'dark'); } catch (_) {}
    }
    updateThemeButtons();
    updateMapTheme(light);
    redrawAuthSculpture();
  }
  updateThemeButtons();
  $('auth-theme-toggle')?.addEventListener('click', () => setTheme(!document.body.classList.contains('light'), true));
  $('btn-theme')?.addEventListener('click', () => setTheme(!document.body.classList.contains('light'), true));
  themeMedia.addEventListener?.('change', event => {
    let saved = null;
    try { saved = localStorage.getItem('coolroute-theme'); } catch (_) {}
    if (!saved) setTheme(event.matches);
  });

  // Dense flowing particle lettering and orbiting dust, drawn locally on canvas.
  function initAuthSculpture() {
    const canvas = $('auth-ambient-canvas');
    const ctx = canvas?.getContext('2d', { alpha: true });
    if (!canvas || !ctx) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const pointer = { x: -10000, y: -10000 };
    const dust = Array.from({ length: 260 }, () => ({
      x: Math.random(), y: Math.random(), phase: Math.random() * Math.PI * 2,
      size: .35 + Math.random() * 1.25, speed: .12 + Math.random() * .5,
    }));
    let particles = [], width = 0, height = 0, frame = 0, raf = 0, lastDraw = 0;

    function resize() {
      const box = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = box.width; height = box.height;
      canvas.width = Math.round(width * dpr); canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const sampler = document.createElement('canvas');
      sampler.width = Math.ceil(width); sampler.height = Math.ceil(height);
      const ink = sampler.getContext('2d', { willReadFrequently: true });
      const mobile = width < 700;
      const fontSize = Math.min(mobile ? width * .19 : width * .155, height * .24, 230);
      ink.clearRect(0, 0, sampler.width, sampler.height);
      ink.fillStyle = '#fff';
      ink.font = `800 ${fontSize}px system-ui, sans-serif`;
      ink.textAlign = 'center'; ink.textBaseline = 'middle';
      ink.fillText('CoolRoute', width * .52, height * (mobile ? .76 : .73), width * .88);
      const pixels = ink.getImageData(0, 0, sampler.width, sampler.height).data;
      const targets = [];
      const stride = mobile ? 4 : 4;
      for (let y = 0; y < sampler.height; y += stride) {
        for (let x = 0; x < sampler.width; x += stride) {
          if (pixels[(y * sampler.width + x) * 4 + 3] > 110) targets.push([x, y]);
        }
      }
      // Bound canvas work on large screens while keeping the text dense.
      const maxTextDots = 1050;
      const hop = Math.max(1, Math.ceil(targets.length / maxTextDots));
      particles = targets.filter((_, i) => i % hop === 0).map(([x, y]) => ({
        x, y, phase: Math.random() * Math.PI * 2, size: .55 + Math.random() * 1.1, kind: 0,
      }));
      for (let i = 0; i < 290; i++) {
        const angle = Math.random() * Math.PI * 2;
        particles.push({
          angle, phase: Math.random() * Math.PI * 2,
          rx: width * (.13 + Math.random() * .37), ry: height * (.06 + Math.random() * .21),
          cx: width * (.48 + (Math.random() - .5) * .18), cy: height * (.72 + (Math.random() - .5) * .10),
          size: .45 + Math.random() * 1.35, speed: (Math.random() < .5 ? -1 : 1) * (.025 + Math.random() * .045), kind: 1,
        });
      }
      if (reduced) draw();
    }

    function draw() {
      if (!width || !height) return;
      const t = reduced ? 0 : frame * .016;
      const light = document.body.classList.contains('light');
      const particleColor = light ? '30,54,49' : '129,238,210';
      const accentColor = light ? '44,126,103' : '255,181,112';
      ctx.clearRect(0, 0, width, height);
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;

      for (const p of particles) {
        let x, y;
        if (p.kind === 0) {
          const drift = reduced ? 0 : Math.sin(t * .55 + p.phase) * 3.2;
          x = p.x + drift;
          y = p.y + (reduced ? 0 : Math.cos(t * .43 + p.phase) * 3.2);
        } else {
          const a = p.angle + t * p.speed;
          x = p.cx + Math.cos(a) * p.rx + Math.sin(a * 2 + p.phase) * 9;
          y = p.cy + Math.sin(a) * p.ry + Math.cos(a * 1.7 + p.phase) * 7;
        }
        const dx = x - pointer.x, dy = y - pointer.y;
        const d2 = dx * dx + dy * dy;
        const push = reduced ? 0 : Math.exp(-d2 / 8000) * (p.kind ? 17 : 11);
        const inv = 1 / Math.sqrt(d2 + 1);
        x += dx * inv * push; y += dy * inv * push;
        ctx.beginPath();
        ctx.arc(x, y, p.size, 0, Math.PI * 2);
        const twinkle = .48 + .35 * (Math.sin(t * 1.2 + p.phase) + 1) / 2;
        const accent = p.kind === 1 && Math.sin(p.phase * 2) > .72;
        ctx.fillStyle = `rgba(${accent ? accentColor : particleColor},${light ? twinkle * .30 : twinkle * .40})`;
        ctx.fill();
      }
      for (const p of dust) {
        const x = (p.x * width + (reduced ? 0 : t * p.speed * 8)) % width;
        const y = p.y * height + (reduced ? 0 : Math.sin(t * .45 + p.phase) * 8);
        const dx = x - pointer.x, dy = y - pointer.y, d = Math.sqrt(dx * dx + dy * dy) + 1;
        const push = reduced ? 0 : Math.exp(-(d * d) / 6500) * 14;
        ctx.beginPath(); ctx.arc(x + dx / d * push, y + dy / d * push, p.size, 0, Math.PI * 2);
        ctx.fillStyle = light ? 'rgba(35,61,55,.20)' : 'rgba(139,218,198,.22)'; ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    redrawAuthSculpture = draw;
    const animate = timestamp => {
      if (timestamp - lastDraw >= 33) { frame++; draw(); lastDraw = timestamp; }
      raf = window.requestAnimationFrame(animate);
    };
    stopAuthSculpture = () => window.cancelAnimationFrame(raf);
    document.addEventListener('pointermove', event => {
      pointer.x = event.clientX; pointer.y = event.clientY;
    }, { passive: true });
    window.addEventListener('resize', resize, { passive: true });
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) window.cancelAnimationFrame(raf);
      else if (!reduced) animate(performance.now());
    });
    resize();
    if (!reduced) animate(performance.now());
  }
  initAuthSculpture();

  window.coolrouteAuthReady = new Promise(resolve => { finishAuth = resolve; });
  window.coolrouteAuthUser = null;

  // Give pointer-capable screens a quiet, responsive glow and tactile button feedback.
  document.addEventListener('pointermove', event => {
    if (event.pointerType === 'touch') return;
    document.documentElement.style.setProperty('--pointer-x', `${event.clientX}px`);
    document.documentElement.style.setProperty('--pointer-y', `${event.clientY}px`);
  }, { passive: true });
  document.addEventListener('click', event => {
    const button = event.target.closest('button:not(:disabled)');
    if (!button) return;
    button.classList.remove('ui-pressed');
    void button.offsetWidth;
    button.classList.add('ui-pressed');
    window.setTimeout(() => button.classList.remove('ui-pressed'), 360);
  });

  function unlock(user) {
    stopAuthSculpture();
    window.coolrouteAuthUser = user;
    document.body.classList.add('app-authenticated');
    screen.setAttribute('aria-hidden', 'true');
    const account = $('account-email');
    if (account && user?.email) { account.textContent = user.email; account.hidden = false; }
    finishAuth(true);
  }

  function showError(message, success = false) {
    const box = $('auth-feedback');
    box.textContent = message;
    box.classList.toggle('success', success);
  }

  function setMode(next) {
    mode = next;
    const signup = mode === 'signup';
    $('tab-signin').classList.toggle('active', !signup);
    $('tab-signup').classList.toggle('active', signup);
    $('tab-signin').setAttribute('aria-selected', String(!signup));
    $('tab-signup').setAttribute('aria-selected', String(signup));
    $('auth-title').textContent = signup ? 'Create your account' : 'Welcome back';
    $('auth-subtitle').textContent = signup
      ? 'One account unlocks your personal route dashboard.'
      : 'Sign in to open your route dashboard.';
    $('auth-submit-label').textContent = signup ? 'Create account' : 'Sign in';
    $('auth-password').setAttribute('autocomplete', signup ? 'new-password' : 'current-password');
    $('auth-password').setAttribute('minlength', signup ? '10' : '1');
    $('auth-password').placeholder = signup ? 'At least 10 characters' : 'Your password';
    $('auth-confirm-row').hidden = !signup;
    $('auth-confirm').required = signup;
    showError('');
  }

  async function authRequest(path, data) {
    const response = await fetch(path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin', body: JSON.stringify(data),
    });
    const raw = await response.text();
    let result;
    try { result = raw ? JSON.parse(raw) : {}; }
    catch (_) { throw new Error('This page is not connected to the CoolRoute backend. Start start_windows.bat and open the exact URL it prints (it may be port 8766).'); }
    if (!response.ok) throw new Error(result.error?.message || `Account request failed (${response.status}).`);
    return result;
  }

  $('tab-signin').addEventListener('click', () => setMode('signin'));
  $('tab-signup').addEventListener('click', () => setMode('signup'));
  $('auth-show-password').addEventListener('click', () => {
    const input = $('auth-password');
    const showing = input.type === 'text';
    input.type = showing ? 'password' : 'text';
    $('auth-show-password').textContent = showing ? 'Show' : 'Hide';
    $('auth-show-password').setAttribute('aria-label', showing ? 'Show password' : 'Hide password');
  });

  $('auth-form').addEventListener('submit', async event => {
    event.preventDefault();
    const email = $('auth-email').value.trim();
    const password = $('auth-password').value;
    if (!$('auth-email').reportValidity() || !$('auth-password').reportValidity()) return;
    if (mode === 'signup' && $('auth-confirm').value !== password) {
      showError('Those passwords do not match.');
      $('auth-confirm').focus();
      return;
    }
    const button = $('auth-submit');
    button.disabled = true;
    showError(mode === 'signup' ? 'Creating your secure local account…' : 'Signing you in…', true);
    try {
      const result = await authRequest(
        mode === 'signup' ? 'api/v1/auth/signup' : 'api/v1/auth/signin',
        { email, password });
      unlock(result);
    } catch (error) {
      showError(error.message || 'Could not connect to the account service.');
    } finally {
      button.disabled = false;
    }
  });

  $('btn-signout').addEventListener('click', async () => {
    try { await fetch('api/v1/auth/signout', { method: 'POST', credentials: 'same-origin' }); }
    finally { window.location.reload(); }
  });

  (async () => {
    try {
      const response = await fetch('api/v1/auth/me', { credentials: 'same-origin' });
      if (!response.ok) throw new Error('CoolRoute backend unavailable');
      const user = await response.json();
      if (user.authenticated) unlock(user);
      else showError('Sign in or create a local account to continue.');
    } catch (_) {
      showError('Backend not connected. Start start_windows.bat and open the exact URL it prints (not an old 8765 tab).');
    }
  })();
})();

/**
 * CoolRoute frontend — fully resilient, always-interactive map.
 * All assets served locally — no CDN required.
 */
 (async () => {
  'use strict';

  if (!await window.coolrouteAuthReady) return;

  // Tell Leaflet where its marker/layer images are (served locally at /images/)
  L.Icon.Default.imagePath = './images/';

  /* ── DOM helper ─────────────────────────────────────────────────── */
  const $ = id => document.getElementById(id);

  /* ── State ──────────────────────────────────────────────────────── */
  const S = {
    mode:         'origin',   // 'origin' | 'destination' | 'close'
    origin:       null,       // { lat, lon }
    destination:  null,       // { lat, lon }
    area:         null,       // area_data result (null until Overpass responds)
    graph:        null,       // graph_from_area result
    markers:      {},         // { origin: L.Marker, destination: L.Marker }
    routeLayers:  [],         // drawn route polylines
    streetLines:  [],         // edge-id → L.Polyline
    closedEdges:  new Set(),
    loadTimer:    null,
    retryTimer:   null,
    retryCount:   0,
    areaLoading:  false,
    areaQueued:   false,
  };

  /* ── Formatters ─────────────────────────────────────────────────── */
  const fmtM   = m => m >= 1000 ? `${(m/1000).toFixed(1)} km` : `${Math.round(m)} m`;
  const fmtMin = t => `${t.toFixed(0)} min`;
  const fmtH   = h => `${h % 12 || 12}:00 ${h >= 12 ? 'PM' : 'AM'}`;
  const fmtPct = n => `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`;

  /* ── Status bar ─────────────────────────────────────────────────── */
  function setStatus(text, cls = '') {
    $('status-text').textContent = text;
    $('status-badge').className  = 'status-badge ' + cls;
  }

  /* ── Map foot hint ──────────────────────────────────────────────── */
  function setHint(text) { $('map-foot-hint').textContent = text; }

  /* ── Map overlay (non-blocking, auto-hides) ─────────────────────── */
  let _overlayTimer = null;
  function showOverlay(text, autohide = 0) {
    const el = $('map-overlay');
    el.textContent = text;
    el.hidden      = false;
    clearTimeout(_overlayTimer);
    if (autohide > 0) _overlayTimer = setTimeout(() => { el.hidden = true; }, autohide);
  }
  function hideOverlay() {
    clearTimeout(_overlayTimer);
    $('map-overlay').hidden = true;
  }

  /* ── API fetch ──────────────────────────────────────────────────── */
  async function apiFetch(url, opts) {
    const r = await fetch(url, opts);
    if (r.status === 401) { window.location.reload(); throw new Error('Your session expired. Sign in again.'); }
    const body = await r.text();
    let d;
    try { d = body ? JSON.parse(body) : {}; }
    catch (_) { throw new Error(`Server returned an unreadable response (${r.status}). Restart CoolRoute and try again.`); }
    if (!r.ok) throw new Error(d.error?.message || `Server error ${r.status}`);
    return d;
  }

  let historyHasMore = false;
  let historyLoading = false;
  async function loadRouteHistory(append = false) {
    if (historyLoading) return;
    historyLoading = true;
    const list = $('history-list');
    const offset = append ? list.childElementCount : 0;
    if (!append) list.replaceChildren();
    $('history-status').textContent = append ? 'Loading older walks…' : 'Loading saved walks…';
    try {
      const result = await apiFetch(`api/v1/history?limit=50&offset=${offset}`);
      (result.history || []).forEach(item => {
        const card = document.createElement('article');
        card.className = 'history-item';
        const summary = document.createElement('div');
        summary.className = 'history-route';
        summary.append(document.createTextNode(`${item.origin_label} → ${item.destination_label}`));
        const time = new Date(item.saved_at * 1000).toLocaleString();
        const best = item.metrics?.coolroute?.distance_m != null
          ? ` · CoolRoute ${fmtM(item.metrics.coolroute.distance_m)}`
          : item.metrics?.shortest?.distance_m != null ? ` · ${fmtM(item.metrics.shortest.distance_m)}` : '';
        const detail = document.createElement('small');
        detail.textContent = `${time}${item.city ? ` · ${item.city}` : ''}${best}`;
        summary.append(detail);
        const reuse = document.createElement('button');
        reuse.type = 'button'; reuse.className = 'history-reuse'; reuse.textContent = 'Use route';
        reuse.addEventListener('click', () => {
          placePin('origin', { ...item.origin, label: item.origin_label });
          placePin('destination', { ...item.destination, label: item.destination_label });
          map.fitBounds([[item.origin.lat, item.origin.lon], [item.destination.lat, item.destination.lon]], { padding: [45, 45], maxZoom: 16 });
          setMode('origin');
          $('history-status').textContent = 'Saved start and destination restored. Click Find my cooler route to plan again.';
        });
        card.append(summary, reuse); list.append(card);
      });
      historyHasMore = Boolean(result.has_more);
      $('btn-history-more').hidden = !historyHasMore;
      $('history-status').textContent = list.childElementCount
        ? `${list.childElementCount} saved walk${list.childElementCount === 1 ? '' : 's'} shown${historyHasMore ? ' · more available' : ''}.`
        : 'No saved walks yet. Plan a route and it will be kept here.';
    } catch (error) {
      $('history-status').textContent = `History could not load: ${error.message}`;
      $('btn-history-more').hidden = true;
    } finally { historyLoading = false; }
  }

  async function saveRouteHistory(routeKey, shortest, coolroute = null, context) {
    try {
      await apiFetch('api/v1/history', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          route_key: routeKey,
          origin: context.origin,
          destination: context.destination,
          origin_label: context.origin_label,
          destination_label: context.destination_label,
          city: context.city,
          preferences: context.preferences,
          shortest, coolroute,
        }),
      });
      await loadRouteHistory(false);
    } catch (error) {
      $('history-status').textContent = `Walk could not be saved: ${error.message}`;
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     MAP SETUP — tiles load immediately, no dependency on Overpass
  ═══════════════════════════════════════════════════════════════════ */
  // Canvas rendering keeps dense OSM street overlays responsive in the browser.
  const map = L.map('map', { zoomControl: false, preferCanvas: true }).setView([26.9124, 75.7873], 15);
  function updateMapTheme(light = document.body.classList.contains('light')) {
    map.getContainer().classList.toggle('map-dark', !light);
  }
  updateMapTheme();
  L.control.zoom({ position: 'bottomright' }).addTo(map);
  const tileSources = [
    {
      name: 'OpenStreetMap',
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    },
    {
      name: 'OpenStreetMap HOT',
      url: 'https://tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, style by <a href="https://www.hotosm.org/">HOT</a>',
    },
    {
      name: 'OpenStreetMap Germany',
      url: 'https://tile.openstreetmap.de/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    },
    {
      name: 'Satellite imagery',
      kind: 'satellite',
      url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: 'Imagery &copy; Esri, Maxar, Earthstar Geographics, and the GIS User Community',
    },
  ];
  const satelliteTileIndex = 3;
  let tileSourceIndex = 0;
  let tileErrorCount = 0;
  let tileLayer = null;
  let tileFallbackTimer = null;

  function advanceTileSource() {
    if (tileSourceIndex + 1 < tileSources.length) {
      const next = tileSourceIndex + 1;
      setHint(`Trying backup map tiles: ${tileSources[next].name}…`);
      useTileSource(next);
      return;
    }
    setHint('Map tiles are unavailable. You can still set points; street lines will show when street data loads.');
    showOverlay('Map backgrounds are unavailable — check your internet connection.', 5000);
  }

  function useTileSource(index) {
    if (tileLayer) map.removeLayer(tileLayer);
    clearTimeout(tileFallbackTimer);
    tileSourceIndex = index;
    const isSatellite = tileSources[index].kind === 'satellite';
    map.getContainer().classList.toggle('map-satellite', isSatellite);
    [['btn-map-street', !isSatellite], ['btn-map-satellite', isSatellite]].forEach(([id, active]) => {
      const button = $(id);
      if (!button) return;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    tileErrorCount = 0;
    let receivedTile = false;
    const layer = L.tileLayer(tileSources[index].url, {
      maxZoom: 19,
      attribution: tileSources[index].attribution,
      updateWhenIdle: true,
      keepBuffer: 2,
    });
    tileLayer = layer;
    layer.on('tileload', () => { receivedTile = true; });
    layer.on('tileerror', () => {
      if (receivedTile || tileLayer !== layer) return;
      tileErrorCount++;
      if (tileErrorCount >= 4) advanceTileSource();
    });
    layer.addTo(map);
    tileFallbackTimer = setTimeout(() => {
      if (tileLayer === layer && !receivedTile) advanceTileSource();
    }, 7000);
  }

  useTileSource(0);
  // Host previews can finish sizing their panel after Leaflet initializes.
  requestAnimationFrame(() => map.invalidateSize({ pan: false }));
  setTimeout(() => map.invalidateSize({ pan: false }), 250);
  window.addEventListener('resize', () => map.invalidateSize({ pan: false }));

  const streetLayer = L.layerGroup().addTo(map);
  const treeLayer   = L.layerGroup().addTo(map);

  function pinIcon(color, size = 16) {
    return L.divIcon({
      className: '',
      html: `<span style="display:block;width:${size}px;height:${size}px;background:${color};`+
            `border:3px solid #fff;border-radius:50%;box-shadow:0 2px 10px rgba(0,0,0,.55)"></span>`,
      iconSize:   [size, size],
      iconAnchor: [size/2, size/2],
    });
  }

  /* ═══════════════════════════════════════════════════════════════════
     MODE MANAGEMENT
  ═══════════════════════════════════════════════════════════════════ */
  function setMode(mode) {
    S.mode = mode;
    document.querySelectorAll('.seg-btn').forEach(b => {
      const on = b.dataset.mode === mode;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    const hints = {
      origin:      'Click anywhere on the map to set your START point',
      destination: 'Click anywhere on the map to set your DESTINATION',
      close:       'Click a street segment to close or reopen it',
    };
    setHint(hints[mode] || '');
    if (mode !== 'close') showOverlay(hints[mode], 2500);
  }

  /* ═══════════════════════════════════════════════════════════════════
     PLACE PIN — works immediately on any map click, no streets needed
  ═══════════════════════════════════════════════════════════════════ */
  function placePin(which, point) {
    point = { ...point, label: point.label || `${point.lat.toFixed(5)}, ${point.lon.toFixed(5)}` };
    S[which] = point;
    const inputId = which === 'origin' ? 'origin-input' : 'dest-input';
    $(inputId).value = point.label;

    if (S.markers[which]) map.removeLayer(S.markers[which]);
    const color = which === 'origin' ? '#3ed9b6' : '#ff9a5c';
    const tip   = which === 'origin' ? '📍 Start' : '🏁 Destination';
    S.markers[which] = L.marker([point.lat, point.lon], { icon: pinIcon(color, 18) })
      .addTo(map)
      .bindTooltip(tip, { direction: 'top' });

    if (S.origin && S.destination) {
      $('verdict').textContent = 'Both points set — click "Find my cooler route" below.';
      $('verdict').classList.remove('has-result');
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     BOUNDING BOX HELPERS
  ═══════════════════════════════════════════════════════════════════ */
  function currentBbox() {
    const b    = map.getBounds();
    const c    = map.getCenter();
    const half = Math.min(0.008, (b.getNorth()-b.getSouth())/2, (b.getEast()-b.getWest())/2);
    return [
      Math.max(-84.9,  c.lat - half), Math.max(-179.9, c.lng - half),
      Math.min(84.9,   c.lat + half), Math.min(179.9,  c.lng + half),
    ];
  }
  function bboxStr(b) { return b.map(x => x.toFixed(5)).join(','); }

  /* ═══════════════════════════════════════════════════════════════════
     PAINT STREET OVERLAY  (called when Overpass data arrives)
  ═══════════════════════════════════════════════════════════════════ */
  function paintStreets(area) {
    streetLayer.clearLayers();
    treeLayer.clearLayers();
    S.streetLines = [];
    S.closedEdges.clear();
    S.graph = area.graph;

    area.graph.edges.forEach((edge, id) => {
      const shaded = edge.shade >= 0.30;
      const color  = shaded ? '#3ed9b6' : '#6b8f89';
      const wt     = shaded ? 4 : 2.5;
      const src    = edge.shade_sources?.length ? edge.shade_sources.join(', ') : 'no mapped shade';

      const line = L.polyline(edge.geometry.map(p => [p.lat, p.lon]),
        { color, weight: wt, opacity: 0.78 })
        .addTo(streetLayer)
        .bindTooltip(`${edge.name} · ${Math.round(edge.shade*100)}% shade · ${src}`,
                     { sticky: true, direction: 'top' });

      line.on('click', e => {
        if (S.mode !== 'close') return;
        L.DomEvent.stopPropagation(e);
        if (S.closedEdges.has(id)) {
          S.closedEdges.delete(id);
          line.setStyle({ color: shaded ? '#3ed9b6' : '#6b8f89', dashArray: null, weight: wt });
          showOverlay('Street reopened', 1400);
        } else {
          S.closedEdges.add(id);
          line.setStyle({ color: '#ff6b6b', dashArray: '5 8', weight: 4 });
          showOverlay('Street closed for this trip', 1400);
        }
      });
      S.streetLines[id] = line;
    });

    (area.trees || []).slice(0, 800).forEach(p =>
      L.circleMarker([p.lat, p.lon], { radius: 3.5, stroke: false, fillColor: '#5fcc88', fillOpacity: 0.45 })
        .addTo(treeLayer)
    );

    S.area = area;
    setStatus('Streets loaded', 'ready');
    hideOverlay();
  }

  /* ═══════════════════════════════════════════════════════════════════
     LOAD STREET DATA — fully background, never blocks map interaction
  ═══════════════════════════════════════════════════════════════════ */
  async function loadStreets(immediate = false) {
    if (S.areaLoading) { S.areaQueued = true; return; }
    clearTimeout(S.loadTimer);
    clearTimeout(S.retryTimer);
    S.loadTimer = setTimeout(async () => {
      if (S.areaLoading) { S.areaQueued = true; return; }
      S.areaLoading = true;
      setStatus('Loading shade overlay…', 'loading');
      try {
        const box  = currentBbox();
        const area = await apiFetch(`api/v1/real/area?bbox=${encodeURIComponent(bboxStr(box))}`);
        S.retryCount = 0;
        paintStreets(area);
        updateWeather(map.getCenter());
      } catch (e) {
        hideOverlay();
        S.retryCount++;
        const wait = Math.min(30, S.retryCount * 8);
        setStatus(`Map ready · shade data retrying in ${wait}s`, 'ready');
        setHint('Street map is ready. Shade overlays are temporarily unavailable; you can still set points and get walking directions.');
        S.retryTimer = setTimeout(() => loadStreets(true), wait * 1000);
      } finally {
        S.areaLoading = false;
        if (S.areaQueued) { S.areaQueued = false; loadStreets(true); }
      }
    }, immediate ? 100 : 700);
  }

  /* ═══════════════════════════════════════════════════════════════════
     WEATHER
  ═══════════════════════════════════════════════════════════════════ */
  async function updateWeather(center) {
    try {
      const w = await apiFetch(
        `api/v1/real/weather?lat=${center.lat}&lon=${center.lng}&hour=${$('inp-hour').value}`
      );
      $('weather-temp').textContent = w.temperature_c != null ? `${Math.round(w.temperature_c)}°C` : '--°';
      const cloud = w.cloud_cover_pct != null ? `${Math.round(w.cloud_cover_pct)}% cloud` : '';
      const wind  = w.wind_speed_kmh  != null ? `${Math.round(w.wind_speed_kmh)} km/h wind` : '';
      $('weather-sub').textContent = [cloud, wind].filter(Boolean).join(' · ') || 'Forecast';
      const cp = w.cloud_cover_pct ?? 0;
      $('weather-chip').querySelector('.weather-icon').textContent = cp > 70 ? '☁' : cp > 30 ? '⛅' : '☀';
    } catch (_) {
      $('weather-sub').textContent = 'Forecast unavailable';
    }
  }

  /* ═══════════════════════════════════════════════════════════════════
     ROUTE DRAWING HELPERS
  ═══════════════════════════════════════════════════════════════════ */
  function clearRoutes() {
    S.routeLayers.forEach(l => map.removeLayer(l));
    S.routeLayers = [];
  }

  function addWarn(text, type = '') {
    const li = document.createElement('li');
    li.textContent = text;
    if (type) li.className = type;
    $('warnings').appendChild(li);
  }

  function deltaClass(val) {
    return val > 0 ? 'metric-delta positive' : val < 0 ? 'metric-delta negative' : 'metric-delta';
  }

  function renderComparisonGraph(base, cool, status = 'Comparing the two walking options') {
    const series = {
      distance: { a: Number(base.distance_m) || 0, b: Number(cool.distance_m) || 0,
        format: v => `${Math.round(v)} m` },
      time: { a: Number(base.walk_time_min) || 0, b: Number(cool.walk_time_min) || 0,
        format: v => `${v.toFixed(1)} min` },
      shade: { a: (Number(base.shaded_share) || 0) * 100, b: (Number(cool.shaded_share) || 0) * 100,
        format: v => `${Math.round(v)}%` },
      heat: { a: Number(base.heat_exposure) || 0, b: Number(cool.heat_exposure) || 0,
        format: v => `${Math.round(v)}` },
    };
    Object.entries(series).forEach(([key, values]) => {
      const row = document.querySelector(`.graph-row[data-metric="${key}"]`);
      if (!row) return;
      const max = Math.max(values.a, values.b, 1);
      [['short', values.a], ['cool', values.b]].forEach(([name, value]) => {
        const bar = row.querySelector(`.${name}-bar`);
        const label = row.querySelector(`.${name}-value`);
        bar.style.width = `${Math.max(2, value / max * 100)}%`;
        bar.title = `${name === 'short' ? 'Shortest' : 'CoolRoute'}: ${values.format(value)}`;
        label.textContent = values.format(value);
      });
    });
    $('graph-status').textContent = status;
  }

  // Draw useful distance/time information as soon as the street directions
  // endpoint responds. Shade and heat stay explicitly unavailable until the
  // separate shade-aware comparison finishes; never invent those values.
  function renderBaselineGraph(distanceM, walkTimeMin, status) {
    const initial = { distance: [distanceM, v => `${Math.round(v)} m`],
      time: [walkTimeMin, v => `${v.toFixed(1)} min`] };
    document.querySelectorAll('.graph-row').forEach(row => {
      const key = row.dataset.metric;
      const shortBar = row.querySelector('.short-bar');
      const shortValue = row.querySelector('.short-value');
      const coolBar = row.querySelector('.cool-bar');
      const coolValue = row.querySelector('.cool-value');
      const available = initial[key];
      shortBar.style.width = available ? '100%' : '0';
      shortBar.title = available ? `Shortest: ${available[1](available[0])}` : '';
      shortValue.textContent = available ? available[1](available[0]) : 'Needs shade data';
      coolBar.style.width = '0';
      coolBar.removeAttribute('title');
      coolValue.textContent = '—';
    });
    $('graph-status').textContent = status;
  }

  function clearComparisonGraph(status) {
    document.querySelectorAll('.graph-bar-line i').forEach(bar => { bar.style.width = '0'; bar.removeAttribute('title'); });
    document.querySelectorAll('.graph-bar-line span').forEach(label => { label.textContent = '—'; });
    $('graph-status').textContent = status;
  }

  function fillMetrics(base, cool) {
    const distDelta  = cool.distance_m - base.distance_m;
    const distPct    = base.distance_m ? 100*(cool.distance_m/base.distance_m-1) : 0;
    const timeDelta  = cool.walk_time_min - base.walk_time_min;
    const shadeDelta = (cool.shaded_share - base.shaded_share) * 100;
    const heatCut    = base.heat_exposure
      ? Math.max(0, 100*(1 - cool.heat_exposure/base.heat_exposure)) : 0;

    $('m-dist-base').textContent  = fmtM(base.distance_m);
    $('m-dist-cool').textContent  = fmtM(cool.distance_m);
    $('m-dist-delta').textContent = `${distDelta>=0?'+':''}${Math.round(distDelta)} m (${fmtPct(distPct)})`;
    $('m-dist-delta').className   = deltaClass(distDelta);

    $('m-time-base').textContent  = fmtMin(base.walk_time_min);
    $('m-time-cool').textContent  = fmtMin(cool.walk_time_min);
    $('m-time-delta').textContent = `${timeDelta>=0?'+':''}${timeDelta.toFixed(1)} min`;
    $('m-time-delta').className   = deltaClass(timeDelta);

    $('m-shade-base').textContent  = `${Math.round(base.shaded_share*100)}%`;
    $('m-shade-cool').textContent  = `${Math.round(cool.shaded_share*100)}%`;
    $('m-shade-delta').textContent = `${shadeDelta>=0?'+':''}${shadeDelta.toFixed(0)}pp`;
    $('m-shade-delta').className   = shadeDelta >= 0 ? 'metric-delta positive' : 'metric-delta';

    $('m-heat-base').textContent  = Math.round(base.heat_exposure);
    $('m-heat-cool').textContent  = Math.round(cool.heat_exposure);
    $('m-heat-delta').textContent = `${heatCut.toFixed(0)}% less heat`;
    $('m-heat-delta').className   = 'metric-delta positive';

    const chip = $('budget-chip');
    chip.textContent = heatCut > 0 ? `${heatCut.toFixed(0)}% less heat` : 'Same route';
    chip.className   = heatCut > 5 ? 'chip good' : 'chip';

    renderComparisonGraph(base, cool,
      heatCut > 2 ? `${heatCut.toFixed(0)}% less estimated heat on CoolRoute` : 'Both options have similar estimated heat');

    return heatCut;
  }

  function endpointsMatch(route, start, end, toleranceM = 180) {
    const c = route?.coordinates;
    if (!Array.isArray(c) || c.length < 2) return false;
    const meters = (a, b) => {
      const rad = Math.PI / 180, dy = (a[0] - b.lat) * rad;
      const dx = (a[1] - b.lon) * rad * Math.cos(b.lat * rad);
      return Math.hypot(dx, dy) * 6371000;
    };
    return (meters(c[0], start) <= toleranceM && meters(c[c.length - 1], end) <= toleranceM) ||
           (meters(c[0], end) <= toleranceM && meters(c[c.length - 1], start) <= toleranceM);
  }

  /* ═══════════════════════════════════════════════════════════════════
     PLAN ROUTE — works WITH or WITHOUT street data loaded
  ═══════════════════════════════════════════════════════════════════ */
  async function planRoute() {
    if (!S.origin || !S.destination) {
      $('warnings').replaceChildren();
      addWarn('Please set both a start and destination by clicking on the map.', 'error');
      return;
    }
    const routeOrigin = { lat: S.origin.lat, lon: S.origin.lon };
    const routeDestination = { lat: S.destination.lat, lon: S.destination.lon };
    const routePreferences = { hour: +$('inp-hour').value, heat_budget_pct: +$('inp-budget').value,
      step_free: $('chk-stepfree').checked, shade_available: $('chk-shade').checked };
    const closedEdgeIds = [...S.closedEdges];
    const routeHistoryContext = {
      origin: routeOrigin, destination: routeDestination,
      origin_label: $('origin-input').value || 'Start',
      destination_label: $('dest-input').value || 'Destination',
      city: $('inp-city').value || '', preferences: routePreferences,
    };

    $('warnings').replaceChildren();
    clearRoutes();
    clearComparisonGraph('Finding routes and shade data…');
    $('btn-plan').disabled = true;
    $('btn-plan').innerHTML = 'Finding your route… <span>⏳</span>';

    // Always get a complete point-to-point walking route first. The local
    // shade graph covers only a small viewport and must never clip the route.
    setStatus('Finding complete walking route…', 'loading');
    try {
      const route = await apiFetch('api/v1/real/directions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin: routeOrigin, destination: routeDestination }),
      });
      const drawRoute = () => {
        clearRoutes();
        S.routeLayers.push(L.polyline(route.coordinates, {
          color: '#09211d', weight: 12, opacity: .92, lineCap: 'round', lineJoin: 'round',
        }).addTo(map));
        S.routeLayers.push(L.polyline(route.coordinates, {
          color: '#ff9a5c', weight: 7, opacity: 1, lineCap: 'round', lineJoin: 'round',
        }).addTo(map));
        const bounds = L.latLngBounds([[routeOrigin.lat, routeOrigin.lon], [routeDestination.lat, routeDestination.lon], ...route.coordinates]);
        map.fitBounds(bounds, { padding: [54, 54], maxZoom: 17 });
      };
      drawRoute();
      const distance = route.distance_m, minutes = route.duration_s / 60;
      $('m-dist-base').textContent = fmtM(distance);
      $('m-dist-cool').textContent = '—';
      $('m-dist-delta').textContent = 'Walking route';
      $('m-dist-delta').className = 'metric-delta';
      $('m-time-base').textContent = fmtMin(minutes);
      $('m-time-cool').textContent = '—';
      $('m-time-delta').textContent = 'Estimated walking time';
      $('m-time-delta').className = 'metric-delta';
      $('m-shade-base').textContent = '?';
      $('m-shade-cool').textContent = '—';
      $('m-shade-delta').textContent = 'Shade comparison unavailable';
      $('m-heat-base').textContent = '—';
      $('m-heat-cool').textContent = '—';
      $('m-heat-delta').textContent = 'Shade data needed';
      $('cool-route-note').textContent = 'Waiting for shade data covering both points.';
      renderBaselineGraph(distance, minutes, 'Street route ready · shade comparison loading');
      $('budget-chip').textContent = 'Shortest route';
      $('budget-chip').className = 'chip';
      $('verdict').textContent = `Complete walking route: ${fmtM(distance)} · about ${fmtMin(minutes)}.`;
      $('verdict').classList.add('has-result');
      $('data-note').textContent = `${route.source} · Compare full street routes on the map.`;
      setStatus(`Route ready · ${route.router}`, 'ready');

      const historyRouteKey = window.crypto?.randomUUID?.() || `walk-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
      await saveRouteHistory(historyRouteKey, {
        distance_m: distance, walk_time_min: minutes, shaded_share: null, heat_exposure: null,
      }, null, routeHistoryContext);

      // Shade comparison loads an area around both chosen points, rather than
      // incorrectly routing only inside the current map viewport.
      const pad = 0.003;
      const routeBbox = [
        Math.max(-84.9, Math.min(routeOrigin.lat, routeDestination.lat) - pad),
        Math.max(-179.9, Math.min(routeOrigin.lon, routeDestination.lon) - pad),
        Math.min(84.9, Math.max(routeOrigin.lat, routeDestination.lat) + pad),
        Math.min(179.9, Math.max(routeOrigin.lon, routeDestination.lon) + pad),
      ];
      if (routeBbox[2] - routeBbox[0] <= 0.045 && routeBbox[3] - routeBbox[1] <= 0.045) {
        $('cool-route-note').textContent = 'Comparing mapped shade and walking routes…';
        void (async () => { try {
            const comparison = await apiFetch('api/v1/real/route', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ origin: routeOrigin, destination: routeDestination, bbox: routeBbox,
                hour: routePreferences.hour, heat_budget_pct: routePreferences.heat_budget_pct,
                step_free: routePreferences.step_free, shade_available: routePreferences.shade_available,
                closed_edge_ids: closedEdgeIds }),
            });
            const { baseline, coolroute } = comparison;
            const metricKeys = ['distance_m', 'walk_time_min', 'shaded_share', 'heat_exposure'];
            if (!baseline || !coolroute || metricKeys.some(key =>
              typeof baseline[key] !== 'number' || !Number.isFinite(baseline[key]) ||
              typeof coolroute[key] !== 'number' || !Number.isFinite(coolroute[key]))) {
              throw new Error('The shade service returned incomplete route data.');
            }
            const completeGeometry = endpointsMatch(baseline, routeOrigin, routeDestination) && endpointsMatch(coolroute, routeOrigin, routeDestination);
            // The local shade graph snaps pins to nearby street junctions. Its
            // metrics remain useful even when that snap differs from the full
            // directions route, so never leave the CoolRoute table blank.
            const heatCut = fillMetrics(baseline, coolroute);
            await saveRouteHistory(historyRouteKey, baseline, coolroute, routeHistoryContext);
            if (completeGeometry) {
              clearRoutes();
              S.routeLayers.push(L.polyline(baseline.coordinates, { color: '#ff9a5c', weight: 9, opacity: .62 }).addTo(map));
              S.routeLayers.push(L.polyline(coolroute.coordinates, { color: '#3ed9b6', weight: 6, opacity: .98, lineCap: 'round', lineJoin: 'round' }).addTo(map));
              map.fitBounds(L.latLngBounds([...baseline.coordinates, ...coolroute.coordinates,
                [routeOrigin.lat, routeOrigin.lon], [routeDestination.lat, routeDestination.lon]]), { padding: [54, 54], maxZoom: 17 });
              $('verdict').textContent = heatCut > 2
                ? `Cooler full route: ${fmtM(coolroute.distance_m)} · ~${heatCut.toFixed(0)}% less heat.`
                : 'The shortest route already fits your heat budget.';
              $('cool-route-note').textContent = heatCut > 2
                ? `${heatCut.toFixed(0)}% lower heat · teal line on map`
                : 'Similar heat exposure · teal line on map';
              $('data-note').textContent = `${comparison.shade_method} · Shade is estimated from mapped features.`;
            } else {
              $('cool-route-note').textContent = heatCut > 2
                ? `${heatCut.toFixed(0)}% lower estimated heat · map keeps the complete walking route`
                : 'Similar heat estimate · map keeps the complete walking route';
              $('verdict').textContent = `Comparison ready: CoolRoute is ${fmtM(coolroute.distance_m)} with ${heatCut.toFixed(0)}% lower estimated heat.`;
              $('data-note').textContent = 'Comparison metrics use the nearest mapped street junctions; the map keeps the complete directions route. ' + (comparison.shade_method || 'Shade is estimated from mapped features.');
            }
          } catch (error) {
            const reason = error?.message || 'The shade comparison service could not return a route.';
            $('cool-route-note').textContent = `CoolRoute comparison unavailable: ${reason}`;
            $('graph-status').textContent = `Comparison unavailable: ${reason}`;
          } })();
      } else {
        const reason = 'This route spans a larger area than the shade-data service supports (about 4 km across).';
        $('cool-route-note').textContent = `CoolRoute comparison unavailable: ${reason}`;
        $('graph-status').textContent = reason;
      }
    } catch (e) {
      addWarn(e.message, 'error');
      setStatus('Route unavailable', 'error');
    }
    $('btn-plan').disabled = false;
    $('btn-plan').innerHTML = 'Find my cooler route <span aria-hidden="true">→</span>';
    return;
  }

  /* ═══════════════════════════════════════════════════════════════════
     RESET
  ═══════════════════════════════════════════════════════════════════ */
  function resetAll() {
    S.origin = S.destination = null;
    $('origin-input').value = '';
    $('dest-input').value = '';
    $('origin-suggestions').hidden = $('dest-suggestions').hidden = true;
    Object.values(S.markers).forEach(m => map.removeLayer(m));
    S.markers = {};
    S.closedEdges.clear();
    clearRoutes();

    if (S.area) {
      S.area.graph.edges.forEach((edge, id) => {
        const line = S.streetLines[id];
        if (line) line.setStyle({
          color: edge.shade>=0.30 ? '#3ed9b6' : '#6b8f89', dashArray: null,
          weight: edge.shade>=0.30 ? 4 : 2.5,
        });
      });
    }

    $('warnings').replaceChildren();
    $('cool-route-note').textContent = 'Shade-aware option appears when shade data is ready.';
    clearComparisonGraph('Plan a route to compare');
    $('verdict').textContent = 'Choose a start and destination on the map, then plan your walk.';
    $('verdict').classList.remove('has-result');
    $('budget-chip').textContent = 'Ready';
    $('budget-chip').className   = 'chip';
    setStatus('Map ready — choose a start point', 'ready');
    setHint('Click anywhere on the map to set your start point');

    ['m-dist-base','m-dist-cool','m-dist-delta',
     'm-time-base','m-time-cool','m-time-delta',
     'm-shade-base','m-shade-cool','m-shade-delta',
     'm-heat-base','m-heat-cool','m-heat-delta'].forEach(id => {
      const el = $(id);
      if (el) el.textContent = el.tagName === 'SPAN' ? '' : '--';
    });
    setMode('origin');
  }

  /* ═══════════════════════════════════════════════════════════════════
     MAP EVENTS — always fire, regardless of street load state
  ═══════════════════════════════════════════════════════════════════ */
  map.on('click', e => {
    if (S.mode === 'close') return;
    placePin(S.mode, { lat: e.latlng.lat, lon: e.latlng.lng });
    if (S.mode === 'origin') setMode('destination');
  });

  map.on('moveend', () => loadStreets(false));

  /* ═══════════════════════════════════════════════════════════════════
     CONTROLS
  ═══════════════════════════════════════════════════════════════════ */
  document.querySelectorAll('[data-mode]').forEach(b =>
    b.addEventListener('click', () => setMode(b.dataset.mode))
  );

  L.DomEvent.disableClickPropagation($('.map-type-control'));
  $('btn-map-street').addEventListener('click', () => useTileSource(0));
  $('btn-map-satellite').addEventListener('click', () => useTileSource(satelliteTileIndex));

  $('btn-plan').addEventListener('click', planRoute);
  $('btn-reset').addEventListener('click', resetAll);
  $('btn-history-refresh').addEventListener('click', () => loadRouteHistory(false));
  $('btn-history-more').addEventListener('click', () => {
    if (historyHasMore) loadRouteHistory(true);
  });

  $('btn-swap').addEventListener('click', () => {
    const tmp = S.origin; S.origin = S.destination; S.destination = tmp;
    if (S.origin)      placePin('origin',      S.origin);
    else $('origin-input').value = '';
    if (S.destination) placePin('destination', S.destination);
    else $('dest-input').value = '';
    clearRoutes();
  });

  $('inp-hour').addEventListener('input', () => {
    $('hour-display').textContent = fmtH(+$('inp-hour').value);
    updateWeather(map.getCenter());
  });

  $('inp-budget').addEventListener('input', () => {
    $('budget-display').textContent = $('inp-budget').value;
  });


  function bindPlaceAutocomplete(which) {
    const input = $(which === 'origin' ? 'origin-input' : 'dest-input');
    const list = $(which === 'origin' ? 'origin-suggestions' : 'dest-suggestions');
    let timer = 0, sequence = 0;
    const hide = () => { list.hidden = true; list.replaceChildren(); };
    const choose = place => {
      hide();
      placePin(which, { lat: place.lat, lon: place.lon, label: place.name });
      map.setView([place.lat, place.lon], Math.max(map.getZoom(), 16));
      updateWeather(map.getCenter());
      if (S.origin && S.destination) {
        map.fitBounds(L.latLngBounds([[S.origin.lat, S.origin.lon], [S.destination.lat, S.destination.lon]]),
          { padding: [60, 60], maxZoom: 16 });
      } else if (which === 'origin') {
        $('dest-input').focus();
      }
    };
    const search = async (selectFirst = false) => {
      const query = input.value.trim();
      const current = ++sequence;
      if (query.length < 2) { hide(); return; }
      list.replaceChildren();
      const loading = document.createElement('div'); loading.className = 'place-suggestion-note'; loading.textContent = 'Searching places…';
      list.append(loading); list.hidden = false;
      try {
        const response = await apiFetch(`api/v1/real/search?q=${encodeURIComponent(query)}`);
        if (current !== sequence || query !== input.value.trim()) return;
        list.replaceChildren();
        if (!response.places?.length) {
          const empty = document.createElement('div'); empty.className = 'place-suggestion-note'; empty.textContent = 'No matching places found.';
          list.append(empty); list.hidden = false; return;
        }
        if (selectFirst) { choose(response.places[0]); return; }
        response.places.forEach(place => {
          const option = document.createElement('button');
          option.type = 'button'; option.className = 'place-suggestion'; option.setAttribute('role', 'option');
          option.textContent = place.name;
          option.addEventListener('click', () => choose(place));
          list.append(option);
        });
        list.hidden = false;
      } catch (error) {
        if (current !== sequence) return;
        list.replaceChildren();
        const failed = document.createElement('div'); failed.className = 'place-suggestion-note'; failed.textContent = error.message;
        list.append(failed); list.hidden = false;
      }
    };
    input.addEventListener('input', () => {
      clearTimeout(timer);
      if (S[which]) {
        S[which] = null;
        if (S.markers[which]) map.removeLayer(S.markers[which]);
        delete S.markers[which]; clearRoutes();
      }
      timer = setTimeout(() => search(false), 300);
    });
    input.addEventListener('keydown', async event => {
      if (event.key === 'Escape') hide();
      if (event.key === 'Enter') {
        event.preventDefault(); clearTimeout(timer);
        if (!list.hidden) {
          const first = list.querySelector('.place-suggestion');
          if (first) { first.click(); return; }
        }
        await search(true);
      }
    });
    input.addEventListener('blur', () => setTimeout(hide, 160));
  }
  bindPlaceAutocomplete('origin');
  bindPlaceAutocomplete('destination');

  async function searchCity() {
    const input = $('inp-city');
    const query = input.value.trim();
    if (!query) { showOverlay('Enter a city or place name first.', 2500); input.focus(); return; }
    const button = $('btn-city-search');
    button.disabled = true;
    button.textContent = 'Searching…';
    try {
      const place = await apiFetch(`api/v1/real/geocode?q=${encodeURIComponent(query)}`);
      map.setView([place.lat, place.lon], 15);
      S.area = null;
      streetLayer.clearLayers(); treeLayer.clearLayers();
      resetAll();
      $('map-foot-hint').textContent = `Showing ${place.name.split(',').slice(0, 2).join(',')}. Type start and destination or click the map.`;
      showOverlay(`Map moved to ${place.name.split(',').slice(0, 2).join(',')}`, 2800);
      updateWeather(map.getCenter());
      loadStreets(true);
    } catch (e) {
      showOverlay(e.message, 4500);
    } finally {
      button.disabled = false;
      button.textContent = '⌕ Search';
    }
  }
  $('btn-city-search').addEventListener('click', searchCity);
  $('inp-city').addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); searchCity(); }
  });

  /* ═══════════════════════════════════════════════════════════════════
     INIT — map is ready immediately, streets load in background
  ═══════════════════════════════════════════════════════════════════ */
  $('hour-display').textContent   = fmtH(13);
  $('budget-display').textContent = '60';
  setMode('origin');
  setStatus('Map ready — click to place your start point', 'ready');
  setHint('Type a start and destination, or click the map to choose points');
  loadRouteHistory(false);

  // Load weather immediately (fast — doesn't depend on Overpass)
  updateWeather(map.getCenter());

  // Load streets in background (slow — Overpass)
  loadStreets(false);

})();


