// ዓለም ዛሬ — motion for the weekly video ("portal" style, chosen by the owner 10 Nov 2026).
// motion.py builds index.html with one scene per card (the cards' own HTML) and sets window.MOTION:
//   { total, fade, scenes: [{ id, type: "cover"|"story"|"follow", start, dur, voice, headEnd, sents }] }
// All times in seconds on the whole video's timeline; voice = when the narration starts (or null),
// headEnd / sents = end of the headline and start of each body sentence, relative to voice.
// Calm rules: no glow at the start, text stays still while it is read, nothing graphic or flashy.
(() => {
  const M = window.MOTION;
  const tl = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } });
  const LIGHT = "rgba(255,236,200,.95)", NOLIGHT = "rgba(255,236,200,0)";

  // a band of light runs through words in reading order (left to right): the words appear lit, then settle
  const sweep = (words, t, size = 18, span = 1.3) => {
    if (!words.length) return;
    const st = Math.min(0.08, span / words.length);
    tl.fromTo(words, { opacity: 0, textShadow: `0 0 ${size}px ${LIGHT}` },
                     { opacity: 1, duration: 0.3, stagger: st, ease: "sine.out" }, t);
    tl.to(words, { textShadow: `0 0 0px ${NOLIGHT}`, duration: 0.6, stagger: st }, t + 0.25);
  };
  // a thin ring ripples out (stats, the note tag)
  const ripple = (ring, t) => ring && tl.fromTo(ring, { scale: 0.05, opacity: 1 },
    { scale: 1, opacity: 0, duration: 0.8, ease: "power2.out", immediateRender: false }, t);
  // the number counts up from 0 (keeps prefix/suffix such as $ … ቢሊዮን or %)
  const countUp = (el, t) => {
    const m = el.textContent.match(/^(\D*?)([\d.,]+)(.*)$/);
    if (!m) return;
    const target = parseFloat(m[2].replace(/,/g, "")), dec = (m[2].split(".")[1] || "").length, o = { v: 0 };
    tl.to(o, { v: target, duration: 1.3, ease: "power2.out",
               onUpdate: () => { el.textContent = m[1] + o.v.toFixed(dec) + m[3]; } }, t);
  };

  M.scenes.forEach((sc, i) => {
    const el = document.getElementById(sc.id);
    const q = s => el.querySelector(s), qa = s => Array.from(el.querySelectorAll(s));
    const t0 = sc.start, end = sc.start + sc.dur;
    if (i) tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: M.fade, ease: "none" }, t0);   // crossfade in
    const v = sc.voice ?? t0 + 0.6;

    if (sc.type === "cover") {
      tl.fromTo(qa(".bg"), { scale: 1.0 }, { scale: 1.08, duration: sc.dur, ease: "none" }, t0);
      tl.from(q(".top"), { opacity: 0, y: -30, duration: 0.6 }, t0 + 0.1);
      tl.from(q(".date"), { opacity: 0, scale: 0.85, transformOrigin: "0% 100%", duration: 0.7 }, t0 + 0.3);
      tl.from(q(".lab"), { opacity: 0, x: -24, duration: 0.5 }, t0 + 0.7);
      sweep(qa(".lead-hl .hw"), t0 + 0.9, 24);
      tl.from(qa(".thumbs .th"), { opacity: 0, scale: 0.6, duration: 0.45, stagger: 0.12, ease: "back.out(1.8)" }, t0 + 1.6);
      tl.from(q(".thumbs .more"), { opacity: 0, x: -16, duration: 0.5 }, t0 + 2.2);
    }

    if (sc.type === "story") {
      tl.fromTo(qa(".hero img"), { scale: 1.0 }, { scale: 1.08, duration: sc.dur, ease: "none" }, t0);
      tl.from(q(".top"), { opacity: 0, y: -30, duration: 0.6 }, t0 + 0.1);
      // portal: the frosted panel opens as a growing circle from the top middle of the panel
      const sh = q(".sheet"), R = Math.hypot((sh.offsetWidth || 1048) / 2, (sh.offsetHeight || 856) - 70) + 20;
      tl.fromTo(sh, { clipPath: "circle(0px at 50% 70px)" },
                    { clipPath: `circle(${R}px at 50% 70px)`, duration: 0.85, ease: "power2.inOut" }, t0 + 0.2);
      tl.from(q(".kicker"), { opacity: 0, x: -24, duration: 0.5 }, t0 + 0.9);
      sweep(qa(".headline .hw"), v, 24, 1.2);
      const starts = (sc.sents || []).map(s => v + s - 0.15);
      qa(".body .sent").forEach((s, k) => sweep(Array.from(s.querySelectorAll(".bw")),
                                                starts[Math.min(k, starts.length - 1)] ?? v + 1.5, 18, 1.4));
      const s0 = (starts[0] ?? v + 1.5) + 0.8;
      if (q(".stats")) tl.from(q(".stats"), { opacity: 0, duration: 0.4 }, s0);
      qa(".stat").forEach((st, k) => {
        const t = s0 + 0.2 + k * 0.6;
        ripple(st.querySelector(".ring"), t);
        tl.fromTo(st.querySelector(".num"), { scale: 0, opacity: 0 },
                  { scale: 1, opacity: 1, duration: 0.55, ease: "back.out(1.8)" }, t + 0.05);
        countUp(st.querySelector(".num"), t + 0.05);
        tl.from(st.querySelector(".l"), { opacity: 0, y: 10, duration: 0.4 }, t + 0.3);
      });
      const last = Math.min((starts[starts.length - 1] ?? v) + 1.3, end - 2.2);
      ripple(q(".note .ring"), last);
      tl.fromTo(q(".note .tag"), { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.5, ease: "back.out(2.2)" }, last + 0.05);
      sweep(qa(".note .nw"), last + 0.35, 16, 1.0);
      tl.from(q(".foot"), { opacity: 0, duration: 0.6 }, last + 1.2);
    }

    if (sc.type === "follow") {
      tl.fromTo(qa(".blur"), { scale: 1.0 }, { scale: 1.06, duration: sc.dur, ease: "none" }, t0);
      tl.from(q(".top"), { opacity: 0, y: -30, duration: 0.6 }, t0 + 0.1);
      tl.from(q(".kick"), { opacity: 0, y: 14, duration: 0.5 }, t0 + 0.3);
      sweep(qa(".big .hw"), t0 + 0.5, 30, 0.6);
      tl.from(q(".tagline"), { opacity: 0, y: 16, duration: 0.6 }, t0 + 1.0);
      tl.from(qa(".ctas span"), { opacity: 0, scale: 0.7, duration: 0.45, stagger: 0.15, ease: "back.out(1.8)" }, t0 + 1.4);
      tl.from(q(".foot2"), { opacity: 0, duration: 0.6 }, t0 + 1.9);
    }
  });

  window.__timelines = window.__timelines || {};
  window.__timelines["main"] = tl;
  tl.seek(0);
})();
