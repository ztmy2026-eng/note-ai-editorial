(function () {
  'use strict';
  var QL = window.QuizLogic;
  var QUESTIONS = window.QUIZ_QUESTIONS || [];
  var KEY = 'stockquiz.progress.v1';
  var LATE_FROM = '21:00';
  var PER_SET = 5;

  // ---------- tiny DOM helper (always textContent, never innerHTML) ----------
  function h(tag, attrs) {
    var el = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) {
      var v = attrs[k];
      if (v === null || v === undefined || v === false) return;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) append(el, arguments[i]);
    return el;
  }
  function append(el, c) {
    if (c === null || c === undefined || c === false) return;
    if (Array.isArray(c)) { c.forEach(function (x) { append(el, x); }); return; }
    el.appendChild(c.nodeType ? c : document.createTextNode(String(c)));
  }
  function $(sel) { return document.querySelector(sel); }

  // ---------- JST helpers ----------
  var timeFmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Tokyo', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
  });
  function jstParts(now) {
    var o = {};
    timeFmt.formatToParts(now).forEach(function (p) { o[p.type] = p.value; });
    return { h: Number(o.hour), m: Number(o.minute), s: Number(o.second) };
  }
  function jstHHMM(now) {
    var p = jstParts(now);
    return (p.h < 10 ? '0' : '') + p.h + ':' + (p.m < 10 ? '0' : '') + p.m;
  }
  function today() { return QL.jstDate(new Date()); }
  function timeLeftText() {
    var p = jstParts(new Date());
    var left = 86400 - (p.h * 3600 + p.m * 60 + p.s);
    var mins = Math.max(1, Math.ceil(left / 60));
    var hh = Math.floor(mins / 60), mm = mins % 60;
    return 'あと' + (hh > 0 ? hh + '時間' : '') + mm + '分';
  }
  var WEEK = ['日', '月', '火', '水', '木', '金', '土'];
  function weekday(dateStr) { return WEEK[new Date(dateStr + 'T00:00:00Z').getUTCDay()]; }

  // ---------- storage ----------
  var Store = {
    ref: null, localOk: false, failed: false,
    testLocal: function () {
      try { localStorage.getItem(KEY); this.localOk = true; } catch (e) { this.localOk = false; }
    },
    withTimeout: function (p, ms) {
      return Promise.race([p, new Promise(function (r) { setTimeout(function () { r(null); }, ms); })]);
    },
    init: async function () {
      this.testLocal();
      try {
        if (!window.claude || typeof window.claude.use !== 'function') return;
        var db = await this.withTimeout(window.claude.use('db'), 8000);
        var user = await this.withTimeout(window.claude.use('user'), 8000);
        if (!db || !user) return;
        var uid = await user.id();
        if (!uid) return;
        this.ref = db.doc('data/users/' + uid + '/progress');
      } catch (e) { this.ref = null; }
    },
    readLocal: function () {
      if (!this.localOk) return null;
      try { return localStorage.getItem(KEY); } catch (e) { this.localOk = false; return null; }
    },
    load: async function () {
      var raw = null;
      if (this.ref) {
        try {
          var snap = await this.ref.get();
          var d = snap.exists ? snap.data() : null;
          raw = d && typeof d.json === 'string' ? d.json : null;
        } catch (e) { this.ref = null; }
      }
      if (raw === null) raw = this.readLocal();
      if (!this.ref && !this.localOk) this.failed = true;
      return QL.loadState(raw);
    },
    writeLocal: function (raw) {
      if (!this.localOk) return false;
      try { localStorage.setItem(KEY, raw); return true; } catch (e) { this.localOk = false; return false; }
    },
    write: async function (raw) {
      var saved = false;
      if (this.ref) {
        try { await this.ref.set({ json: raw }); saved = true; } catch (e) { /* fall through to local */ }
      }
      if (!saved) saved = this.writeLocal(raw);
      this.failed = !saved && !this.ref;
      if (!saved) this.failed = true;
      showBanner();
    }
  };
  function showBanner() { $('#banner').hidden = !Store.failed; }

  var Saver = {
    timer: null, busy: false, dirty: false,
    queue: function () {
      this.dirty = true;
      clearTimeout(this.timer);
      this.timer = setTimeout(function () { Saver.run(); }, 300);
    },
    run: async function () {
      if (this.busy) return;
      this.busy = true;
      try {
        while (this.dirty) {
          this.dirty = false;
          await Store.write(QL.serialize(App.S));
        }
      } finally { this.busy = false; }
    },
    flushLocal: function () {
      if (this.dirty && !Store.ref) { Store.writeLocal(QL.serialize(App.S)); }
    }
  };

  // ---------- app state ----------
  var App = {
    S: QL.emptyState(), tab: 'home', session: null, usedToday: {}, renderedDate: null
  };
  function persist() { Saver.queue(); }
  function isDone(date) {
    return App.S.doneLog.some(function (e) { return e.date === date; });
  }
  function doneEntry(date) {
    return App.S.doneLog.filter(function (e) { return e.date === date; })[0] || null;
  }

  // ---------- views ----------
  var Views = {};
  App.Views = Views;
  window.QuizApp = App; // Task 8b adds Views.wrong / Views.stats / Views.words

  function placeholder(title) {
    return function (root) {
      root.appendChild(h('section', { class: 'card placeholder' },
        h('h2', { text: title }), h('p', { class: 'muted', text: '準備中' })));
    };
  }
  Views.wrong = placeholder('不正解リスト');
  Views.stats = placeholder('成績');
  Views.words = placeholder('用語帳');

  // ----- Home -----
  Views.home = function (root) {
    var date = today();
    App.renderedDate = date;
    var streak = QL.currentStreak(App.S, date);
    var done = doneEntry(date);
    var cold = streak === 0;

    root.appendChild(h('section', { class: 'hero', 'aria-label': '連続日数' },
      h('div', { class: 'hero-num' },
        h('span', { class: 'hero-flame' + (cold ? ' cold' : ''), 'aria-hidden': 'true', text: '🔥' }),
        h('span', { class: 'hero-n' + (cold ? ' cold' : ''), id: 'streak-n', text: String(streak) }),
        h('span', { class: 'hero-unit', text: '日連続' })),
      h('p', { class: 'hero-sub', text: cold ? '今日の5問から、はじめましょう' : '毎日5問で、連続を伸ばそう' })));

    if (done) {
      root.appendChild(h('section', { class: 'status done', id: 'status', 'aria-label': '今日の状態' },
        h('span', { class: 'status-main', text: '✓ 今日は完了' }),
        h('span', { class: 'status-sub', text: done.time ? '完了 ' + done.time + '(日本時間)' : '完了' })));
    } else {
      root.appendChild(h('section', { class: 'status todo', id: 'status', 'aria-label': '今日の状態' },
        h('span', { class: 'status-main', text: '今日は未完了' }),
        h('span', { class: 'status-sub', id: 'timeleft', text: timeLeftText() + '(24時まで)' })));
    }

    root.appendChild(h('button', { type: 'button', class: 'btn', id: 'start-btn', onclick: function () { startSession(); } },
      done ? 'もっとやる(+5問)' : '今日の5問をはじめる'));

    var due = QL.dueWrong(App.S, date).length;
    root.appendChild(h('p', { class: 'due-line' },
      due > 0 ? ['復習する問題が ', h('strong', { text: due + '問' }), ' 待っています'] : '復習待ちの問題はありません'));

    root.appendChild(calendar(date));
  };

  function calendar(date) {
    var doneMap = {};
    App.S.doneLog.forEach(function (e) { if (!doneMap[e.date] || (e.time || '') < (doneMap[e.date].time || '')) doneMap[e.date] = e; });
    var days = [];
    for (var i = 13; i >= 0; i--) days.push(QL.addDays(date, -i));
    var wrap = h('div', { class: 'cal' });
    days.forEach(function (d) {
      var e = doneMap[d];
      var late = !!(e && e.time && e.time >= LATE_FROM);
      var label = d.slice(5).replace('-', '/') + (e ? ' 完了' + (late ? '(遅め)' : '') : (d === date ? ' 今日・未完了' : ' 未完了'));
      wrap.appendChild(h('div', { class: 'cal-day', role: 'img', 'aria-label': label },
        h('span', { text: weekday(d) }),
        h('span', { class: 'cal-dot' + (e ? ' done' : '') + (d === date ? ' today' : '') }),
        h('span', { text: String(Number(d.slice(8))) }),
        h('span', { class: 'cal-late' + (late ? '' : ' none'), text: '遅め' })));
    });
    return h('section', { class: 'card', 'aria-label': '直近14日' },
      h('div', { class: 'cal-head' }, h('h3', { text: '直近14日' }), h('span', { class: 'muted', text: '日本時間' })),
      wrap,
      h('div', { class: 'cal-legend' },
        h('span', null, h('span', { style: 'color:var(--ok)', text: '●' }), ' 完了'), h('span', { text: '○ 未完了' }), h('span', { text: '遅め = 21時以降に完了' })));
  }

  // ----- Quiz -----
  function startSession() {
    var date = today();
    var used = App.usedToday[date] || (App.usedToday[date] = {});
    var pool = QUESTIONS.filter(function (q) { return !used[q.id]; });
    if (pool.length < PER_SET) pool = QUESTIONS;
    var picked = QL.pickDaily(App.S, pool, date, PER_SET);
    var dueIds = {};
    QL.dueWrong(App.S, date).forEach(function (e) { dueIds[e.id] = true; });
    picked.forEach(function (q) { used[q.id] = true; });
    App.session = {
      date: date, isMore: isDone(date), idx: 0, phase: 'q', score: 0, wrong: [], newBadges: [],
      items: picked.map(function (q) { return { q: q, retry: !!dueIds[q.id], pres: null, input: null, correct: null }; })
    };
    go('quiz');
  }

  Views.quiz = function (root) {
    var s = App.session;
    if (!s) {
      var done = isDone(today());
      root.appendChild(h('section', { class: 'card placeholder' },
        h('h2', { text: done ? '今日の5問は完了しています' : '今日の5問' }),
        h('p', { class: 'muted', text: done ? 'もっと解いても、連続日数は変わりません。' : '1日5問。3分ほどで終わります。' }),
        h('div', { class: 'btnrow', style: 'margin-top:16px' },
          h('button', { type: 'button', class: 'btn', onclick: function () { startSession(); } }, done ? 'もっとやる(+5問)' : '今日の5問をはじめる'))));
      return;
    }
    if (s.phase === 'result') return resultView(root, s);
    var item = s.items[s.idx];
    if (!item.pres) item.pres = QL.present(item.q, item.retry);
    questionView(root, s, item);
  };

  function questionView(root, s, item) {
    var pres = item.pres, answered = s.phase === 'a';
    var n = s.items.length;
    root.appendChild(h('div', { class: 'qhead' },
      h('span', { class: 'qprog', 'aria-label': n + '問中' + (s.idx + 1) + '問目', text: (s.idx + 1) + '/' + n }),
      h('div', { class: 'bar', 'aria-hidden': 'true' }, h('i', { style: 'width:' + Math.round((s.idx + (answered ? 1 : 0)) / n * 100) + '%' }))));

    var tags = [];
    if (item.retry) tags.push(h('span', { class: 'tag retry', text: '前に間違えた問題' }));
    if (s.isMore) tags.push(h('span', { class: 'tag', text: 'もっとやる' }));
    if (tags.length) root.appendChild(h('div', { class: 'tags' }, tags));

    root.appendChild(h('h2', { class: 'qtext', id: 'qtext', text: pres.question }));

    if (pres.type === 'number') numberInput(root, s, item, answered);
    else choiceList(root, s, item, answered);

    if (answered) feedback(root, s, item);
  }

  var KEYS = ['ア', 'イ', 'ウ', 'エ', 'オ', 'カ'];
  function choiceList(root, s, item, answered) {
    var pres = item.pres;
    var ul = h('ul', { class: 'choices', 'aria-labelledby': 'qtext' });
    pres.choices.forEach(function (c, i) {
      var cls = 'choice', mark = null;
      if (answered && i === pres.correctIndex) { cls += ' right'; mark = '○ 正解'; }
      else if (answered && i === item.input) { cls += ' wrong'; mark = '× あなたの答え'; }
      ul.appendChild(h('li', null,
        h('button', { type: 'button', class: cls, disabled: answered, onclick: function () { answer(i); } },
          h('span', { class: 'choice-key', 'aria-hidden': 'true', text: KEYS[i] }),
          h('span', { class: 'choice-text', text: c }),
          mark ? h('span', { class: 'choice-mark', text: mark }) : null)));
    });
    root.appendChild(ul);
  }

  function numberInput(root, s, item, answered) {
    var unit = item.q.unit || '';
    var input = h('input', {
      id: 'numin', class: 'numin', type: 'text', inputmode: 'decimal', autocomplete: 'off', 'aria-labelledby': 'qtext',
      disabled: answered, value: answered ? String(item.input) : null
    });
    var form = h('form', { class: 'numform', onsubmit: function (ev) {
      ev.preventDefault();
      if (!input.value.trim()) { input.focus(); return; }
      answer(input.value);
    } },
      h('div', { class: 'numrow' }, input, unit ? h('span', { class: 'numunit', text: unit }) : null),
      answered ? null : h('button', { type: 'submit', class: 'btn' }, '回答する'));
    root.appendChild(form);
    if (!answered) setTimeout(function () { try { input.focus({ preventScroll: true }); } catch (e) { /* ignore */ } }, 0);
  }

  function answer(input) {
    var s = App.session;
    if (!s || s.phase !== 'q') return;
    var item = s.items[s.idx], q = item.q, pres = item.pres;
    var correct = pres.type === 'number'
      ? QL.numberAnswerOk(input, pres.answer, q.tol || 0)
      : input === pres.correctIndex;
    item.input = input;
    item.correct = correct;
    s.phase = 'a';
    if (correct) s.score++; else s.wrong.push(item);

    var st = QL.recordAnswer(App.S, q, correct, s.date);
    st = QL.addStat(st, q, correct);
    if (st.seen.indexOf(q.id) < 0) st = Object.assign({}, st, { seen: st.seen.concat(q.id) });
    App.S = st;
    persist();

    var ans = pres.type === 'number' ? pres.answer + (q.unit || '') : pres.choices[pres.correctIndex];
    $('#live').textContent = correct ? '正解です' : '不正解です。正解は ' + ans;
    render();
    var v = $('#verdict');
    if (v) v.focus({ preventScroll: false });
  }

  function safeUrl(u) { return typeof u === 'string' && /^https?:\/\//i.test(u) ? u : null; }

  function feedback(root, s, item) {
    var pres = item.pres, q = item.q, ok = item.correct;
    var ansText = pres.type === 'number' ? pres.answer + (q.unit || '') : pres.choices[pres.correctIndex];
    var box = h('section', { class: 'fb', 'aria-label': '解説' });
    box.appendChild(h('div', { class: 'verdict ' + (ok ? 'ok' : 'ng'), id: 'verdict', tabindex: '-1' },
      h('span', { class: 'verdict-mark', 'aria-hidden': 'true', text: ok ? '○' : '×' }),
      h('span', { text: ok ? '正解!' : '不正解' })));
    box.appendChild(h('p', { class: 'fb-answer' }, '正解: ', h('b', { text: ansText })));
    box.appendChild(h('p', { class: 'fb-explain', text: pres.explain }));
    if (pres.term) {
      box.appendChild(h('p', { class: 'fb-term' }, '用語: ', h('b', { text: pres.term }), q.termDef ? ' ' + q.termDef : ''));
    }
    if (pres.asof) {
      var src = pres.source || {};
      var url = safeUrl(src.url);
      box.appendChild(h('p', { class: 'asof' },
        '数字は ' + pres.asof + ' 時点 ／ 出典: ',
        url ? h('a', { href: url, target: '_blank', rel: 'noopener noreferrer', text: src.name || url }) : (src.name || '不明'),
        QL.isStale(q, s.date) ? h('span', { class: 'stale', text: '古い数字' }) : null));
    }
    box.appendChild(reportButton(q.id));
    var last = s.idx === s.items.length - 1;
    box.appendChild(h('button', { type: 'button', class: 'btn', id: 'next-btn', onclick: function () { next(); } },
      last ? '結果を見る' : '次へ'));
    root.appendChild(box);
  }

  function reportButton(id) {
    var already = App.S.reports.indexOf(id) >= 0;
    var b = h('button', { type: 'button', class: 'report', disabled: already }, already ? '報告ずみ' : 'この問題が変');
    b.addEventListener('click', function () {
      if (App.S.reports.indexOf(id) >= 0) return;
      App.S = Object.assign({}, App.S, { reports: App.S.reports.concat(id) });
      persist();
      b.disabled = true;
      b.textContent = '報告ずみ';
    });
    return b;
  }

  function next() {
    var s = App.session;
    if (s.idx < s.items.length - 1) { s.idx++; s.phase = 'q'; render(); window.scrollTo(0, 0); return; }
    complete(s);
    s.phase = 'result';
    render();
    window.scrollTo(0, 0);
  }

  function complete(s) {
    var st = App.S;
    var first = !s.isMore && !isDone(s.date);
    if (first) {
      st = QL.updateStreak(st, s.date);
      st = Object.assign({}, st, { doneLog: st.doneLog.concat({ date: s.date, time: jstHHMM(new Date()) }) });
    }
    var have = {};
    st.badges.forEach(function (b) { have[b] = true; });
    s.newBadges = QL.badgesFor(st).filter(function (b) { return !have[b]; });
    if (s.newBadges.length) st = Object.assign({}, st, { badges: st.badges.concat(s.newBadges) });
    App.S = st;
    persist();
  }

  var BADGE_NAMES = { first: 'はじめの一歩(初めて回答)', streak7: '7日連続', streak30: '30日連続', q100: '100問回答' };

  function resultView(root, s) {
    var n = s.items.length;
    var streak = QL.currentStreak(App.S, s.date);
    root.appendChild(h('section', { class: 'card score' },
      h('p', { class: 'muted', text: s.isMore ? 'もっとやる の結果' : '今日の5問 完了' }),
      h('p', { class: 'score-n', 'aria-label': n + '問中' + s.score + '問正解' }, String(s.score), h('small', { text: '/' + n })),
      h('p', { class: 'hero-sub' }, '🔥 ', h('strong', { text: streak + '日連続' }), s.isMore ? '(連続日数は変わりません)' : '')));
    if (s.newBadges.length) {
      root.appendChild(h('section', { class: 'newbadge', role: 'status' },
        '新しいバッジ: ' + s.newBadges.map(function (b) { return BADGE_NAMES[b] || b; }).join('、')));
    }
    if (s.wrong.length) {
      var card = h('section', { class: 'card', 'aria-label': '間違えた問題' }, h('h3', { text: '間違えた問題(' + s.wrong.length + ')' }));
      s.wrong.forEach(function (it) {
        var p = it.pres;
        var ans = p.type === 'number' ? p.answer + (it.q.unit || '') : p.choices[p.correctIndex];
        card.appendChild(h('div', { class: 'wrongitem' },
          h('p', { class: 'qtext', text: p.question }),
          h('p', { class: 'fb-answer' }, '正解: ', h('b', { text: ans })),
          h('p', { class: 'fb-explain', text: p.explain })));
      });
      root.appendChild(card);
    } else {
      root.appendChild(h('p', { class: 'due-line', text: '全問正解です。' }));
    }
    root.appendChild(h('div', { class: 'btnrow' },
      h('button', { type: 'button', class: 'btn', id: 'home-btn', onclick: function () { App.session = null; go('home'); } }, 'ホームに戻る'),
      h('button', { type: 'button', class: 'btn secondary', onclick: function () { startSession(); } }, 'もっとやる(+5問)')));
  }

  // ---------- navigation ----------
  var TABS = ['home', 'quiz', 'wrong', 'stats', 'words'];
  function go(tab, fromPop) {
    if (TABS.indexOf(tab) < 0) tab = 'home';
    var changed = App.tab !== tab;
    App.tab = tab;
    if (!fromPop && changed) { try { history.pushState({ tab: tab }, ''); } catch (e) { /* ignore */ } }
    render();
    window.scrollTo(0, 0);
  }
  function render() {
    var root = $('#view');
    root.replaceChildren();
    (Views[App.tab] || Views.home)(root);
    document.querySelectorAll('.tab').forEach(function (b) {
      if (b.getAttribute('data-tab') === App.tab) b.setAttribute('aria-current', 'page');
      else b.removeAttribute('aria-current');
    });
  }
  App.render = render;
  App.go = go;

  function tick() {
    if (App.tab !== 'home') return;
    if (App.renderedDate !== today()) { render(); return; }
    var el = $('#timeleft');
    if (el) el.textContent = timeLeftText() + '(24時まで)';
  }

  // ---------- boot ----------
  async function boot() {
    document.querySelectorAll('.tab').forEach(function (b) {
      b.addEventListener('click', function () { go(b.getAttribute('data-tab')); });
    });
    window.addEventListener('popstate', function (ev) { go((ev.state && ev.state.tab) || 'home', true); });
    try { history.replaceState({ tab: 'home' }, ''); } catch (e) { /* ignore */ }
    window.addEventListener('pagehide', function () { Saver.flushLocal(); });
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') Saver.flushLocal(); else tick();
    });
    try {
      await Store.init();
      App.S = await Store.load();
    } catch (e) {
      App.S = QL.emptyState();
      Store.failed = true;
    }
    showBanner();
    render();
    setInterval(tick, 30000);
  }
  boot();
})();
