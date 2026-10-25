// 不正解リスト / 成績 / 用語帳. Loaded after app.js; uses QuizApp (S, Views, render, util).
(function () {
  'use strict';
  var App = window.QuizApp, QL = window.QuizLogic;
  var QUESTIONS = window.QUIZ_QUESTIONS || [];
  var U = App.util, h = U.h;

  var FIELD_NAMES = { basics: '投資の基礎', semi_ai: '半導体・AI', energy: 'エネルギー', health: 'ヘルスケア', robotics: 'ロボット' };
  var FIELDS = ['basics', 'semi_ai', 'energy', 'health', 'robotics'];
  var LEVEL_NAMES = { basic: '基礎', mid: '中級', adv: '上級' };
  var LEVELS = ['basic', 'mid', 'adv'];
  var BADGES = [
    ['first', 'はじめの一歩', '初めて回答した'],
    ['streak7', '7日連続', '7日続けて完了した'],
    ['streak30', '30日連続', '30日続けて完了した'],
    ['q100', '100問', '合計100問に回答した']
  ];

  var byId = {};
  QUESTIONS.forEach(function (q) { byId[q.id] = q; });

  function fieldName(f) { return FIELD_NAMES[f] || f; }
  function levelName(l) { return LEVEL_NAMES[l] || l; }
  function chips(q) {
    return h('span', { class: 'chips' },
      h('span', { class: 'chip', text: fieldName(q.field) }),
      h('span', { class: 'chip lv', text: levelName(q.level) }));
  }
  function answerText(q) { return q.type === 'number' ? q.answer + (q.unit || '') : q.answer; }
  function pct(r, t) { return t > 0 ? Math.min(100, Math.max(0, Math.round(r / t * 100))) : 0; }

  // ======================= 不正解 =======================
  var openWrong = {};

  App.Views.wrong = function (root) {
    var date = U.today();
    var rows = App.S.wrongList.filter(function (e) { return byId[e.id]; }).slice()
      .sort(function (a, b) { return a.nextDue < b.nextDue ? -1 : a.nextDue > b.nextDue ? 1 : (a.id < b.id ? -1 : 1); });
    var due = rows.filter(function (e) { return e.nextDue <= date; }).length;

    root.appendChild(h('h2', { class: 'vtitle', text: '不正解リスト' }));
    if (!rows.length) {
      root.appendChild(h('section', { class: 'card placeholder' },
        h('h2', { text: '間違えた問題はありません。' }),
        h('p', { class: 'muted', text: '間違えた問題は、ここに集まります。2回続けて正解すると、リストから卒業します。' })));
      return;
    }
    root.appendChild(h('p', { class: 'summary', id: 'wrong-summary' },
      h('strong', { text: rows.length + '問' }), ' / 今日出題 ', h('strong', { text: due + '問' })));

    var ul = h('ul', { class: 'vlist' });
    rows.forEach(function (e) {
      var q = byId[e.id];
      var isDue = e.nextDue <= date;
      var left = Math.max(1, 2 - (e.okInRow || 0));
      var next = isDue ? '今日から出題' : '次の出題: ' + Number(e.nextDue.slice(5, 7)) + '/' + Number(e.nextDue.slice(8)) + '(' + U.weekday(e.nextDue) + ')';
      var open = !!openWrong[e.id];
      var bodyId = 'wb-' + e.id;
      var li = h('li', { class: 'vitem' + (isDue ? ' due' : '') });
      var head = h('button', { type: 'button', class: 'vhead', 'aria-expanded': open ? 'true' : 'false', 'aria-controls': bodyId },
        h('span', { class: 'vrow' }, chips(q), isDue ? h('span', { class: 'flag', text: '今日' }) : null),
        h('span', { class: 'vq' + (open ? '' : ' clamp2'), text: q.question }),
        h('span', { class: 'vmeta' },
          h('span', { text: '卒業まで あと' + left + '回' }),
          h('span', { class: isDue ? 'due-text' : '', text: next })),
        h('span', { class: 'vhint', 'aria-hidden': 'true', text: open ? '▲ 閉じる' : '▼ 答えを見る' }));
      var body = h('div', { class: 'vbody', id: bodyId, hidden: !open },
        h('p', { class: 'fb-answer' }, '正解: ', h('b', { text: answerText(q) })),
        h('p', { class: 'fb-explain', text: q.explain }),
        q.asof ? U.asofLine(q, q, date) : null);
      head.addEventListener('click', function () {
        openWrong[e.id] = !openWrong[e.id];
        var y = window.scrollY;
        App.render();
        window.scrollTo(0, y);
        var again = document.querySelector('[aria-controls="' + bodyId + '"]');
        if (again) again.focus({ preventScroll: true });
      });
      li.appendChild(head);
      li.appendChild(body);
      ul.appendChild(li);
    });
    root.appendChild(ul);
  };

  // ======================= 成績 =======================
  function barRow(label, r, t, strong) {
    var p = pct(r, t);
    return h('li', { class: 'st-row' },
      h('div', { class: 'st-top' },
        h('span', { class: 'st-label', text: label }),
        h('span', { class: 'st-num', text: t > 0 ? p + '%(' + r + '/' + t + '問)' : 'まだ回答なし' })),
      h('div', { class: 'st-bar' + (strong ? ' strong' : ''), 'aria-hidden': 'true' }, h('i', { style: 'width:' + (t > 0 ? Math.max(p, 2) : 0) + '%' })));
  }

  function setLevel(l) {
    if (App.S.level === l) return;
    App.S = Object.assign({}, App.S, { level: l, recent: [] }); // recent restarts so the level-up suggestion counts from here
    U.persist();
    App.render();
    var b = document.querySelector('.lvbtn[data-level="' + l + '"]');
    if (b) b.focus({ preventScroll: true });
  }

  (function () {
    App.Views.stats = function (root) {
      var S = App.S, date = U.today();
      var total = 0, right = 0;
      var byLevel = {}, byField = {}, cells = [];
      Object.keys(S.stats).forEach(function (f) {
        Object.keys(S.stats[f]).forEach(function (l) {
          var c = S.stats[f][l];
          total += c.total; right += c.right;
          byLevel[l] = byLevel[l] || { r: 0, t: 0 }; byLevel[l].r += c.right; byLevel[l].t += c.total;
          byField[f] = byField[f] || { r: 0, t: 0 }; byField[f].r += c.right; byField[f].t += c.total;
          if (c.total >= 5) cells.push({ f: f, l: l, r: c.right, t: c.total, a: c.right / c.total });
        });
      });

      root.appendChild(h('h2', { class: 'vtitle', text: '成績' }));

      // level-up suggestion
      var sug = QL.suggestLevel(S);
      if (sug) {
        root.appendChild(h('section', { class: 'newbadge', 'aria-label': 'レベルの提案' },
          h('p', { text: '直近20問の正答率が8割を超えました。「' + levelName(sug) + '」に進んでみませんか?' }),
          h('button', { type: 'button', class: 'btn small', id: 'levelup-btn', style: 'margin-top:8px', onclick: function () { setLevel(sug); } }, 'レベルを上げる')));
      }

      // level control
      var seg = h('div', { class: 'seg', role: 'group', 'aria-label': '新しい問題のレベル' });
      LEVELS.forEach(function (l) {
        seg.appendChild(h('button', { type: 'button', class: 'lvbtn', 'data-level': l, 'aria-pressed': S.level === l ? 'true' : 'false', onclick: function () { setLevel(l); } }, levelName(l)));
      });
      root.appendChild(h('section', { class: 'card', 'aria-label': 'いまのレベル' },
        h('h3', { text: 'いまのレベル' }), seg,
        h('p', { class: 'muted', style: 'margin-top:8px', text: 'レベルは「新しい問題のレベル」を決めます。間違えた問題の復習には影響しません。' })));

      if (total === 0) {
        root.appendChild(h('section', { class: 'card placeholder' },
          h('h2', { text: 'まだ成績がありません' }),
          h('p', { class: 'muted', text: '今日の5問を解くと、正答率やバッジがここに出ます。' })));
      } else {
        root.appendChild(h('section', { class: 'card', 'aria-label': '全体の正答率' },
          h('h3', { text: '全体の正答率' }),
          h('p', { class: 'big' }, h('span', { class: 'big-n', text: pct(right, total) + '%' }), h('span', { class: 'muted', text: '(' + right + '/' + total + '問 正解)' })),
          h('div', { class: 'st-bar strong', 'aria-hidden': 'true' }, h('i', { style: 'width:' + Math.max(pct(right, total), 2) + '%' }))));

        var lvl = h('ul', { class: 'st-list' });
        LEVELS.forEach(function (l) { var c = byLevel[l] || { r: 0, t: 0 }; lvl.appendChild(barRow(levelName(l), c.r, c.t)); });
        root.appendChild(h('section', { class: 'card', 'aria-label': 'レベル別' }, h('h3', { text: 'レベル別' }), lvl));

        var fld = h('ul', { class: 'st-list' });
        FIELDS.forEach(function (f) { var c = byField[f] || { r: 0, t: 0 }; fld.appendChild(barRow(fieldName(f), c.r, c.t)); });
        root.appendChild(h('section', { class: 'card', 'aria-label': '分野別' }, h('h3', { text: '分野別' }), fld));

        cells.sort(function (a, b) { return a.a - b.a || b.t - a.t; });
        var weak = cells.slice(0, 3);
        var wk = h('section', { class: 'card', 'aria-label': '苦手ランキング' }, h('h3', { text: '苦手ランキング' }));
        if (weak.length) {
          var ol = h('ol', { class: 'st-list rank' });
          weak.forEach(function (c, i) {
            ol.appendChild(h('li', { class: 'st-row' },
              h('div', { class: 'st-top' },
                h('span', { class: 'st-label', text: (i + 1) + '位 ' + fieldName(c.f) + ' × ' + levelName(c.l) }),
                h('span', { class: 'st-num', text: pct(c.r, c.t) + '%(' + c.r + '/' + c.t + '問)' })),
              h('div', { class: 'st-bar warn', 'aria-hidden': 'true' }, h('i', { style: 'width:' + Math.max(pct(c.r, c.t), 2) + '%' }))));
          });
          wk.appendChild(ol);
          wk.appendChild(h('p', { class: 'muted', text: '5問以上答えた分野×レベルの中で、正答率が低い順です。' }));
        } else {
          wk.appendChild(h('p', { class: 'muted', text: 'まだありません。同じ分野×レベルを5問以上答えると出ます。' }));
        }
        root.appendChild(wk);
      }

      // recent 20
      var rec = S.recent;
      var rcard = h('section', { class: 'card', 'aria-label': '直近20問' }, h('h3', { text: '直近20問' }));
      if (rec.length) {
        var rr = rec.reduce(function (a, b) { return a + b; }, 0);
        rcard.appendChild(h('p', { class: 'big' }, h('span', { class: 'big-n', text: pct(rr, rec.length) + '%' }), h('span', { class: 'muted', text: '(' + rr + '/' + rec.length + '問 正解)' })));
        var strip = h('div', { class: 'recent', 'aria-hidden': 'true' });
        rec.forEach(function (v) { strip.appendChild(h('span', { class: v ? 'ok' : 'ng', text: v ? '○' : '×' })); });
        rcard.appendChild(strip);
      } else {
        rcard.appendChild(h('p', { class: 'muted', text: 'まだありません。' }));
        if (S.stats && Object.keys(S.stats).length) rcard.appendChild(h('p', { class: 'muted', text: 'レベルを変えたので、ここから数え直します。' }));
      }
      root.appendChild(rcard);

      // streak + days
      var days = {};
      S.doneLog.forEach(function (e) { days[e.date] = true; });
      root.appendChild(h('section', { class: 'card two', 'aria-label': '連続と合計' },
        h('div', null, h('p', { class: 'muted', text: '連続日数' }), h('p', { class: 'big-n', text: QL.currentStreak(S, date) + '日' })),
        h('div', null, h('p', { class: 'muted', text: '完了した日' }), h('p', { class: 'big-n', text: Object.keys(days).length + '日' }))));

      // badges
      var have = QL.badgesFor(S).concat(S.badges);
      var bl = h('ul', { class: 'badges' });
      BADGES.forEach(function (b) {
        var got = have.indexOf(b[0]) >= 0;
        bl.appendChild(h('li', { class: 'badge' + (got ? ' got' : '') },
          h('span', { class: 'badge-name', text: (got ? '✓ ' : '') + b[1] }),
          h('span', { class: 'muted', text: got ? '獲得ずみ' : '条件: ' + b[2] })));
      });
      root.appendChild(h('section', { class: 'card', 'aria-label': 'バッジ' }, h('h3', { text: 'バッジ' }), bl));
    };
  })();

  // ======================= 用語帳 =======================
  var wState = { q: '', all: false, open: {} };

  // fold width / case / katakana -> hiragana so 'ＰＥＲ', 'per', 'ペア' and 'ぺあ' all match
  function fold(s) {
    return String(s || '').normalize('NFKC').toLowerCase().replace(/[ァ-ヶ]/g, function (c) {
      return String.fromCharCode(c.charCodeAt(0) - 0x60);
    }).replace(/\s+/g, '');
  }

  function buildTerms() {
    var seen = {};
    App.S.seen.forEach(function (id) { seen[id] = true; });
    var map = {}, order = [];
    QUESTIONS.forEach(function (q) {
      if (!q.term) return;
      var key = fold(q.term);
      var t = map[key];
      if (!t) { t = map[key] = { term: q.term, def: q.termDef || '', fields: [], qs: [], seen: false, key: key }; order.push(t); }
      if (t.fields.indexOf(q.field) < 0) t.fields.push(q.field);
      t.qs.push(q);
      if (seen[q.id]) {
        if (!t.seen) { t.seen = true; t.qs.unshift(t.qs.pop()); } // the first seen question comes first
      }
      // Same term with a different termDef: the first one is kept (data check 2026-10: 0 such pairs in 133 questions).
      if (!t.def && q.termDef) t.def = q.termDef;
    });
    order.forEach(function (t) {
      t.fields.sort(function (a, b) { return FIELDS.indexOf(a) - FIELDS.indexOf(b); });
    });
    return order;
  }

  App.Views.words = function (root) {
    var terms = buildTerms();
    var seenCount = terms.filter(function (t) { return t.seen; }).length;
    var date = U.today();

    root.appendChild(h('h2', { class: 'vtitle', text: '用語帳' }));
    var count = h('p', { class: 'summary', id: 'words-count', 'aria-live': 'polite' });
    var input = h('input', { type: 'search', id: 'words-q', class: 'search', placeholder: '用語をさがす(例: PER)', 'aria-label': '用語をさがす', autocomplete: 'off', enterkeyhint: 'search', value: wState.q || null });
    var toggle = h('input', { type: 'checkbox', id: 'words-all' });
    toggle.checked = wState.all;
    root.appendChild(input);
    root.appendChild(h('label', { class: 'toggle', for: 'words-all' }, toggle, h('span', { text: 'すべての用語' })));
    root.appendChild(count);
    var listBox = h('div', { id: 'words-list' });
    root.appendChild(listBox);

    function paint() {
      var q = fold(wState.q);
      var pool = terms.filter(function (t) { return wState.all || t.seen; });
      var shown = pool.filter(function (t) { return !q || fold(t.term).indexOf(q) >= 0 || fold(t.def).indexOf(q) >= 0; });
      count.textContent = (wState.all ? '全' + terms.length + '用語' : seenCount + ' / 全' + terms.length + '用語') +
        (q ? ' ・ 見つかった用語: ' + shown.length + '件' : '');
      listBox.replaceChildren();
      if (!pool.length) {
        listBox.appendChild(h('section', { class: 'card placeholder' },
          h('h2', { text: 'まだ用語がありません' }),
          h('p', { class: 'muted', text: 'クイズに答えると、出てきた用語がここにたまります。「すべての用語」で全部を見ることもできます。' })));
        return;
      }
      if (!shown.length) {
        listBox.appendChild(h('p', { class: 'muted center', text: '見つかりませんでした。' }));
        return;
      }
      shown.sort(function (a, b) {
        var fa = FIELDS.indexOf(a.fields[0]), fb = FIELDS.indexOf(b.fields[0]);
        return fa - fb || a.term.localeCompare(b.term, 'ja');
      });
      var group = null, ul = null;
      shown.forEach(function (t, i) {
        if (t.fields[0] !== group) {
          group = t.fields[0];
          listBox.appendChild(h('h3', { class: 'ghead', text: fieldName(group) }));
          ul = h('ul', { class: 'vlist' });
          listBox.appendChild(ul);
        }
        var open = !!wState.open[t.key];
        var bodyId = 'wd-' + i;
        var sample = t.qs[0];
        var li = h('li', { class: 'vitem' });
        var head = h('button', { type: 'button', class: 'vhead', 'aria-expanded': open ? 'true' : 'false', 'aria-controls': bodyId },
          h('span', { class: 'vrow' },
            h('b', { class: 'term', text: t.term }),
            h('span', { class: 'chips' }, t.fields.map(function (f) { return h('span', { class: 'chip', text: fieldName(f) }); })),
            !t.seen ? h('span', { class: 'chip unseen', text: '未出題' }) : null),
          h('span', { class: 'vq', text: t.def }),
          h('span', { class: 'vhint', 'aria-hidden': 'true', text: open ? '▲ 閉じる' : '▼ くわしく' }));
        var body = h('div', { class: 'vbody', id: bodyId, hidden: !open },
          h('p', { class: 'fb-explain', text: sample.explain }),
          sample.asof ? U.asofLine(sample, sample, date) : null);
        head.addEventListener('click', function () {
          wState.open[t.key] = !wState.open[t.key];
          var o = wState.open[t.key];
          head.setAttribute('aria-expanded', o ? 'true' : 'false');
          body.hidden = !o;
          head.lastChild.textContent = o ? '▲ 閉じる' : '▼ くわしく';
        });
        li.appendChild(head);
        li.appendChild(body);
        ul.appendChild(li);
      });
    }

    input.addEventListener('input', function () { wState.q = input.value; paint(); });
    toggle.addEventListener('change', function () { wState.all = toggle.checked; paint(); });
    paint();
  };
})();
