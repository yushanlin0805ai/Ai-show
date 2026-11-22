// zodiac 品牌共用動畫：starfield（改寫自 HyperFrames registry/blocks/starfield，Apache-2.0）與進場動作。
// 全部可跳秒（seekable），沒有 Math.random。
window.Zodiac = {
  // 在 container 裡撒星星，回傳 render(p)，p = 0..1 為這段的進度
  starfield(container, { w = 1080, h = 700, count = 140, dur = 2, big = 1 } = {}) {
    const TAU = Math.PI * 2;
    const rnd = (n) => { const x = Math.sin(n * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
    const pal = ["#fff7e0", "#ffe08a"];
    const stars = [];
    for (let i = 0; i < count; i++) {
      const r = rnd(i + 7000), tier = r < 0.7 ? 0 : r < 0.95 ? 1 : 2, size = [1.6, 2.6, 4][tier] * big;
      const el = document.createElement("div");
      el.className = "star";
      el.style.width = el.style.height = size + "px";
      const color = i % 3 === 0 ? pal[1] : pal[0];
      el.style.background = color;
      if (tier === 2) { el.style.borderRadius = "50%"; el.style.boxShadow = `0 0 4px 1px ${color}, 0 0 10px 3px ${color}80`; }
      container.appendChild(el);
      stars.push({ el, x: rnd(i + 5000) * w, y: Math.round(rnd(i + 6000) * h), drift: (tier === 0 ? 2 : 5) * dur,
        omega: TAU * Math.max(1, Math.round((dur / 1.6) * (2 + rnd(i + 4000) * 2))), phi: TAU * rnd(i + 1000),
        base: 0.75 + rnd(i + 2000) * 0.25, amp: tier === 2 ? 0.12 : 0.2 + rnd(i + 3000) * 0.2 });
    }
    const render = (p) => stars.forEach((s) => {
      s.el.style.transform = `translate3d(${s.x - s.drift * (p - 0.5)}px,${s.y}px,0)`;
      s.el.style.opacity = Math.min(1, s.base + s.amp * Math.sin(s.omega * p + s.phi));
    });
    render(0);
    return render;
  },
  // 把 starfield 接到時間軸上
  addStars(tl, render, start, dur) {
    const st = { p: 0 };
    tl.to(st, { p: 1, duration: dur, ease: "none", onUpdate: () => render(st.p) }, start);
  },
  fadeUp: (tl, s, t, d = 0.4) => tl.fromTo(s, { opacity: 0, y: 24 }, { opacity: 1, y: 0, duration: d, ease: "power2.out" }, t),
  pop: (tl, s, t) => tl.fromTo(s, { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(2)" }, t),
  tagIn: (tl, s, t) => tl.fromTo(s, { opacity: 0, y: 12, scale: 0.8 }, { opacity: 1, y: 0, scale: 1, duration: 0.3, ease: "back.out(2.5)" }, t),
};
