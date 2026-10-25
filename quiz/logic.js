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

  var api = {
    jstDate: jstDate,
    daysBetween: daysBetween,
    updateStreak: updateStreak,
    currentStreak: currentStreak
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.QuizLogic = Object.assign(root.QuizLogic || {}, api);
})(typeof window !== 'undefined' ? window : globalThis);
