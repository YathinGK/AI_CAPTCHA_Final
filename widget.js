/**
 * VideoCap Widget  v4.0
 * Exact visual match to the original VideoCaptcha.js React component.
 *
 * Flow:
 *   Phase 1 – reCAPTCHA-style box  (idle → loading spinner → triangle puzzle)
 *   Phase 2 – Full VideoCap card    (header + step pills + hero + video + text-input + footer)
 *
 * Usage:
 *   <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Roboto:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap">
 *   <script src="https://your-server.com/widget.js"></script>
 *   <div id="vc"></div>
 *   <script>
 *     VideoCap.render({
 *       container: '#vc',
 *       apiKey:    'vc_YOUR_KEY',
 *       apiUrl:    'https://your-server.com',
 *       onSuccess: function(token) { ... },
 *       onError:   function(err)   { ... },
 *     });
 *   </script>
 */
(function (W) {
  'use strict';

  /* ─── defaults ──────────────────────────────────────────── */
  var DEFAULTS = {
    container: '#vc',
    apiKey:    'vc_gUQY-SBk52arKM1ZazcnVg93mZ8rDdSXlKmwe3iwW1plnmzxT-yCOQ',
    apiUrl:    'http://localhost:5000',
    onSuccess: function (t) { console.log('[VideoCap] ok', t); },
    onError:   function (e) { console.warn('[VideoCap] err', e); },
  };

  /* ─── triangle data ─────────────────────────────────────── */
  var TDOTS  = [{x:110,y:22},{x:28,y:152},{x:192,y:152}];
  var TEDGES = [[0,1],[1,2],[0,2]];

  /* ═══════════════════════════════════════════════════════════
     CSS – injected once, prefixed with _vc_ to avoid clashes
  ═══════════════════════════════════════════════════════════ */
  function injectCSS() {
    if (document.getElementById('_vcap_css')) return;
    var s = document.createElement('style');
    s.id  = '_vcap_css';
    s.textContent = [

      /* ── Phase-1 landing widget ── */
      '._vcap-lp-widget{width:300px;background:#f9f9f9;border:1px solid #d3d3d3;',
        'border-radius:3px;box-shadow:0 1px 3px rgba(0,0,0,.10);overflow:hidden;}',

      '._vcap-row{display:flex;align-items:center;padding:0 12px;height:74px;',
        'background:#f9f9f9;cursor:pointer;user-select:none;}',
      '._vcap-row-nc{cursor:default;}',

      '._vcap-cba{width:44px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}',
      '._vcap-cb{width:28px;height:28px;border:2px solid #c1c1c1;border-radius:3px;',
        'background:#fff;display:flex;align-items:center;justify-content:center;',
        'position:relative;transition:border-color .2s;flex-shrink:0;}',
      '._vcap-row:hover ._vcap-cb{border-color:#b0b0b0;}',
      '._vcap-cb-loading{border-color:transparent!important;background:transparent!important;}',
      '._vcap-cb-checked{border-color:transparent!important;background:#4a90d9!important;}',

      '._vcap-spin{position:absolute;inset:-2px;width:calc(100% + 4px);height:calc(100% + 4px);',
        'animation:_vcapRot .9s linear infinite;}',
      '@keyframes _vcapRot{to{transform:rotate(360deg)}}',

      '._vcap-robot-lbl{flex:1;font-family:Roboto,sans-serif;font-size:14px;font-weight:400;',
        'color:#000;letter-spacing:.01em;padding-left:10px;}',

      '._vcap-logo-blk{display:flex;flex-direction:column;align-items:center;justify-content:center;',
        'gap:1px;flex-shrink:0;width:72px;padding-right:2px;}',
      '._vcap-logo-name{font-family:Roboto,sans-serif;font-size:10px;font-weight:500;',
        'color:#9aa0a6;letter-spacing:.05em;text-transform:uppercase;line-height:1;}',
      '._vcap-logo-sub{font-family:Roboto,sans-serif;font-size:8px;color:#9aa0a6;',
        'line-height:1.3;white-space:nowrap;}',

      /* puzzle section */
      '._vcap-puzzle{display:flex;flex-direction:column;animation:_vcapFd .3s ease;}',
      '@keyframes _vcapFd{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}',
      '._vcap-div{height:1px;background:#e0e0e0;margin:0 12px;}',
      '._vcap-pi{padding:14px 16px 10px;background:#fff;}',

      '._vcap-tw{display:flex;flex-direction:column;align-items:center;gap:.55rem;}',
      '._vcap-tlbl{font-size:.7rem;font-weight:600;color:#64748b;text-align:center;',
        'min-height:1.1em;font-family:Sora,sans-serif;}',
      '._vcap-tsvg{width:100%;max-width:210px;height:auto;display:block;touch-action:none;user-select:none;}',

      '._vcap-prog{display:flex;gap:.4rem;align-items:center;}',
      '._vcap-pip{width:22px;height:3px;border-radius:2px;background:#e2e8f0;',
        'transition:background .3s ease,transform .2s ease;}',
      '._vcap-pip.drawn{background:linear-gradient(90deg,#FF6B35,#FFB347);}',
      '._vcap-pip.done{background:linear-gradient(90deg,#22c55e,#16a34a);transform:scaleY(1.5);}',
      '._vcap-tri-rst{background:none;border:1px solid #e2e8f0;color:#94a3b8;',
        'padding:.25rem .65rem;border-radius:5px;font-size:.65rem;font-weight:600;',
        'font-family:Sora,sans-serif;cursor:pointer;transition:border-color .2s,color .2s;}',
      '._vcap-tri-rst:hover{border-color:#FF6B35;color:#FF6B35;}',

      /* ── Phase-2 full card ── */
      '._vcap-card-wrap{max-width:520px;margin:0 auto;font-family:Sora,sans-serif;}',
      '._vcap-card{background:#fff;border-radius:20px;',
        'box-shadow:0 2px 8px rgba(0,0,0,.06),0 16px 48px rgba(0,0,0,.10);',
        'overflow:hidden;animation:_vcapUp .4s ease;}',
      '@keyframes _vcapUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}',

      /* header */
      '._vcap-hdr{display:flex;align-items:center;justify-content:space-between;',
        'padding:1.1rem 1.5rem;border-bottom:1px solid #f3ede6;}',
      '._vcap-logo-grp{display:flex;align-items:center;gap:.55rem;}',
      '._vcap-hdr-icon{width:36px;height:36px;',
        'background:linear-gradient(135deg,#FF6B35 0%,#FF9A5C 100%);border-radius:9px;',
        'display:flex;align-items:center;justify-content:center;flex-shrink:0;',
        'box-shadow:0 3px 10px rgba(255,107,53,.35);}',
      '._vcap-title{font-size:1.05rem;font-weight:700;color:#1a1a1a;margin:0;letter-spacing:-.02em;}',
      '._vcap-title span{color:#FF6B35;}',

      /* step pills */
      '._vcap-pills{display:flex;align-items:center;gap:.4rem;}',
      '._vcap-pill{display:flex;align-items:center;gap:.3rem;padding:.28rem .65rem;',
        'border-radius:20px;font-size:.72rem;font-weight:600;letter-spacing:.01em;',
        'transition:all .2s ease;}',
      '._vcap-pill-i{background:#f0ece8;color:#a89b8e;border:1.5px solid #e8e0d8;}',
      '._vcap-pill-a{background:#1a1a1a;color:#fff;border:1.5px solid #1a1a1a;}',
      '._vcap-pill-c{background:#FF6B35;color:#fff;border:1.5px solid #FF6B35;}',
      '._vcap-pill-num{width:16px;height:16px;border-radius:50%;',
        'display:flex;align-items:center;justify-content:center;font-size:.62rem;font-weight:700;}',
      '._vcap-pill-i ._vcap-pill-num{background:#e0d8d0;color:#a89b8e;}',
      '._vcap-pill-a ._vcap-pill-num{background:rgba(255,255,255,.2);}',
      '._vcap-pill-c ._vcap-pill-num{background:rgba(255,255,255,.25);}',

      /* hero */
      '._vcap-hero{padding:1.4rem 1.5rem .6rem;}',
      '._vcap-hero-title{font-size:1.55rem;font-weight:800;color:#1a1a1a;margin:0 0 .3rem;',
        'letter-spacing:-.03em;line-height:1.2;}',
      '._vcap-hero-sub{font-size:.83rem;color:#8a7d74;margin:0;font-weight:400;line-height:1.45;}',

      /* generate button */
      '._vcap-gen-btn{display:block;width:calc(100% - 3rem);margin:0 1.5rem 1rem;',
        'background:linear-gradient(90deg,#FF6B35 0%,#FF9A5C 100%);color:#fff;border:none;',
        'padding:.78rem;border-radius:12px;font-size:.9rem;font-weight:700;',
        'font-family:Sora,sans-serif;cursor:pointer;',
        'transition:opacity .2s,box-shadow .2s;box-shadow:0 4px 16px rgba(255,107,53,.35);}',
      '._vcap-gen-btn:hover:not(:disabled){opacity:.9;box-shadow:0 6px 22px rgba(255,107,53,.45);}',
      '._vcap-gen-btn:disabled{opacity:.55;cursor:not-allowed;}',

      /* generate prompt placeholder */
      '._vcap-prompt{display:flex;flex-direction:column;align-items:center;justify-content:center;',
        'height:200px;gap:.75rem;background:#faf7f4;border-radius:12px;',
        'border:2px dashed #e8ddd4;margin-bottom:1rem;}',
      '._vcap-prompt-icon{font-size:2.5rem;opacity:.45;}',
      '._vcap-prompt-txt{font-size:.83rem;color:#b0a398;font-weight:500;}',

      /* body */
      '._vcap-body{padding:.85rem 1.5rem 1.25rem;animation:_vcapUp .35s ease;}',

      /* video */
      '._vcap-vsec{margin-bottom:1rem;border-radius:12px;overflow:hidden;',
        'background:#111;position:relative;}',
      '._vcap-live-badge{position:absolute;top:10px;left:10px;',
        'background:rgba(20,10,5,.72);border-radius:20px;padding:.22rem .6rem;',
        'display:flex;align-items:center;gap:.3rem;z-index:2;}',
      '._vcap-live-dot{width:7px;height:7px;border-radius:50%;background:#ef4444;',
        'animation:_vcapDot 1.5s ease-in-out infinite;}',
      '@keyframes _vcapDot{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.8)}}',
      '._vcap-live-txt{font-size:.63rem;font-weight:700;color:#fff;letter-spacing:.1em;}',
      '._vcap-video{width:100%;display:block;max-height:260px;object-fit:contain;}',

      /* question */
      '._vcap-qsec{margin-bottom:.85rem;}',
      '._vcap-qbox{display:flex;align-items:flex-start;gap:.75rem;',
        'background:#faf7f4;border:1px solid #f0e8e0;border-radius:12px;padding:.85rem 1rem;}',
      '._vcap-qicon{width:34px;height:34px;',
        'background:linear-gradient(135deg,#FF6B35 0%,#FF9A5C 100%);border-radius:8px;',
        'display:flex;align-items:center;justify-content:center;flex-shrink:0;',
        'box-shadow:0 3px 10px rgba(255,107,53,.28);}',
      '._vcap-qicon svg{width:16px;height:16px;}',
      '._vcap-qlbl{font-size:.63rem;font-weight:700;color:#FF6B35;letter-spacing:.1em;',
        'text-transform:uppercase;margin:0 0 .2rem;display:block;}',
      '._vcap-qtxt{font-size:.9rem;font-weight:600;color:#1a1a1a;line-height:1.45;margin:0;}',

      /* answer input */
      '._vcap-ans-wrap{position:relative;margin-bottom:.25rem;}',
      '._vcap-ans-inp{width:100%;padding:.9rem 1rem;font-size:.88rem;font-family:Sora,sans-serif;',
        'color:#1a1a1a;border:1.5px solid #e8ddd4;border-radius:12px;background:#faf7f4;',
        'transition:border-color .2s,box-shadow .2s,background .2s;outline:none;}',
      '._vcap-ans-inp::placeholder{color:#c0b4a8;}',
      '._vcap-ans-inp:focus{border-color:#FF6B35;background:#fff;',
        'box-shadow:0 0 0 3px rgba(255,107,53,.12);}',
      '._vcap-ans-inp:disabled{background:#f5f0eb;cursor:not-allowed;color:#b0a398;}',
      '._vcap-char{font-size:.7rem;color:#c0b4a8;text-align:right;margin-top:3px;}',

      /* verify button */
      '._vcap-verify{width:100%;background:linear-gradient(90deg,#FF6B35 0%,#FF9A5C 100%);',
        'color:#fff;border:none;padding:.9rem 1.5rem;border-radius:12px;',
        'font-size:.95rem;font-weight:700;font-family:Sora,sans-serif;cursor:pointer;',
        'transition:opacity .2s,transform .15s,box-shadow .2s;',
        'display:flex;align-items:center;justify-content:center;gap:.5rem;',
        'margin-top:.85rem;box-shadow:0 6px 20px rgba(255,107,53,.38);}',
      '._vcap-verify:hover:not(:disabled){opacity:.92;transform:translateY(-1px);',
        'box-shadow:0 8px 28px rgba(255,107,53,.45);}',
      '._vcap-verify:active:not(:disabled){transform:translateY(0);}',
      '._vcap-verify:disabled{opacity:.5;cursor:not-allowed;transform:none;',
        'box-shadow:0 3px 10px rgba(255,107,53,.2);}',

      /* messages */
      '._vcap-msgsec{padding:0 1.5rem;}',
      '._vcap-errmsg{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;',
        'padding:.65rem .9rem;border-radius:10px;font-size:.8rem;font-weight:500;',
        'margin-bottom:.6rem;animation:_vcapUp .3s ease;}',
      '._vcap-msg{padding:.65rem .9rem;border-radius:10px;font-size:.8rem;font-weight:500;',
        'line-height:1.45;animation:_vcapUp .3s ease;margin-bottom:.6rem;}',
      '._vcap-msg.instruction{background:#fff8f4;color:#c04a1a;border:1px solid #fdd5be;}',
      '._vcap-msg.success-message{background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;}',
      '._vcap-msg.retry-message,._vcap-msg.error{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;}',
      '._vcap-msg.countdown{background:#fff8f4;color:#c04a1a;border:1px solid #fdd5be;}',
      '._vcap-msg.timeout{background:#fef2f2;color:#991b1b;border:1px solid #fecaca;}',
      '._vcap-msg.selected{background:#fff8f4;color:#c04a1a;border:1px solid #fdd5be;}',
      '._vcap-msg.loading{background:#faf7f4;color:#a05a3a;border:1px solid #e8ddd4;}',
      '._vcap-cdown{font-family:"JetBrains Mono",monospace;font-weight:600;color:#ef4444;}',

      /* retry row */
      '._vcap-retry-row{padding:0 1.5rem .5rem;display:flex;justify-content:flex-end;}',
      '._vcap-retry-btn{background:none;border:1.5px solid #e8ddd4;color:#6b5c50;',
        'padding:.5rem 1.1rem;border-radius:8px;font-size:.8rem;font-weight:600;',
        'font-family:Sora,sans-serif;cursor:pointer;',
        'transition:border-color .2s,background .2s,color .2s;}',
      '._vcap-retry-btn:hover:not(:disabled){border-color:#FF6B35;color:#FF6B35;background:#fff8f4;}',

      /* footer */
      '._vcap-footer{display:flex;align-items:center;justify-content:space-between;',
        'padding:.85rem 1.5rem;border-top:1px solid #f3ede6;}',
      '._vcap-fbadges{display:flex;align-items:center;gap:.9rem;}',
      '._vcap-fbadge{display:flex;align-items:center;gap:.28rem;}',
      '._vcap-fbadge svg{width:12px;height:12px;flex-shrink:0;color:#b0a398;}',
      '._vcap-fbadge span{font-size:.7rem;color:#a89b8e;font-weight:500;}',
      '._vcap-fright{font-size:.7rem;color:#b0a398;font-weight:500;}',
      '._vcap-fright strong{color:#FF6B35;font-weight:700;}',

      /* loading overlay */
      '._vcap-overlay{position:fixed;inset:0;background:rgba(245,239,232,.6);',
        'display:flex;align-items:center;justify-content:center;z-index:9999;}',
      '._vcap-spinner{width:36px;height:36px;border:3px solid #f0e8e0;',
        'border-top-color:#FF6B35;border-radius:50%;animation:_vcapRot .8s linear infinite;}',

    ].join('');
    document.head.appendChild(s);
  }

  /* ─── tiny helpers ──────────────────────────────────────── */
  function el(tag, cls) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    return e;
  }
  function assign(t) {
    for (var i = 1; i < arguments.length; i++) {
      var s = arguments[i];
      for (var k in s) if (Object.prototype.hasOwnProperty.call(s, k)) t[k] = s[k];
    }
    return t;
  }

  /* ─── shield logo SVG ───────────────────────────────────── */
  function shieldSVG(w, h) {
    return '<svg width="'+w+'" height="'+h+'" viewBox="0 0 56 64" fill="none">' +
      '<defs><linearGradient id="_vcSG2" x1="0%" y1="0%" x2="100%" y2="100%">' +
      '<stop offset="0%" stop-color="#4f97f5"/><stop offset="100%" stop-color="#1a6fd4"/>' +
      '</linearGradient></defs>' +
      '<path d="M28 2L4 13v17c0 14.5 10.2 28.1 24 31.2C41.8 58.1 52 44.5 52 30V13L28 2z" fill="url(#_vcSG2)"/>' +
      '<path d="M28 2L4 13v4l24-11 24 11v-4L28 2z" fill="rgba(255,255,255,.2)"/>' +
      '<polygon points="21,20 39,30 21,40" fill="white"/>' +
      '</svg>';
  }

  /* ─── orange shield logo (for card header) ──────────────── */
  function orangeShieldSVG() {
    return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none">' +
      '<path d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6L12 2z"' +
      ' fill="rgba(255,255,255,0.25)" stroke="white" stroke-width="2" stroke-linejoin="round"/>' +
      '<polygon points="10,8 16,12 10,16" fill="white"/>' +
      '</svg>';
  }

  /* ═══════════════════════════════════════════════════════════
     Phase-1 row builder
  ═══════════════════════════════════════════════════════════ */
  function buildRow(state) {
    var row = el('div', '_vcap-row' + (state !== 'idle' ? ' _vcap-row-nc' : ''));

    /* checkbox */
    var cba = el('div', '_vcap-cba');
    var cb  = el('div', '_vcap-cb' +
      (state === 'loading' ? ' _vcap-cb-loading' :
       state === 'checked' ? ' _vcap-cb-checked' : ''));

    if (state === 'loading') {
      cb.innerHTML =
        '<svg class="_vcap-spin" viewBox="0 0 24 24" fill="none">' +
        '<circle cx="12" cy="12" r="9" stroke="#e2e8f0" stroke-width="2.5"/>' +
        '<path d="M12 3a9 9 0 0 1 9 9" stroke="url(#_vcCG3)" stroke-width="2.5" stroke-linecap="round"/>' +
        '<defs><linearGradient id="_vcCG3" x1="0%" y1="0%" x2="100%" y2="0%">' +
        '<stop offset="0%" stop-color="#FF6B35"/>' +
        '<stop offset="100%" stop-color="#FFB347"/>' +
        '</linearGradient></defs></svg>';
    } else if (state === 'checked') {
      cb.innerHTML =
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none">' +
        '<polyline points="20 6 9 17 4 12" stroke="white" stroke-width="3"' +
        ' stroke-linecap="round" stroke-linejoin="round"/></svg>';
    }
    cba.appendChild(cb);
    row.appendChild(cba);

    var lbl = el('span', '_vcap-robot-lbl');
    lbl.textContent = state === 'checked' ? 'Connect the dots to verify' : "I'm not a robot";
    row.appendChild(lbl);

    var logo = el('div', '_vcap-logo-blk');
    logo.innerHTML = shieldSVG(32, 36) +
      '<span class="_vcap-logo-name">VideoCap</span>' +
      '<span class="_vcap-logo-sub">Privacy · Terms</span>';
    row.appendChild(logo);

    return row;
  }

  /* ═══════════════════════════════════════════════════════════
     Triangle puzzle (vanilla JS port of React component)
  ═══════════════════════════════════════════════════════════ */
  function buildTriangle(onDone) {
    var NS = 'http://www.w3.org/2000/svg';
    var drawn = [], dragging = false, dragFrom = null;
    var dragPos = {x:0,y:0}, hoverDot = null, done = false;

    var wrap = el('div', '_vcap-tw');
    var lbl  = el('p',   '_vcap-tlbl');
    lbl.textContent = 'Drag between the dots';

    /* SVG */
    var svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 220 170');
    svg.setAttribute('class',   '_vcap-tsvg');

    /* defs */
    var defs = document.createElementNS(NS, 'defs');
    defs.innerHTML =
      '<linearGradient id="_vcEG3" x1="0%" y1="0%" x2="100%" y2="0%">' +
        '<stop offset="0%" stop-color="#FF6B35"/><stop offset="100%" stop-color="#FFB347"/>' +
      '</linearGradient>' +
      '<linearGradient id="_vcDG3" x1="0%" y1="0%" x2="100%" y2="100%">' +
        '<stop offset="0%" stop-color="#FF6B35"/><stop offset="100%" stop-color="#FF9A5C"/>' +
      '</linearGradient>' +
      '<linearGradient id="_vcOK3" x1="0%" y1="0%" x2="100%" y2="100%">' +
        '<stop offset="0%" stop-color="#22c55e"/><stop offset="100%" stop-color="#16a34a"/>' +
      '</linearGradient>' +
      '<filter id="_vcGl3">' +
        '<feGaussianBlur stdDeviation="2.5" result="b"/>' +
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>' +
      '</filter>';
    svg.appendChild(defs);

    /* ghost guide */
    var ghost = document.createElementNS(NS, 'polygon');
    ghost.setAttribute('points', TDOTS.map(function(d){return d.x+','+d.y;}).join(' '));
    ghost.setAttribute('fill', 'none');
    ghost.setAttribute('stroke', '#e2e8f0');
    ghost.setAttribute('stroke-width', '1.5');
    ghost.setAttribute('stroke-dasharray', '5 4');
    svg.appendChild(ghost);

    /* edge layer */
    var edgeLayer = document.createElementNS(NS, 'g');
    svg.appendChild(edgeLayer);

    /* live drag line */
    var dragLine = document.createElementNS(NS, 'line');
    dragLine.setAttribute('stroke', 'rgba(255,107,53,0.5)');
    dragLine.setAttribute('stroke-width', '2');
    dragLine.setAttribute('stroke-linecap', 'round');
    dragLine.setAttribute('stroke-dasharray', '5 4');
    dragLine.style.display = 'none';
    svg.appendChild(dragLine);

    /* dots */
    var dotEls = TDOTS.map(function(d, i) {
      var g = document.createElementNS(NS, 'g');
      g.style.cursor = 'grab';

      function mkC(r, fill, stroke, sw) {
        var c = document.createElementNS(NS, 'circle');
        c.setAttribute('cx', d.x); c.setAttribute('cy', d.y); c.setAttribute('r', r);
        c.setAttribute('fill', fill);
        if (stroke) { c.setAttribute('stroke', stroke); c.setAttribute('stroke-width', sw||'1'); }
        return c;
      }

      var pulse = mkC(18, 'rgba(255,107,53,0.06)');
      var ring  = mkC(0,  'none', 'rgba(255,107,53,0.4)', '1.5');
      var main  = mkC(12, '#fff', '#cbd5e1', '2');
      var inner = mkC(3,  '#94a3b8');
      g.appendChild(pulse); g.appendChild(ring); g.appendChild(main); g.appendChild(inner);

      g.addEventListener('mousedown', function(e){ e.preventDefault(); startDrag(e,i); });
      g.addEventListener('touchstart', function(e){ e.preventDefault(); startDrag(e,i); },{passive:false});
      svg.appendChild(g);
      return {pulse:pulse,ring:ring,main:main,inner:inner};
    });

    /* pips */
    var progRow = el('div', '_vcap-prog');
    var pips = TEDGES.map(function(){
      var p = el('div','_vcap-pip'); progRow.appendChild(p); return p;
    });

    /* reset button */
    var rst = el('button', '_vcap-tri-rst');
    rst.textContent = '↺ Reset';
    rst.style.display = 'none';
    rst.addEventListener('click', function(){ drawn=[]; redraw(); });

    /* helpers */
    function svgPt(e) {
      var r = svg.getBoundingClientRect();
      var cx = e.touches ? e.touches[0].clientX : e.clientX;
      var cy = e.touches ? e.touches[0].clientY : e.clientY;
      return { x:((cx-r.left)/r.width)*220, y:((cy-r.top)/r.height)*170 };
    }
    function hitDot(x,y) {
      for (var i=0;i<TDOTS.length;i++)
        if (Math.hypot(x-TDOTS[i].x, y-TDOTS[i].y)<22) return i;
      return null;
    }
    function hasEdge(a,b) {
      return drawn.some(function(e){ return (e[0]===a&&e[1]===b)||(e[0]===b&&e[1]===a); });
    }
    function allDone() {
      return TEDGES.every(function(e){ return hasEdge(e[0],e[1]); });
    }
    function sa(el,k,v){ el.setAttribute(k,v); }

    function redraw() {
      while(edgeLayer.firstChild) edgeLayer.removeChild(edgeLayer.firstChild);
      drawn.forEach(function(e){
        var a=TDOTS[e[0]],b=TDOTS[e[1]];
        var ln=document.createElementNS(NS,'line');
        sa(ln,'x1',a.x);sa(ln,'y1',a.y);sa(ln,'x2',b.x);sa(ln,'y2',b.y);
        sa(ln,'stroke', done?'url(#_vcOK3)':'url(#_vcEG3)');
        sa(ln,'stroke-width','2.5');sa(ln,'stroke-linecap','round');
        sa(ln,'filter','url(#_vcGl3)');
        edgeLayer.appendChild(ln);
      });

      dotEls.forEach(function(de,i){
        var conn = drawn.some(function(e){return e[0]===i||e[1]===i;});
        var isFr = dragFrom===i;
        var isHv = hoverDot===i&&dragging&&dragFrom!==i;
        var r    = isFr?16:isHv?15:12;
        sa(de.main,'r',r);
        sa(de.main,'fill', done?'url(#_vcOK3)':(conn||isFr)?'url(#_vcDG3)':'#fff');
        sa(de.main,'stroke',(conn||isFr||isHv)?'#FF6B35':'#cbd5e1');
        sa(de.main,'filter',(isFr||isHv)?'url(#_vcGl3)':'none');
        sa(de.inner,'fill',(conn||isFr)?'white':'#94a3b8');
        sa(de.inner,'r',done?'0':'3');
        sa(de.ring,'r',isHv?'22':'0');
        sa(de.pulse,'r',(!conn&&!done&&!isFr)?'18':'0');
      });

      TEDGES.forEach(function(e,i){
        var dr=drawn.some(function(de){return (de[0]===e[0]&&de[1]===e[1])||(de[0]===e[1]&&de[1]===e[0]);});
        pips[i].className='_vcap-pip'+(dr?' drawn':'')+(done?' done':'');
      });

      var rem=TEDGES.filter(function(e){return !hasEdge(e[0],e[1]);}).length;
      lbl.textContent = done?'✓ Verified!':
        dragging?'Release on a dot':
        drawn.length===0?'Drag between the dots':
        rem+' connection'+(rem!==1?'s':'')+' left';
      rst.style.display=(drawn.length>0&&!done)?'':'none';
    }

    function startDrag(e,i){
      if(done)return;
      dragging=true; dragFrom=i;
      var p=svgPt(e); dragPos=p;
      dragLine.style.display='';
      sa(dragLine,'x1',TDOTS[i].x);sa(dragLine,'y1',TDOTS[i].y);
      sa(dragLine,'x2',p.x);sa(dragLine,'y2',p.y);
      redraw();
    }
    function onMove(e){
      if(!dragging)return;
      var p=svgPt(e); dragPos=p;
      hoverDot=hitDot(p.x,p.y);
      sa(dragLine,'x2',p.x);sa(dragLine,'y2',p.y);
      redraw();
    }
    function onUp(e){
      if(!dragging)return;
      dragging=false; dragLine.style.display='none';
      var p=svgPt(e);
      var t=hitDot(p.x,p.y);
      if(t!==null&&t!==dragFrom&&!hasEdge(dragFrom,t)){
        drawn.push([dragFrom,t]);
        if(allDone()){ done=true; redraw(); setTimeout(onDone,700); return; }
      }
      dragFrom=null; hoverDot=null;
      redraw();
    }

    window.addEventListener('mousemove',onMove);
    window.addEventListener('mouseup',onUp);
    window.addEventListener('touchmove',onMove,{passive:false});
    window.addEventListener('touchend',onUp);

    wrap.appendChild(lbl);
    wrap.appendChild(svg);
    wrap.appendChild(progRow);
    wrap.appendChild(rst);
    redraw();
    return wrap;
  }

  /* ═══════════════════════════════════════════════════════════
     Step pills HTML
  ═══════════════════════════════════════════════════════════ */
  function buildPills(step) {
    var defs = ['Load','Watch','Verify'];
    var pills = el('div', '_vcap-pills');
    defs.forEach(function(name, i) {
      var cls = i < step ? '_vcap-pill-c' : i === step ? '_vcap-pill-a' : '_vcap-pill-i';
      var p = el('div', '_vcap-pill ' + cls);
      var num = el('span', '_vcap-pill-num');
      num.textContent = i + 1;
      p.appendChild(num);
      p.appendChild(document.createTextNode(name));
      pills.appendChild(p);
    });
    return pills;
  }

  /* ═══════════════════════════════════════════════════════════
     Main Widget class
  ═══════════════════════════════════════════════════════════ */
  function Widget(opts) {
    this.cfg    = assign({}, DEFAULTS, opts);
    this.root   = null;
    this.token  = null;
    this.answer = '';
    this.step   = 0;          // 0=Load 1=Watch 2=Verify
    this.timerHandle = null;
    this.countdown   = 0;
    this.failCount   = 0;
    this.blocked     = false;
    this._init();
  }

  Widget.prototype._init = function() {
    injectCSS();
    var sel = this.cfg.container;
    this.root = typeof sel === 'string' ? document.querySelector(sel) : sel;
    if (!this.root) { console.error('[VideoCap] container not found:', sel); return; }
    this.failCount = this.failCount || 0;
    this._phase2(null);
  };

  /* ─── Phase 1: reCAPTCHA box ─── */
  Widget.prototype._phase1 = function() {
    var self = this;
    var widget = el('div', '_vcap-lp-widget');
    var row    = buildRow('idle');
    widget.appendChild(row);
    widget.appendChild(this._p1footer());
    this.root.innerHTML = '';
    this.root.appendChild(widget);

    row.addEventListener('click', function() {
      widget.replaceChild(buildRow('loading'), row);
      setTimeout(function() { self._showPuzzle(widget); }, 1600);
    });
  };

  Widget.prototype._p1footer = function() {
    // small footer matching the lp-widget style
    var f = document.createElement('div');
    f.style.cssText = 'display:flex;align-items:center;justify-content:space-between;' +
      'padding:5px 12px 6px;border-top:1px solid #e0e0e0;' +
      'font-family:Roboto,sans-serif;font-size:8px;color:#9aa0a6;';
    f.innerHTML = '<span>Privacy · Terms</span><span><strong style="color:#FF6B35">VideoCap</strong></span>';
    return f;
  };

  /* ─── Show triangle puzzle inside Phase-1 box ─── */
  Widget.prototype._showPuzzle = function(widget) {
    var self = this;

    // swap to checked row
    var lr = widget.querySelector('._vcap-row');
    widget.replaceChild(buildRow('checked'), lr);

    // puzzle body
    var pb    = el('div', '_vcap-puzzle');
    var divEl = el('div', '_vcap-div');
    var inner = el('div', '_vcap-pi');

    inner.appendChild(buildTriangle(function() {
      // triangle done → switch to Phase 2
      self._phase2(widget);
    }));

    pb.appendChild(divEl);
    pb.appendChild(inner);

    var footer = widget.querySelector('div[style]');
    widget.insertBefore(pb, footer);
  };

  /* ─── Phase 2: Full VideoCap card ─── */
  Widget.prototype._phase2 = function(widget) {
    var self = this;

    // replace the whole lp-widget with the full card
    var cardWrap = el('div', '_vcap-card-wrap');
    var card     = el('div', '_vcap-card');
    cardWrap.appendChild(card);

    // header
    var hdr = el('div', '_vcap-hdr');
    var logoGrp = el('div', '_vcap-logo-grp');
    var icon = el('div', '_vcap-hdr-icon');
    icon.innerHTML = orangeShieldSVG();
    logoGrp.appendChild(icon);
    var title = el('h1', '_vcap-title');
    title.innerHTML = 'Video<span>Cap</span>';
    logoGrp.appendChild(title);
    hdr.appendChild(logoGrp);
    self.pillsEl = buildPills(0);
    hdr.appendChild(self.pillsEl);
    card.appendChild(hdr);

    // hero
    var hero = el('div', '_vcap-hero');
    var ht   = el('p', '_vcap-hero-title');
    ht.textContent = "Verify you're human 👋";
    var hs   = el('p', '_vcap-hero-sub');
    hs.textContent = 'Watch the short video, then answer the question below to continue.';
    hero.appendChild(ht); hero.appendChild(hs);
    card.appendChild(hero);

    // generate button
    self.genBtn = el('button', '_vcap-gen-btn');
    self.genBtn.textContent = 'Generate CAPTCHA';
    self.genBtn.addEventListener('click', function() { self._loadCaptcha(card); });
    card.appendChild(self.genBtn);

    // body placeholder
    self.bodyEl = el('div', '_vcap-body');
    var prompt = el('div', '_vcap-prompt');
    prompt.innerHTML =
      '<span class="_vcap-prompt-icon">🎥</span>' +
      '<span class="_vcap-prompt-txt">Click "Generate CAPTCHA" to begin</span>';
    self.bodyEl.appendChild(prompt);
    card.appendChild(self.bodyEl);

    // message section
    self.msgSec = el('div', '_vcap-msgsec');
    card.appendChild(self.msgSec);

    // retry row (hidden initially)
    self.retryRow = el('div', '_vcap-retry-row');
    self.retryRow.style.display = 'none';
    var retryBtn = el('button', '_vcap-retry-btn');
    retryBtn.textContent = 'Try New CAPTCHA';
    retryBtn.addEventListener('click', function() { self._loadCaptcha(card); });
    self.retryRow.appendChild(retryBtn);
    card.appendChild(self.retryRow);

    // footer
    card.appendChild(self._cardFooter());

    // mount
    self.root.innerHTML = ''; self.root.appendChild(cardWrap);
    // keep Generate CAPTCHA button visible
  };

  /* ─── load CAPTCHA from API ─── */
  Widget.prototype._loadCaptcha = function(card) {
    var self = this;

    self._clearTimer();
    self.answer = '';
    self.step   = 0;
    self._updatePills(card);
    self._clearMsg();
    self.retryRow.style.display = 'none';

    // disable generate button
    self.genBtn.disabled    = true;
    self.genBtn.textContent = 'Generating…';

    // show loading message
    self._setMsg('🛡️ Generating AI-resistant CAPTCHA…', 'loading');

    // show overlay spinner
    var overlay = el('div', '_vcap-overlay');
    overlay.innerHTML = '<div class="_vcap-spinner"></div>';
    document.body.appendChild(overlay);

    var hdrs = { 'Content-Type': 'application/json', 'X-API-Key': self.cfg.apiKey };

    fetch(self.cfg.apiUrl + '/api/captcha/generate', { headers: hdrs })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        document.body.removeChild(overlay);
        self.genBtn.disabled    = false;
        self.genBtn.textContent = 'Generate CAPTCHA';

        if (!d.success) throw new Error(d.error || 'Generation failed');

        self.token = d.token;
        self.step  = 1;
        self._updatePills(card);
        self._renderChallenge(card, d);
        self._setMsg('CAPTCHA ready — watch carefully and answer.', 'instruction');
      })
      .catch(function(err) {
        document.body.removeChild(overlay);
        self.genBtn.disabled    = false;
        self.genBtn.textContent = 'Generate CAPTCHA';
        self._setMsg('❌ ' + err.message, 'error');
        self.cfg.onError(err.message);
      });
  };

  /* ─── render video + question + input inside bodyEl ─── */
  Widget.prototype._renderChallenge = function(card, data) {
    var self = this;
    var body = self.bodyEl;
    body.innerHTML = '';

    /* video section */
    var vsec  = el('div', '_vcap-vsec');
    var badge = el('div', '_vcap-live-badge');
    badge.innerHTML = '<div class="_vcap-live-dot"></div><span class="_vcap-live-txt">LIVE</span>';
    vsec.appendChild(badge);

    var vid = document.createElement('video');
    vid.className = '_vcap-video';
    vid.controls  = true;
    vid.autoplay  = true;
    vid.muted     = true;
    vid.setAttribute('playsinline', '');
    vid.setAttribute('preload', 'auto');

    // H.264 source with explicit codec — primary
    var src1 = document.createElement('source');
    src1.setAttribute('src',  data.video_url);
    src1.setAttribute('type', 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"');
    vid.appendChild(src1);

    // plain mp4 fallback
    var src2 = document.createElement('source');
    src2.setAttribute('src',  data.video_url);
    src2.setAttribute('type', 'video/mp4');
    vid.appendChild(src2);

    vid.addEventListener('error', function() {
      self._setErr('Failed to load video. Make sure the backend is running.');
    });
    vid.addEventListener('ended', function() {
      self._setMsg('Watch carefully and answer — you have 10 seconds.', 'countdown');
      self.step = 2;
      self._updatePills(card);
      self._startTimer(card);
    });

    vsec.appendChild(vid);
    body.appendChild(vsec);

    /* question section */
    var qsec = el('div', '_vcap-qsec');
    var qbox = el('div', '_vcap-qbox');
    var qico = el('div', '_vcap-qicon');
    qico.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"' +
      ' stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="12" cy="12" r="10"/>' +
      '<path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>' +
      '<line x1="12" y1="17" x2="12.01" y2="17" stroke-width="3"/>' +
      '</svg>';
    qbox.appendChild(qico);

    var qcontent = el('div');
    var qlbl = el('span', '_vcap-qlbl');
    qlbl.textContent = 'Question';
    var qtxt = el('p', '_vcap-qtxt');
    qtxt.textContent = data.question || '';
    qcontent.appendChild(qlbl); qcontent.appendChild(qtxt);
    qbox.appendChild(qcontent);
    qsec.appendChild(qbox);
    body.appendChild(qsec);

    /* answer text input (exactly like original — NOT MCQ) */
    var ansWrap = el('div', '_vcap-ans-wrap');
    var inp = el('input', '_vcap-ans-inp');
    inp.type        = 'text';
    inp.placeholder = 'Type your answer here...';
    inp.autocomplete = 'off';
    inp.maxLength    = 100;
    inp.addEventListener('input', function() {
      self.answer = inp.value.slice(0, 100);
      inp.value   = self.answer;
      charEl.textContent = self.answer.length + ' / 100';
      verifyBtn.disabled = !self.answer.trim();
      if (self.answer.trim()) {
        self.step = 1;
        self._updatePills(card);
        self._setMsg('Answer entered! Click "Verify & Continue" or press Enter.', 'selected');
      }
    });
    inp.addEventListener('keypress', function(e) {
      if (e.key === 'Enter' && self.answer.trim()) self._submit(card, inp, verifyBtn);
    });

    var charEl = el('div', '_vcap-char');
    charEl.textContent = '0 / 100';
    ansWrap.appendChild(inp);
    ansWrap.appendChild(charEl);
    body.appendChild(ansWrap);

    /* verify button */
    var verifyBtn = el('button', '_vcap-verify');
    verifyBtn.disabled  = true;
    verifyBtn.innerHTML = '<span>🔒</span><span>Verify &amp; Continue</span><span>→</span>';
    verifyBtn.addEventListener('click', function() {
      self._submit(card, inp, verifyBtn);
    });
    body.appendChild(verifyBtn);
  };

  /* ─── submit answer ─── */
  Widget.prototype._submit = function(card, inp, btn) {
    var self = this;
    if (!self.answer.trim() || !self.token) return;

    self._clearTimer();
    self.step = 2;
    self._updatePills(card);

    btn.disabled    = true;
    btn.textContent = 'Verifying…';
    inp.disabled    = true;
    self._clearMsg();

    var overlay = el('div', '_vcap-overlay');
    overlay.innerHTML = '<div class="_vcap-spinner"></div>';
    document.body.appendChild(overlay);

    var hdrs = { 'Content-Type': 'application/json', 'X-API-Key': self.cfg.apiKey };
    fetch(self.cfg.apiUrl + '/api/captcha/validate', {
      method: 'POST', headers: hdrs,
      body: JSON.stringify({ token: self.token, answer: self.answer.trim() }),
    })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        document.body.removeChild(overlay);
        inp.disabled = false;
        if (d.success) {
          btn.innerHTML = '<span>🔒</span><span>Verify &amp; Continue</span><span>→</span>';
          self._setMsg('✅ ' + d.message, 'success-message');
          self.retryRow.style.display = 'none';
          self.cfg.onSuccess(self.token);
          setTimeout(function() { self._loadCaptcha(card); }, 3000);
        } else {
          btn.disabled  = false;
          btn.innerHTML = '<span>🔒</span><span>Verify &amp; Continue</span><span>→</span>';
          self.failCount = (self.failCount || 0) + 1;
          if (self.failCount >= 5) {
            self.blocked = true;
            self._clearTimer();
            self._setMsg('too many wrong attempts ⛔ Access denied. Retry After 2 mins', 'timeout');
            self.retryRow.style.display = 'none';
            inp.disabled = true;
            btn.disabled = true;
            self.cfg.onError('blocked');
            var blockSec = 120;
            var blockTimer = setInterval(function() {
              blockSec--;
              if (blockSec <= 0) {
                clearInterval(blockTimer);
                self.failCount = 0;
                self.blocked = false;
                self._loadCaptcha(card);
              }
            }, 1000);
          } else {
            var left = 5 - self.failCount;
            self._setMsg('❌ ' + d.message + ' — ' + left + ' attempt' + (left===1?'':'s') + ' left', 'retry-message');
            self.retryRow.style.display = '';
            self.cfg.onError(d.message);
            setTimeout(function() { self._loadCaptcha(card); }, 2000);
          }
        }
      })
      .catch(function(err) {
        document.body.removeChild(overlay);
        inp.disabled  = false;
        btn.disabled  = false;
        btn.innerHTML = '<span>🔒</span><span>Verify &amp; Continue</span><span>→</span>';
        self._setMsg('Validation failed. Please try again.', 'error');
        self.cfg.onError(err.message);
      });
  };

  /* ─── countdown timer (10 s after video ends) ─── */
  Widget.prototype._startTimer = function(card) {
    var self = this;
    self._clearTimer();
    self.countdown = 10;
    self.timerHandle = setInterval(function() {
      self.countdown--;
      var cm = self.msgSec.querySelector('._vcap-msg');
      if (cm) {
        var cs = cm.querySelector('._vcap-cdown');
        if (cs) cs.textContent = ' (' + self.countdown + 's)';
      }
      if (self.countdown <= 0) {
        self._clearTimer();
        self._setMsg('⏰ Time expired! Generating new CAPTCHA…', 'timeout');
        setTimeout(function() { self._loadCaptcha(card); }, 1000);
      }
    }, 1000);
  };

  Widget.prototype._clearTimer = function() {
    if (this.timerHandle) { clearInterval(this.timerHandle); this.timerHandle = null; }
    this.countdown = 0;
  };

  /* ─── pill update ─── */
  Widget.prototype._updatePills = function(card) {
    var hdr = card.querySelector('._vcap-hdr');
    if (!hdr) return;
    var old = hdr.querySelector('._vcap-pills');
    var np  = buildPills(this.step);
    if (old) hdr.replaceChild(np, old);
    else hdr.appendChild(np);
  };

  /* ─── message helpers ─── */
  Widget.prototype._clearMsg = function() {
    this.msgSec.innerHTML = '';
  };
  Widget.prototype._setMsg = function(text, type) {
    this.msgSec.innerHTML = '';
    var m = el('div', '_vcap-msg ' + type);
    // For countdown type, add the timer span
    if (type === 'countdown') {
      m.textContent = text;
      var cs = el('span', '_vcap-cdown');
      cs.textContent = ' (10s)';
      m.appendChild(cs);
    } else {
      m.textContent = text;
    }
    this.msgSec.appendChild(m);
  };
  Widget.prototype._setErr = function(text) {
    this.msgSec.innerHTML = '';
    var e = el('div', '_vcap-errmsg');
    e.textContent = '❌ ' + text;
    this.msgSec.appendChild(e);
  };

  /* ─── card footer (Encrypted · 30 sec · No tracking) ─── */
  Widget.prototype._cardFooter = function() {
    var footer = el('div', '_vcap-footer');

    var badges = el('div', '_vcap-fbadges');

    function badge(iconHTML, label) {
      var b = el('div', '_vcap-fbadge');
      b.innerHTML = iconHTML + '<span>' + label + '</span>';
      return b;
    }

    badges.appendChild(badge(
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
      'Encrypted'
    ));
    badges.appendChild(badge(
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
      '30 sec'
    ));
    badges.appendChild(badge(
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/>' +
      '<line x1="12" y1="20" x2="12.01" y2="20"/></svg>',
      'No tracking'
    ));

    footer.appendChild(badges);

    var fr = el('div', '_vcap-fright');
    fr.innerHTML = 'Protected by <strong>VideoCap</strong>';
    footer.appendChild(fr);

    return footer;
  };

  /* ═══════════════════════════════════════════════════════════
     Public API
  ═══════════════════════════════════════════════════════════ */
  W.VideoCap = {
    render: function(opts) { return new Widget(opts); },
  };

}(window));