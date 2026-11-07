(function (root) {
  'use strict';

  var fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit'
  });

  function jstDate(now) {
    return fmt.format(now);
  }

  function toDays(s) {
    var p = s.split('-').map(Number);
    return Date.UTC(p[0], p[1] - 1, p[2]) / 86400000;
  }

  function daysBetween(a, b) {
    return Math.round(toDays(b) - toDays(a));
  }

  function updateStreak(state, today) {
    var s = state || {};
    var last = s.lastDoneDate || null;
    var streak = s.streak || 0;
    var next;
    if (last === today) next = streak || 1;
    else if (last && daysBetween(last, today) === 1) next = streak + 1;
    else next = 1;
    return Object.assign({}, s, { streak: next, lastDoneDate: today });
  }

  function currentStreak(state, today) {
    var s = state || {};
    if (!s.lastDoneDate) return 0;
    var gap = daysBetween(s.lastDoneDate, today);
    return gap >= 0 && gap <= 1 ? (s.streak || 0) : 0;
  }

  function addDays(dateStr, n) {
    var d = new Date(toDays(dateStr) * 86400000 + n * 86400000);
    return d.toISOString().slice(0, 10);
  }

  var STAGE_DAYS = [1, 3, 7];

  function stageDays(stage) {
    return STAGE_DAYS[Math.min(stage, STAGE_DAYS.length - 1)];
  }

  function recordAnswer(state, q, correct, today) {
    var s = state || {};
    var list = s.wrongList || [];
    var found = false;
    var next = [];
    list.forEach(function (e) {
      if (e.id !== q.id) { next.push(e); return; }
      found = true;
      if (!correct) {
        next.push({ id: e.id, stage: 0, nextDue: addDays(today, stageDays(0)), okInRow: 0 });
      } else if (e.okInRow + 1 >= 2) {
        // graduated: drop from the list
      } else {
        var stage = e.stage + 1;
        next.push({ id: e.id, stage: stage, nextDue: addDays(today, stageDays(stage)), okInRow: e.okInRow + 1 });
      }
    });
    if (!found && !correct) {
      next.push({ id: q.id, stage: 0, nextDue: addDays(today, stageDays(0)), okInRow: 0 });
    }
    return Object.assign({}, s, { wrongList: next });
  }

  function dueWrong(state, today) {
    var list = (state && state.wrongList) || [];
    return list.filter(function (e) { return e.nextDue <= today; })
      .sort(function (a, b) { return a.nextDue < b.nextDue ? -1 : a.nextDue > b.nextDue ? 1 : 0; });
  }

  function shuffle(arr, rng) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  var SECTORS = ['semi_ai', 'energy', 'health', 'robotics'];

  function dayOfYear(dateStr) {
    return daysBetween(dateStr.slice(0, 4) + '-01-01', dateStr) + 1;
  }

  function accuracy(stats, field) {
    var byLevel = (stats && stats[field]) || {};
    var right = 0, total = 0;
    Object.keys(byLevel).forEach(function (lv) {
      var e = byLevel[lv] || {};
      right += Number(e.right) || 0;
      total += Number(e.total) || 0;
    });
    return total > 0 ? right / total : 0.5;
  }

  // Weighted random order (Efraimidis-Spirakis): higher weight tends to come first.
  function weightedOrder(list, weightOf, rng) {
    return shuffle(list, rng).map(function (q) {
      var w = weightOf(q);
      return { q: q, k: Math.pow(Math.max(rng(), 1e-12), 1 / w) };
    }).sort(function (a, b) { return b.k - a.k; }).map(function (x) { return x.q; });
  }

  function pickDaily(state, Q, today, n, rng) {
    var st = state || {};
    var count = n === undefined ? 5 : n;
    var rand = rng || Math.random;
    var level = st.level || 'basic';
    var seen = {};
    (st.seen || []).forEach(function (id) { seen[id] = true; });
    var byId = {};
    Q.forEach(function (q) { byId[q.id] = q; });

    var out = [];
    var used = {};
    function add(q) {
      if (out.length >= count || used[q.id]) return;
      used[q.id] = true;
      out.push(q);
    }

    // 1) due wrong-list questions, hard cap of 2
    var due = 0;
    dueWrong(st, today).forEach(function (e) {
      if (due >= 2 || !byId[e.id]) return;
      due++;
      add(byId[e.id]);
    });

    // 2) emphasis alternates by day parity; weak fields weigh more
    var basicsDay = dayOfYear(today) % 2 === 0;
    function weightOf(q) {
      var preferred = (q.field === 'basics') === basicsDay && (basicsDay || SECTORS.indexOf(q.field) >= 0);
      var weak = 1 + (1 - accuracy(st.stats, q.field)) * 2;
      return (preferred ? 4 : 1) * weak;
    }
    function fill(list) {
      weightedOrder(list.filter(function (q) { return !used[q.id]; }), weightOf, rand).forEach(add);
    }
    // wrong-list questions that are not due yet are never served as ordinary questions
    var notDue = {};
    (st.wrongList || []).forEach(function (e) { if (e && e.nextDue > today) notDue[e.id] = true; });
    function ok(q) { return !notDue[q.id]; }
    fill(Q.filter(function (q) { return q.level === level && !seen[q.id] && ok(q); }));
    fill(Q.filter(function (q) { return q.level === level && ok(q); }));
    fill(Q.filter(ok));
    fill(Q); // last resort
    return out;
  }

  function present(q, isRetry, rng) {
    var rand = rng || Math.random;
    var text = q.question;
    var choices = q.choices;
    var answer = q.answer;
    if (isRetry && q.variants && q.variants.length) {
      var others = q.variants.filter(function (v) { return v && v.question && v.question !== q.question; });
      if (others.length) {
        var v = others[Math.min(Math.floor(rand() * others.length), others.length - 1)];
        if (q.type === 'number') {
          text = v.question;
          if (v.answer !== undefined) answer = v.answer;
        } else if (v.choices && v.answer !== undefined) {
          // a variant whose answer is not among its own choices is unanswerable: keep the original
          if (v.choices.indexOf(v.answer) >= 0) { text = v.question; choices = v.choices; answer = v.answer; }
        } else {
          text = v.question;
        }
      }
    }
    var out = {
      id: q.id, question: text, choices: null, correctIndex: -1, type: q.type,
      explain: q.explain, term: q.term, asof: q.asof, source: q.source
    };
    if (q.type === 'number') {
      out.answer = answer;
      return out;
    }
    var arranged = shuffle(choices, rand);
    var idx = arranged.indexOf(answer);
    if (isRetry && arranged.length > 1 && new Set(arranged).size === arranged.length) {
      var origIdx = q.choices.indexOf(q.answer);
      if (idx === origIdx) {
        var to = (idx + 1) % arranged.length;
        var t = arranged[idx]; arranged[idx] = arranged[to]; arranged[to] = t;
        idx = to;
      }
    }
    out.choices = arranged;
    out.correctIndex = idx;
    return out;
  }

  function addStat(state, q, correct) {
    var s = Object.assign({}, state);
    var stats = Object.assign({}, s.stats || {});
    var byLevel = Object.assign({}, stats[q.field] || {});
    var cur = byLevel[q.level] || { right: 0, total: 0 };
    byLevel[q.level] = { right: cur.right + (correct ? 1 : 0), total: cur.total + 1 };
    stats[q.field] = byLevel;
    s.stats = stats;
    s.recent = (s.recent || []).concat(correct ? 1 : 0).slice(-20);
    return s;
  }

  function suggestLevel(state) {
    var recent = (state && state.recent) || [];
    if (recent.length < 20) return null;
    var right = recent.reduce(function (a, b) { return a + b; }, 0);
    if (!(right / recent.length > 0.8)) return null;
    var order = ['basic', 'mid', 'adv'];
    var i = order.indexOf(state.level || 'basic');
    return i >= 0 && i < order.length - 1 ? order[i + 1] : null;
  }

  function totalAnswers(state) {
    var n = 0, stats = (state && state.stats) || {};
    Object.keys(stats).forEach(function (f) {
      Object.keys(stats[f] || {}).forEach(function (l) { n += (stats[f][l] && stats[f][l].total) || 0; });
    });
    return n;
  }

  function badgesFor(state) {
    var out = [], n = totalAnswers(state), st = (state && state.streak) || 0;
    if (n >= 1) out.push('first');
    if (st >= 7) out.push('streak7');
    if (st >= 30) out.push('streak30');
    if (n >= 100) out.push('q100');
    return out;
  }

  function numberAnswerOk(input, answer, tol) {
    var t = String(input == null ? '' : input)
      .replace(/[０-９]/g, function (c) { return String.fromCharCode(c.charCodeAt(0) - 0xFEE0); })
      .replace(/[．。]/g, '.')
      .replace(/[－−ー]/g, '-')
      .replace(/[，,]/g, '')
      .replace(/(\d)[\s\u3000]+(?=\d)/g, '$1\u0001')
      .replace(/[\s\u3000]/g, '')
      .replace(/^(-?(?:\d+\.?\d*|\.\d+))[^\d.\-]+$/, '$1');
    if (!/^-?(\d+\.?\d*|\.\d+)$/.test(t)) return false;
    return Math.abs(parseFloat(t) - answer) <= tol + 1e-9;
  }

  function isStale(q, today) {
    if (!q || !q.asof || q.stale === false) return false;
    return daysBetween(q.checked || q.asof, today) > 90;
  }

  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  function isObj(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
  function isNum(x) { return typeof x === 'number' && isFinite(x); }
  function isDateStr(x) { return typeof x === 'string' && DATE_RE.test(x); }

  function emptyState() {
    return {
      streak: 0, lastDoneDate: null, doneLog: [], wrongList: [], stats: {},
      recent: [], seen: [], level: 'basic', badges: [], reports: []
    };
  }

  function strings(a) {
    return Array.isArray(a) ? a.filter(function (x) { return typeof x === 'string'; }) : [];
  }

  function loadState(raw) {
    var out = emptyState();
    var p;
    try { p = JSON.parse(raw); } catch (e) { return out; }
    if (!isObj(p)) return out;
    if (isNum(p.streak) && p.streak >= 0) out.streak = p.streak;
    if (isDateStr(p.lastDoneDate)) out.lastDoneDate = p.lastDoneDate;
    if (p.level === 'basic' || p.level === 'mid' || p.level === 'adv') out.level = p.level;
    out.seen = strings(p.seen);
    out.badges = strings(p.badges);
    out.reports = strings(p.reports);
    if (Array.isArray(p.recent)) {
      out.recent = p.recent.filter(function (x) { return x === 0 || x === 1; }).slice(-20);
    }
    if (Array.isArray(p.doneLog)) {
      out.doneLog = p.doneLog.filter(function (e) { return isObj(e) && typeof e.date === 'string'; });
    }
    if (Array.isArray(p.wrongList)) {
      p.wrongList.forEach(function (e) {
        if (!isObj(e) || typeof e.id !== 'string' || e.id === '' || !isDateStr(e.nextDue)) return;
        out.wrongList.push({
          id: e.id,
          stage: isNum(e.stage) ? e.stage : 0,
          nextDue: e.nextDue,
          okInRow: isNum(e.okInRow) ? e.okInRow : 0
        });
      });
    }
    if (isObj(p.stats)) {
      Object.keys(p.stats).forEach(function (f) {
        var lv = p.stats[f];
        if (!isObj(lv)) return;
        var clean = {};
        Object.keys(lv).forEach(function (l) {
          var c = lv[l];
          if (isObj(c) && isNum(c.right) && isNum(c.total)) clean[l] = { right: c.right, total: c.total };
        });
        if (Object.keys(clean).length) out.stats[f] = clean;
      });
    }
    return out;
  }

  function serialize(state) {
    return JSON.stringify(state);
  }

  // ---------- compare card (pure) ----------
  var MINUS = '−';
  function num1(v) { // at most 1 decimal, no trailing .0, thousands separators
    var r = Math.round(Math.abs(v) * 10) / 10;
    var parts = String(r).split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return parts.join('.');
  }
  function fmtAmount(value, unit) {
    var u = unit || '';
    var neg = value < 0 ? MINUS : '';
    var abs = Math.abs(value);
    if ((u === '億ドル' || u === '億円') && abs >= 10000) {
      var rounded = Math.round(abs * 10) / 10;
      var cho = Math.floor(rounded / 10000);
      var oku = Math.round((rounded - cho * 10000) * 10) / 10;
      var tail = u.slice(1); // ドル / 円
      if (oku === 0) return neg + num1(cho) + '兆' + tail;
      return neg + num1(cho) + '兆' + num1(oku) + '億' + tail;
    }
    return neg + num1(abs) + u;
  }
  function fmtPct(value) {
    var r = Math.round(value * 10) / 10;
    if (r === 0) return '0%';
    return (r < 0 ? MINUS : '+') + num1(r) + '%';
  }
  function isNum(v) { return typeof v === 'number' && isFinite(v); }
  function timesText(x) { return x >= 10 ? String(Math.round(x)) : (Math.round(x * 10) / 10).toFixed(1); }
  function ratioTextFor(cur, v) {
    var ratio = cur / v;
    if (ratio >= 2) {
      var t = Math.round(ratio * 10) / 10;
      return '今回は約' + timesText(t) + '倍';
    }
    if (ratio >= 1) return '今回は+' + Math.round((ratio - 1) * 100) + '%';
    return '今回は' + MINUS + Math.round((1 - ratio) * 100) + '%';
  }
  function rateSummary(rows, cur, peers) {
    var best = null;
    rows.forEach(function (r) {
      if (!r.current && r.value > 0 && (!best || r.value > best.value)) best = r;
    });
    if (!cur || !best) return undefined;
    var head = '今回の' + fmtPct(cur.value) + 'は、' + (peers ? 'ほかのカテゴリーで最高(' : 'ここに並べた過去の中で最高(') + best.label + ' ' + fmtPct(best.value) + ')';
    if (cur.value <= 0) return head + 'を下回っています';
    if (cur.value > best.value) {
      var x = cur.value / best.value;
      return head + 'の約' + timesText(Math.round(x * 10) / 10) + '倍';
    }
    return head + 'の約' + Math.max(1, Math.round(cur.value / best.value * 10)) + '割';
  }
  function compareView(compare) {
    var out = { groups: [], hot: null };
    var groups = compare && Array.isArray(compare.groups) ? compare.groups : [];
    groups.forEach(function (g) {
      if (!g || typeof g !== 'object' || !Array.isArray(g.rows)) return;
      var kind = g.kind === 'rate' ? 'rate' : 'level';
      var rows = g.rows.filter(function (r) { return r && typeof r === 'object' && isNum(r.value); });
      if (!rows.length) return;
      var max = 0;
      rows.forEach(function (r) { max = Math.max(max, Math.abs(r.value)); });
      var cur = null;
      rows.forEach(function (r) { if (r.current === true && !cur) cur = r; });
      var noRatio = g.noRatio === true;
      var view = {
        title: String(g.title || ''), kind: kind, noRatio: noRatio,
        rows: rows.map(function (r) {
          var w = r.value === 0 || max === 0 ? 0 : Math.min(100, Math.max(2, Math.round(Math.abs(r.value) / max * 100)));
          var o = {
            label: String(r.label || ''), value: r.value, unit: r.unit, current: r === cur,
            note: r.note, asof: r.asof, source: r.source,
            text: kind === 'rate' ? fmtPct(r.value) : fmtAmount(r.value, r.unit),
            widthPct: w
          };
          if (kind === 'level' && !noRatio && cur && r !== cur && r.noRatio !== true &&
              r.value > 0 && cur.value > 0 && r.basis === cur.basis) {
            o.ratioText = ratioTextFor(cur.value, r.value);
          }
          return o;
        })
      };
      if (kind === 'rate') {
        var sm = rateSummary(rows.map(function (r) { return { label: String(r.label || ''), value: r.value, current: r === cur }; }), cur ? { value: cur.value } : null, g.compareTo === 'peers');
        if (sm) { view.summary = sm; if (!out.hot && g.compareTo !== 'peers') out.hot = 'ホットさの目安:' + sm; }
      }
      out.groups.push(view);
    });
    return out;
  }

  var api = {
    jstDate: jstDate,
    daysBetween: daysBetween,
    updateStreak: updateStreak,
    currentStreak: currentStreak,
    addDays: addDays,
    STAGE_DAYS: STAGE_DAYS,
    recordAnswer: recordAnswer,
    dueWrong: dueWrong,
    pickDaily: pickDaily,
    present: present,
    addStat: addStat,
    suggestLevel: suggestLevel,
    badgesFor: badgesFor,
    numberAnswerOk: numberAnswerOk,
    isStale: isStale,
    fmtAmount: fmtAmount,
    fmtPct: fmtPct,
    compareView: compareView,
    emptyState: emptyState,
    loadState: loadState,
    serialize: serialize
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.QuizLogic = Object.assign(root.QuizLogic || {}, api);
})(typeof window !== 'undefined' ? window : globalThis);
