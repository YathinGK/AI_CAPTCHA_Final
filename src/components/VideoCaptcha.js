import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import './VideoCaptcha.css';

/* ─────────────────────────────────────────────────────────────
   LOGO
───────────────────────────────────────────────────────────── */
const LogoIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
    <path
      d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6L12 2z"
      fill="rgba(255,255,255,0.25)" stroke="white" strokeWidth="2" strokeLinejoin="round"
    />
    <polygon points="10,8 16,12 10,16" fill="white" />
  </svg>
);

/* ─────────────────────────────────────────────────────────────
   STEP PILLS
───────────────────────────────────────────────────────────── */
const StepPills = ({ currentStep }) => {
  const steps = [{ label: 'Load', num: '1' }, { label: 'Watch', num: '2' }, { label: 'Verify', num: '3' }];
  return (
    <div className="step-pills">
      {steps.map((s, i) => {
        let cls = 'step-pill inactive';
        if (i < currentStep) cls = 'step-pill completed';
        else if (i === currentStep) cls = 'step-pill active';
        return (
          <div key={s.label} className={cls}>
            <span className="step-pill-num">{s.num}</span>{s.label}
          </div>
        );
      })}
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────
   DRAG-TO-CONNECT TRIANGLE PUZZLE
───────────────────────────────────────────────────────────── */
const TrianglePuzzle = ({ onSuccess }) => {
  const svgRef = useRef(null);
  const SVG_W  = 220;
  const SVG_H  = 170;

  const DOTS = [
    { id: 0, x: 110, y: 22  },
    { id: 1, x: 28,  y: 152 },
    { id: 2, x: 192, y: 152 },
  ];

  const REQUIRED_EDGES = [[0,1],[1,2],[0,2]];

  const [drawnEdges, setDrawnEdges] = useState([]);
  const [dragging, setDragging]     = useState(false);
  const [dragFrom, setDragFrom]     = useState(null);
  const [dragPos, setDragPos]       = useState({ x: 0, y: 0 });
  const [hoverDot, setHoverDot]     = useState(null);
  const [done, setDone]             = useState(false);
  const [flash, setFlash]           = useState(false);
  const [errorEdge, setErrorEdge]   = useState(null);

  const toSVGCoords = useCallback((e) => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };
    const rect = svg.getBoundingClientRect();
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: ((clientX - rect.left) / rect.width)  * SVG_W,
      y: ((clientY - rect.top)  / rect.height) * SVG_H,
    };
  }, []);

  const hitTest = useCallback((x, y) => {
    for (const d of DOTS) {
      if (Math.hypot(x - d.x, y - d.y) < 22) return d.id;
    }
    return null;
  }, []);

  const hasEdge = (a, b, edges) =>
    edges.some(([x, y]) => (x===a&&y===b)||(x===b&&y===a));

  const allDone = (edges) =>
    REQUIRED_EDGES.every(([a,b]) => edges.some(([x,y])=>(x===a&&y===b)||(x===b&&y===a)));

  const onMouseDownDot = (e, id) => {
    e.preventDefault();
    if (done) return;
    setDragging(true);
    setDragFrom(id);
    setDragPos(toSVGCoords(e));
  };

  const onMouseMove = useCallback((e) => {
    if (!dragging) return;
    const pos = toSVGCoords(e);
    setDragPos(pos);
    setHoverDot(hitTest(pos.x, pos.y));
  }, [dragging, toSVGCoords, hitTest]);

  const onMouseUp = useCallback((e) => {
    if (!dragging) return;
    setDragging(false);
    const pos = toSVGCoords(e);
    const target = hitTest(pos.x, pos.y);
    if (target !== null && target !== dragFrom) {
      if (hasEdge(dragFrom, target, drawnEdges)) {
        setErrorEdge([dragFrom, target]);
        setTimeout(() => setErrorEdge(null), 600);
      } else {
        const next = [...drawnEdges, [dragFrom, target]];
        setDrawnEdges(next);
        if (allDone(next)) {
          setDone(true);
          setFlash(true);
          setTimeout(onSuccess, 900);
        }
      }
    }
    setDragFrom(null);
    setHoverDot(null);
  }, [dragging, dragFrom, drawnEdges, toSVGCoords, hitTest, onSuccess]);

  useEffect(() => {
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    window.addEventListener('touchmove', onMouseMove, { passive: false });
    window.addEventListener('touchend', onMouseUp);
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('touchmove', onMouseMove);
      window.removeEventListener('touchend', onMouseUp);
    };
  }, [onMouseMove, onMouseUp]);

  const drawnCount = drawnEdges.filter(([a,b]) =>
    REQUIRED_EDGES.some(([x,y])=>(x===a&&y===b)||(x===b&&y===a))
  ).length;

  const statusMsg = done
    ? '✓ Verified!'
    : dragging ? 'Release on a dot'
    : drawnEdges.length === 0 ? 'Drag between the dots'
    : `${3 - drawnCount} connection${3 - drawnCount !== 1 ? 's' : ''} left`;

  return (
    <div className={`tri-wrap${flash ? ' tri-flash' : ''}`}>
      <p className="tri-label">{statusMsg}</p>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="tri-svg"
        style={{ touchAction: 'none', userSelect: 'none' }}
      >
        <defs>
          <linearGradient id="edgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#FF6B35" />
            <stop offset="100%" stopColor="#FFB347" />
          </linearGradient>
          <linearGradient id="dotGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#FF6B35" />
            <stop offset="100%" stopColor="#FF9A5C" />
          </linearGradient>
          <linearGradient id="doneGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stopColor="#22c55e" />
            <stop offset="100%" stopColor="#16a34a" />
          </linearGradient>
          <filter id="glw">
            <feGaussianBlur stdDeviation="2.5" result="b"/>
            <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {/* Ghost guide */}
        <polygon
          points={DOTS.map(d=>`${d.x},${d.y}`).join(' ')}
          fill="none" stroke="#e2e8f0" strokeWidth="1.5" strokeDasharray="5 4"
        />

        {/* Drawn edges */}
        {drawnEdges.map(([a,b], i) => {
          const da = DOTS[a], db = DOTS[b];
          const isErr = errorEdge&&((errorEdge[0]===a&&errorEdge[1]===b)||(errorEdge[0]===b&&errorEdge[1]===a));
          return (
            <line key={i}
              x1={da.x} y1={da.y} x2={db.x} y2={db.y}
              stroke={done ? 'url(#doneGrad)' : isErr ? '#ef4444' : 'url(#edgeGrad)'}
              strokeWidth="2.5" strokeLinecap="round"
              filter="url(#glw)"
              className="tri-edge-drawn"
            />
          );
        })}

        {/* Live drag line */}
        {dragging && dragFrom !== null && (
          <line
            x1={DOTS[dragFrom].x} y1={DOTS[dragFrom].y}
            x2={dragPos.x} y2={dragPos.y}
            stroke="rgba(255,107,53,0.5)"
            strokeWidth="2" strokeLinecap="round" strokeDasharray="5 4"
          />
        )}

        {/* Dots */}
        {DOTS.map((d) => {
          const isConn   = drawnEdges.some(([a,b])=>a===d.id||b===d.id);
          const isFrom   = dragFrom === d.id;
          const isTarget = hoverDot === d.id && dragging && dragFrom !== d.id;
          const r = isFrom ? 16 : isTarget ? 15 : 12;

          return (
            <g key={d.id}
              onMouseDown={(e) => onMouseDownDot(e, d.id)}
              onTouchStart={(e) => { e.preventDefault(); onMouseDownDot(e, d.id); }}
              style={{ cursor: done ? 'default' : 'grab' }}
            >
              {isFrom && <circle cx={d.x} cy={d.y} r="24" fill="rgba(255,107,53,0.1)" className="tri-drag-ring" />}
              {isTarget && <circle cx={d.x} cy={d.y} r="22" fill="none" stroke="rgba(255,107,53,0.4)" strokeWidth="1.5" className="tri-hover-ring" />}
              {!isConn && !done && !isFrom && <circle cx={d.x} cy={d.y} r="18" fill="rgba(255,107,53,0.06)" className="tri-pulse" />}
              <circle cx={d.x} cy={d.y} r={r}
                fill={done ? 'url(#doneGrad)' : (isConn||isFrom) ? 'url(#dotGrad)' : '#fff'}
                stroke={(isConn||isFrom||isTarget) ? '#FF6B35' : '#cbd5e1'}
                strokeWidth="2"
                filter={(isFrom||isTarget) ? 'url(#glw)' : 'none'}
                style={{ transition: 'r 0.12s ease' }}
              />
              {done
                ? <text x={d.x} y={d.y+5} textAnchor="middle" fontSize="10" fill="white" fontWeight="700">✓</text>
                : <circle cx={d.x} cy={d.y} r="3" fill={(isConn||isFrom) ? 'white' : '#94a3b8'} />
              }
            </g>
          );
        })}
      </svg>

      {/* Progress pips */}
      <div className="tri-progress">
        {REQUIRED_EDGES.map(([a,b], i) => {
          const drawn = drawnEdges.some(([x,y])=>(x===a&&y===b)||(x===b&&y===a));
          return <div key={i} className={`tri-pip${drawn?' drawn':''}${done?' done':''}`} />;
        })}
      </div>

      {drawnEdges.length > 0 && !done && (
        <button className="tri-reset" onClick={() => setDrawnEdges([])}>↺ Reset</button>
      )}
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────
   LANDING WIDGET
───────────────────────────────────────────────────────────── */
const LandingWidget = ({ onProceed }) => {
  const [state, setState] = useState('idle');

  const handleCheck = () => {
    if (state !== 'idle') return;
    setState('loading');
    setTimeout(() => setState('puzzle'), 1800);
  };

  return (
    <div className="lp-root">
      <div className="lp-layout">
        <div className={`lp-widget${state === 'puzzle' ? ' lp-widget-expanded' : ''}`}>

          {(state === 'idle' || state === 'loading') && (
            <div className="lp-recaptcha-row" onClick={handleCheck}>
              <div className="lp-checkbox-area">
                <div className={`lp-checkbox${state === 'loading' ? ' lp-checkbox-loading' : ''}`}>
                  {state === 'loading' && (
                    <svg className="lp-check-spin" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="9" stroke="#e2e8f0" strokeWidth="2.5"/>
                      <path d="M12 3a9 9 0 0 1 9 9" stroke="url(#cGrad)" strokeWidth="2.5" strokeLinecap="round"/>
                      <defs>
                        <linearGradient id="cGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#FF6B35"/>
                          <stop offset="100%" stopColor="#FFB347"/>
                        </linearGradient>
                      </defs>
                    </svg>
                  )}
                </div>
              </div>
              <span className="lp-robot-label">I'm not a robot</span>
              <div className="lp-logo-block">
                <div className="lp-vc-icon">
                  <svg width="32" height="36" viewBox="0 0 56 64" fill="none">
                    <defs>
                      <linearGradient id="vcGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#4f97f5"/>
                        <stop offset="100%" stopColor="#1a6fd4"/>
                      </linearGradient>
                    </defs>
                    <path d="M28 2L4 13v17c0 14.5 10.2 28.1 24 31.2C41.8 58.1 52 44.5 52 30V13L28 2z" fill="url(#vcGrad)"/>
                    <path d="M28 2L4 13v4l24-11 24 11v-4L28 2z" fill="rgba(255,255,255,0.2)"/>
                    <polygon points="21,20 39,30 21,40" fill="white"/>
                  </svg>
                </div>
                <span className="lp-vc-name">Video Cap</span>
                <span className="lp-vc-links">Privacy - Terms</span>
              </div>
            </div>
          )}

          {state === 'puzzle' && (
            <div className="lp-puzzle-body">
              <div className="lp-recaptcha-row lp-recaptcha-row--checked">
                <div className="lp-checkbox-area">
                  <div className="lp-checkbox lp-checkbox-checked">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <polyline points="20 6 9 17 4 12" stroke="white" strokeWidth="3"
                        strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  </div>
                </div>
                <span className="lp-robot-label">Connect the dots to verify</span>
                <div className="lp-logo-block">
                  <div className="lp-vc-icon">
                    <svg width="32" height="36" viewBox="0 0 56 64" fill="none">
                      <defs>
                        <linearGradient id="vcGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#4f97f5"/>
                          <stop offset="100%" stopColor="#1a6fd4"/>
                        </linearGradient>
                      </defs>
                      <path d="M28 2L4 13v17c0 14.5 10.2 28.1 24 31.2C41.8 58.1 52 44.5 52 30V13L28 2z" fill="url(#vcGrad2)"/>
                      <path d="M28 2L4 13v4l24-11 24 11v-4L28 2z" fill="rgba(255,255,255,0.2)"/>
                      <polygon points="21,20 39,30 21,40" fill="white"/>
                    </svg>
                  </div>
                  <span className="lp-vc-name">VideoCap</span>
                  <span className="lp-vc-links">Privacy - Terms</span>
                </div>
              </div>
              <div className="lp-divider" />
              <div className="lp-puzzle-inner">
                <TrianglePuzzle onSuccess={onProceed} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────
   VIDEO LOAD TIMEOUT  (3 seconds)
   If the <video> element has not fired 'canplay' within 3 s of
   receiving the src, we request a cached CAPTCHA instead.
───────────────────────────────────────────────────────────── */
const VIDEO_LOAD_TIMEOUT_MS = 3000;

/* ─────────────────────────────────────────────────────────────
   MAIN CAPTCHA PAGE
───────────────────────────────────────────────────────────── */
const VideoCaptcha = () => {
  const [page, setPage] = useState('captcha');

  const [videoUrl, setVideoUrl]             = useState('');
  const [question, setQuestion]             = useState('');
  const [selectedAnswer, setSelectedAnswer] = useState('');
  const [resultMessage, setResultMessage]   = useState('');
  const [messageType, setMessageType]       = useState('');
  const [loading, setLoading]               = useState(false);
  const [token, setToken]                   = useState('');
  const [error, setError]                   = useState('');
  const [captchaGenerated, setCaptchaGenerated] = useState(false);
  const [timeoutCountdown, setTimeoutCountdown] = useState(0);
  const [autoTimeoutId, setAutoTimeoutId]   = useState(null);
  const [currentStep, setCurrentStep]       = useState(0);
  const [fromCache, setFromCache]           = useState(false);

  // ── Video-load timeout refs ────────────────────────────────────────────
  const videoLoadTimerRef  = useRef(null);
  const videoCanPlayFired  = useRef(false);
  const fetchingFallback   = useRef(false);   // guard against double-fetch

  const API_BASE_URL      = 'http://localhost:5000';
  const MAX_ANSWER_LENGTH = 100;

  useEffect(() => () => {
    if (autoTimeoutId) { clearTimeout(autoTimeoutId); clearInterval(autoTimeoutId); }
    _clearVideoLoadTimer();
  }, [autoTimeoutId]);

  // ── Video load timer helpers ───────────────────────────────────────────
  const _clearVideoLoadTimer = () => {
    if (videoLoadTimerRef.current) {
      clearTimeout(videoLoadTimerRef.current);
      videoLoadTimerRef.current = null;
    }
  };

  const _startVideoLoadTimer = useCallback(() => {
    _clearVideoLoadTimer();
    videoCanPlayFired.current  = false;
    fetchingFallback.current   = false;

    videoLoadTimerRef.current = setTimeout(() => {
      if (!videoCanPlayFired.current && !fetchingFallback.current) {
        fetchingFallback.current = true;
        console.warn(`[VideoCap] Video did not load within ${VIDEO_LOAD_TIMEOUT_MS}ms — fetching cached CAPTCHA`);
        setResultMessage('⚡ Video took too long — loading a cached challenge…');
        setMessageType('loading');
        // Re-request; the backend will return a cached video immediately
        _fetchFromServer(true);
      }
    }, VIDEO_LOAD_TIMEOUT_MS);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Answer-timeout helpers (10 s after video ends) ────────────────────
  const startAutoTimeout = () => {
    setTimeoutCountdown(10);
    if (autoTimeoutId) { clearTimeout(autoTimeoutId); clearInterval(autoTimeoutId); }
    let c = 10;
    const id = setInterval(() => {
      c--;
      setTimeoutCountdown(c);
      if (c <= 0) {
        clearInterval(id);
        setResultMessage('⏰ Time expired! Generating new CAPTCHA...');
        setMessageType('timeout');
        setTimeout(fetchCaptchaData, 1000);
      }
    }, 1000);
    setAutoTimeoutId(id);
  };

  const clearAutoTimeout = () => {
    if (autoTimeoutId) { clearTimeout(autoTimeoutId); clearInterval(autoTimeoutId); setAutoTimeoutId(null); }
    setTimeoutCountdown(0);
  };

  const handleVideoEnded = () => {
    setResultMessage('Watch carefully and answer — you have 10 seconds.');
    setMessageType('countdown');
    setCurrentStep(2);
    startAutoTimeout();
  };

  const resetCaptchaStates = () => {
    setTimeoutCountdown(0); clearAutoTimeout();
    _clearVideoLoadTimer();
    setSelectedAnswer(''); setResultMessage(''); setMessageType(''); setCurrentStep(0);
  };

  // ── Core fetch (used by both normal flow and fallback) ─────────────────
  const _fetchFromServer = async (forceCache = false) => {
    const url = forceCache
      ? `${API_BASE_URL}/api/generate?prefer_cache=1`
      : `${API_BASE_URL}/api/generate`;

    try {
      const r = await axios.get(url);
      if (r.data.success) {
        const isCached = !!r.data.from_cache;
        setFromCache(isCached);
        setVideoUrl(`${API_BASE_URL}${r.data.video_url}`);
        setQuestion(r.data.question);
        setToken(r.data.token);
        setCaptchaGenerated(true);
        setCurrentStep(1);
        setResultMessage(
          isCached
            ? '⚡ Loaded a cached challenge — watch carefully and answer.'
            : 'CAPTCHA ready — watch carefully and answer.'
        );
        setMessageType('instruction');
        // Start the 3-second video-element load watchdog
        _startVideoLoadTimer();
      } else {
        setError(r.data.error || 'Failed to generate CAPTCHA. Please try again.');
      }
    } catch {
      setError('Network error. Please check if the backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const fetchCaptchaData = async () => {
    setLoading(true);
    setError('');
    resetCaptchaStates();
    setCaptchaGenerated(false);
    setFromCache(false);
    setResultMessage('🛡️ Generating AI-resistant CAPTCHA...');
    setMessageType('loading');
    await _fetchFromServer(false);
  };

  // ── Video element event handlers ───────────────────────────────────────
  const handleVideoCanPlay = () => {
    // Video is ready — cancel the fallback timer
    videoCanPlayFired.current = true;
    _clearVideoLoadTimer();
  };

  const handleVideoError = () => {
    _clearVideoLoadTimer();
    if (!fetchingFallback.current) {
      fetchingFallback.current = true;
      setError('Failed to load video — fetching cached challenge…');
      setTimeout(() => {
        setError('');
        _fetchFromServer(true);
      }, 800);
    }
  };

  // ── Validate ───────────────────────────────────────────────────────────
  const validateAnswer = async () => {
    if (!selectedAnswer.trim()) { setError('Please type an answer before submitting.'); return; }
    clearAutoTimeout(); setCurrentStep(2); setLoading(true); setError('');
    try {
      const r = await axios.post(`${API_BASE_URL}/api/validate`, { token, answer: selectedAnswer.trim() });
      if (r.data.success) {
        setResultMessage('✅ ' + r.data.message); setMessageType('success-message');
        setTimeout(handleRetry, 3000);
      } else {
        setResultMessage('❌ ' + r.data.message); setMessageType('retry-message');
        setTimeout(handleRetry, 2000);
      }
    } catch { setError('Validation failed. Please try again.'); }
    finally { setLoading(false); }
  };

  const handleAnswerChange = (e) => {
    const val = e.target.value.slice(0, MAX_ANSWER_LENGTH);
    setSelectedAnswer(val); setError('');
    if (val.trim()) {
      setCurrentStep(1);
      setResultMessage('Answer entered! Click "Verify & Continue" or press Enter.');
      setMessageType('selected');
    }
  };

  const handleRetry = () => fetchCaptchaData();

  if (page === 'landing') return <LandingWidget onProceed={() => setPage('captcha')} />;

  return (
    <div className="video-captcha-container">
      <div className="captcha-card">
        <div className="captcha-header">
          <div className="captcha-logo-group">
            <div className="captcha-header-icon"><LogoIcon /></div>
            <h1 className="captcha-title">Video<span>Cap</span></h1>
          </div>
          <StepPills currentStep={currentStep} />
        </div>

        <div className="captcha-hero">
          <p className="captcha-hero-title">Verify you're human 👋</p>
          <p className="captcha-hero-subtitle">Watch the short video, then answer the question below to continue.</p>
        </div>

        {!captchaGenerated && (
          <button onClick={fetchCaptchaData} disabled={loading} className="generate-btn">
            {loading ? 'Generating…' : 'Generate CAPTCHA'}
          </button>
        )}

        {captchaGenerated ? (
          <div className="captcha-body">
            <div className="video-section">
              <div className="video-live-badge">
                <div className="video-live-dot" />
                <span className="video-live-text">{fromCache ? 'CACHED' : 'LIVE'}</span>
              </div>
              {/*
                key={videoUrl} forces React to unmount + remount the <video>
                element whenever the URL changes, which restarts the load
                watchdog cleanly.
              */}
              <video
                key={videoUrl}
                src={videoUrl}
                controls
                autoPlay
                muted
                playsInline
                preload="auto"
                className="captcha-video"
                onCanPlay={handleVideoCanPlay}
                onError={handleVideoError}
                onEnded={handleVideoEnded}
              >
                {/* Explicit source with codec hint helps Chrome pick the right decoder */}
                <source src={videoUrl} type='video/mp4; codecs="avc1.42E01E, mp4a.40.2"' />
                <source src={videoUrl} type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>

            <div className="question-section">
              <div className="question-box">
                <div className="question-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
                    <line x1="12" y1="17" x2="12.01" y2="17" strokeWidth="3"/>
                  </svg>
                </div>
                <div className="question-content">
                  <span className="question-label">Question</span>
                  <p className="question-text">{question}</p>
                </div>
              </div>
            </div>

            <div className="answer-input-wrapper">
              <input
                type="text"
                value={selectedAnswer}
                onChange={handleAnswerChange}
                placeholder="Type your answer here..."
                disabled={loading}
                className="answer-input"
                autoComplete="off"
                maxLength={MAX_ANSWER_LENGTH}
                onKeyPress={(e) => { if (e.key==='Enter' && selectedAnswer.trim()) validateAnswer(); }}
              />
              <div className="char-counter">{selectedAnswer.length} / {MAX_ANSWER_LENGTH}</div>
            </div>

            <button
              className="verify-btn-full"
              onClick={validateAnswer}
              disabled={!selectedAnswer.trim() || loading}
            >
              {loading ? 'Verifying…' : <><span>🔒</span><span>Verify &amp; Continue</span><span>→</span></>}
            </button>
          </div>
        ) : (
          !loading && (
            <div className="captcha-body">
              <div className="generate-prompt">
                <span className="generate-prompt-icon">🎥</span>
                <span className="generate-prompt-text">Click "Generate CAPTCHA" to begin</span>
              </div>
            </div>
          )
        )}

        <div className="message-section">
          {error && <div className="error-message">❌ {error}</div>}
          {resultMessage && (
            <div className={`message ${messageType}`}>
              {resultMessage}
              {timeoutCountdown > 0 && <span className="countdown-timer"> ({timeoutCountdown}s)</span>}
            </div>
          )}
        </div>

        {resultMessage && !resultMessage.includes('Successful') && captchaGenerated && (
          <div className="retry-section">
            <button className="retry-btn" onClick={handleRetry} disabled={loading}>Try New CAPTCHA</button>
          </div>
        )}

        <div className="captcha-footer">
          <div className="footer-badges">
            <div className="footer-badge-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg><span>Encrypted</span>
            </div>
            <div className="footer-badge-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
              </svg><span>30 sec</span>
            </div>
            <div className="footer-badge-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39"/>
                <line x1="12" y1="20" x2="12.01" y2="20"/>
              </svg><span>No tracking</span>
            </div>
          </div>
          <div className="footer-right">Protected by <strong>VideoCap</strong></div>
        </div>
      </div>

      {loading && <div className="loading-overlay"><div className="spinner"/></div>}
    </div>
  );
};

export default VideoCaptcha;