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

  var api = {
    jstDate: jstDate,
    daysBetween: daysBetween,
    updateStreak: updateStreak,
    currentStreak: currentStreak,
    addDays: addDays,
    STAGE_DAYS: STAGE_DAYS,
    recordAnswer: recordAnswer,
    dueWrong: dueWrong
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.QuizLogic = Object.assign(root.QuizLogic || {}, api);
})(typeof window !== 'undefined' ? window : globalThis);
