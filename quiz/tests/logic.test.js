const test = require('node:test');
const assert = require('node:assert');
const L = require('../logic.js');

test('jstDate converts to Asia/Tokyo', () => {
  assert.strictEqual(L.jstDate(new Date('2026-10-24T15:00:00Z')), '2026-10-25');
  assert.strictEqual(L.jstDate(new Date('2026-10-24T14:59:59Z')), '2026-10-24');
});

test('daysBetween', () => {
  assert.strictEqual(L.daysBetween('2026-10-24', '2026-10-25'), 1);
  assert.strictEqual(L.daysBetween('2026-10-31', '2026-11-02'), 2);
  assert.strictEqual(L.daysBetween('2026-10-25', '2026-10-25'), 0);
});

test('updateStreak', () => {
  assert.deepStrictEqual(L.updateStreak({}, '2026-10-25'), { streak: 1, lastDoneDate: '2026-10-25' });
  const s = { streak: 3, lastDoneDate: '2026-10-24' };
  assert.strictEqual(L.updateStreak(s, '2026-10-25').streak, 4);
  assert.strictEqual(L.updateStreak({ streak: 4, lastDoneDate: '2026-10-25' }, '2026-10-25').streak, 4);
  const r = L.updateStreak({ streak: 5, lastDoneDate: '2026-10-22' }, '2026-10-25');
  assert.strictEqual(r.streak, 1);
  assert.strictEqual(r.lastDoneDate, '2026-10-25');
  assert.strictEqual(s.streak, 3); // no mutation
});

test('currentStreak', () => {
  assert.strictEqual(L.currentStreak({ streak: 3, lastDoneDate: '2026-10-25' }, '2026-10-25'), 3);
  assert.strictEqual(L.currentStreak({ streak: 3, lastDoneDate: '2026-10-24' }, '2026-10-25'), 3);
  assert.strictEqual(L.currentStreak({ streak: 3, lastDoneDate: '2026-10-23' }, '2026-10-25'), 0);
  assert.strictEqual(L.currentStreak({}, '2026-10-25'), 0);
});

test('addDays', () => {
  assert.strictEqual(L.addDays('2026-10-31', 1), '2026-11-01');
  assert.strictEqual(L.addDays('2026-12-31', 7), '2027-01-07');
});

test('recordAnswer: new wrong answer enters list', () => {
  const s = {};
  const r = L.recordAnswer(s, { id: 'q1' }, false, '2026-10-25');
  assert.deepStrictEqual(r.wrongList, [{ id: 'q1', stage: 0, nextDue: '2026-10-26', okInRow: 0 }]);
  assert.strictEqual(s.wrongList, undefined); // no mutation
});

test('recordAnswer: correct re-answer advances stage, 2 in a row graduates', () => {
  const s0 = { wrongList: [{ id: 'q1', stage: 0, nextDue: '2026-10-26', okInRow: 0 }] };
  const s1 = L.recordAnswer(s0, { id: 'q1' }, true, '2026-10-26');
  assert.deepStrictEqual(s1.wrongList, [{ id: 'q1', stage: 1, nextDue: '2026-10-29', okInRow: 1 }]);
  assert.strictEqual(s0.wrongList[0].okInRow, 0); // no mutation
  const s2 = L.recordAnswer(s1, { id: 'q1' }, true, '2026-10-29');
  assert.deepStrictEqual(s2.wrongList, []);
});

test('recordAnswer: stage stays at 7 days after the end', () => {
  const s = { wrongList: [{ id: 'q1', stage: 2, nextDue: '2026-11-01', okInRow: 0 }] };
  const r = L.recordAnswer(s, { id: 'q1' }, true, '2026-11-01');
  assert.deepStrictEqual(r.wrongList, [{ id: 'q1', stage: 3, nextDue: '2026-11-08', okInRow: 1 }]);
});

test('recordAnswer: wrong again resets okInRow and stage', () => {
  const s = { wrongList: [{ id: 'q1', stage: 1, nextDue: '2026-10-29', okInRow: 1 }] };
  const r = L.recordAnswer(s, { id: 'q1' }, false, '2026-10-29');
  assert.deepStrictEqual(r.wrongList, [{ id: 'q1', stage: 0, nextDue: '2026-10-30', okInRow: 0 }]);
});

test('recordAnswer: correct answer outside list does not add it', () => {
  const r = L.recordAnswer({}, { id: 'q9' }, true, '2026-10-25');
  assert.deepStrictEqual(r.wrongList, []);
});

test('dueWrong: due entries, oldest nextDue first', () => {
  const s = { wrongList: [
    { id: 'a', stage: 0, nextDue: '2026-10-26', okInRow: 0 },
    { id: 'b', stage: 0, nextDue: '2026-10-24', okInRow: 0 },
    { id: 'c', stage: 0, nextDue: '2026-10-27', okInRow: 0 }
  ] };
  assert.deepStrictEqual(L.dueWrong(s, '2026-10-26').map(e => e.id), ['b', 'a']);
  assert.deepStrictEqual(L.dueWrong({}, '2026-10-26'), []);
});

// ---- pickDaily ----
const FIELDS = ['basics', 'semi_ai', 'energy', 'health', 'robotics'];
function mkQ(n) {
  return Array.from({ length: n }, (_, i) => ({
    id: 'q' + i, level: 'basic', field: FIELDS[i % FIELDS.length], type: 'choice',
    question: 'Q' + i, choices: ['a', 'b'], answer: 0, explain: '', term: 't' + i
  }));
}
function seqRng(seed) {
  let x = seed;
  return () => { x = (x * 1103515245 + 12345) % 2147483648; return x / 2147483648; };
}
const dupFree = (arr) => new Set(arr.map(q => q.id)).size === arr.length;

test('pickDaily: returns 5 unique questions', () => {
  const r = L.pickDaily({}, mkQ(30), '2026-10-25', 5, seqRng(1));
  assert.strictEqual(r.length, 5);
  assert.ok(dupFree(r));
});

test('pickDaily: at most 2 due wrong questions even when 5 are due', () => {
  const Q = mkQ(30);
  const wrong = ['q0', 'q1', 'q2', 'q3', 'q4'].map(id => ({ id, stage: 0, nextDue: '2026-10-24', okInRow: 0 }));
  const state = { wrongList: wrong, seen: Q.map(q => q.id).slice(0, 5) };
  const r = L.pickDaily(state, Q, '2026-10-25', 5, seqRng(2));
  const dueIds = wrong.map(w => w.id);
  assert.strictEqual(r.length, 5);
  assert.ok(dupFree(r));
  assert.strictEqual(r.filter(q => dueIds.includes(q.id)).length, 2);
  // oldest-first: the two chosen are the first two due
  assert.ok(r.some(q => q.id === 'q0') && r.some(q => q.id === 'q1'));
});

test('pickDaily: fills to 5 with seen questions when new ones run out', () => {
  const Q = mkQ(10);
  const state = { seen: Q.map(q => q.id).slice(0, 8) };
  const r = L.pickDaily(state, Q, '2026-10-25', 5, seqRng(3));
  assert.strictEqual(r.length, 5);
  assert.ok(dupFree(r));
  assert.ok(r.some(q => q.id === 'q8') && r.some(q => q.id === 'q9'));
});

test('pickDaily: all seen still returns 5', () => {
  const Q = mkQ(10);
  const r = L.pickDaily({ seen: Q.map(q => q.id) }, Q, '2026-10-25', 5, seqRng(3));
  assert.strictEqual(r.length, 5);
  assert.ok(dupFree(r));
});

test('pickDaily: only 3 questions total returns 3 without throwing', () => {
  const r = L.pickDaily({}, mkQ(3), '2026-10-25', 5, seqRng(4));
  assert.strictEqual(r.length, 3);
  assert.ok(dupFree(r));
});

test('pickDaily: fixed rng gives deterministic result', () => {
  const Q = mkQ(30);
  const a = L.pickDaily({}, Q, '2026-10-25', 5, seqRng(7)).map(q => q.id);
  const b = L.pickDaily({}, Q, '2026-10-25', 5, seqRng(7)).map(q => q.id);
  assert.deepStrictEqual(a, b);
});

test('pickDaily: tolerates missing/partial state.stats and wrongList ids not in Q', () => {
  const Q = mkQ(20);
  const state = { stats: { basics: {} , semi_ai: { basic: { right: 1 } } }, wrongList: [{ id: 'zzz', stage: 0, nextDue: '2026-10-01', okInRow: 0 }] };
  const r = L.pickDaily(state, Q, '2026-10-25', 5, seqRng(5));
  assert.strictEqual(r.length, 5);
  assert.ok(dupFree(r));
});

test('pickDaily: prefers basics on one day-parity and sectors on the other', () => {
  const Q = mkQ(100);
  const count = (day) => {
    let basics = 0;
    for (let s = 1; s <= 20; s++) {
      basics += L.pickDaily({}, Q, day, 5, seqRng(s)).filter(q => q.field === 'basics').length;
    }
    return basics;
  };
  const a = count('2026-10-25'), b = count('2026-10-26');
  assert.notStrictEqual(a, b);
  assert.ok(Math.abs(a - b) >= 10);
});

test('pickDaily: weak field (low accuracy) is chosen more often', () => {
  const Q = mkQ(100);
  const state = { stats: { energy: { basic: { right: 0, total: 10 } }, semi_ai: { basic: { right: 10, total: 10 } },
    health: { basic: { right: 10, total: 10 } }, robotics: { basic: { right: 10, total: 10 } } } };
  let en = 0, hl = 0;
  for (let s = 1; s <= 20; s++) {
    const r = L.pickDaily(state, Q, '2026-10-26', 5, seqRng(s));
    en += r.filter(q => q.field === 'energy').length;
    hl += r.filter(q => q.field === 'health').length;
  }
  assert.ok(en > hl);
});

test('pickDaily: does not mutate inputs', () => {
  const Q = mkQ(10); const copy = JSON.stringify(Q);
  const st = { seen: ['q0'] }; const sc = JSON.stringify(st);
  L.pickDaily(st, Q, '2026-10-25', 5, seqRng(1));
  assert.strictEqual(JSON.stringify(Q), copy);
  assert.strictEqual(JSON.stringify(st), sc);
});

const pq = () => ({
  id: 'p1', level: 'basic', field: 'basics', type: 'choice', question: 'PERとは?',
  choices: ['株価収益率', '配当利回り', '自己資本比率', '売上高'], answer: '株価収益率',
  explain: 'e', term: 'PER', asof: '2026-10-01', source: 'http://x',
  variants: [
    { question: '株価を1株益で割った指標は?' },
    { question: 'PERの正式名称に近いのは?', choices: ['A', 'B', 'C', 'D'], answer: 'C' }
  ]
});

test('present: correct answer string matches choices[correctIndex]; display fields copied', () => {
  for (let s = 1; s <= 30; s++) {
    const q = pq();
    const p = L.present(q, false, seqRng(s));
    assert.strictEqual(p.choices[p.correctIndex], '株価収益率');
    assert.strictEqual(p.question, q.question);
    assert.deepStrictEqual([...p.choices].sort(), [...q.choices].sort());
    assert.strictEqual(p.id, 'p1'); assert.strictEqual(p.type, 'choice');
    assert.strictEqual(p.explain, 'e'); assert.strictEqual(p.term, 'PER');
    assert.strictEqual(p.asof, '2026-10-01'); assert.strictEqual(p.source, 'http://x');
  }
});

test('present: different rng gives different arrangement', () => {
  const seen = new Set();
  for (let s = 1; s <= 20; s++) seen.add(L.present(pq(), false, seqRng(s)).choices.join('|'));
  assert.ok(seen.size > 1);
});

test('present: retry with variants changes the question text and still matches answer', () => {
  const texts = new Set();
  for (let s = 1; s <= 30; s++) {
    const q = pq();
    const p = L.present(q, true, seqRng(s));
    assert.notStrictEqual(p.question, q.question);
    texts.add(p.question);
    const expected = p.question === q.variants[1].question ? 'C' : '株価収益率';
    assert.strictEqual(p.choices[p.correctIndex], expected);
  }
  assert.strictEqual(texts.size, 2);
});

test('present: retry moves the correct position away from the original index', () => {
  for (let s = 1; s <= 50; s++) {
    const q = pq();
    const orig = q.choices.indexOf(q.answer);
    const p = L.present(q, true, seqRng(s));
    assert.notStrictEqual(p.correctIndex, orig);
    assert.strictEqual(new Set(p.choices).size, 4);
  }
});

test('present: works without variants (retry and not)', () => {
  const q = pq(); delete q.variants;
  [false, true].forEach(r => {
    const p = L.present(q, r, seqRng(3));
    assert.strictEqual(p.question, q.question);
    assert.strictEqual(p.choices[p.correctIndex], '株価収益率');
  });
});

test('present: non-retry ignores variants', () => {
  assert.strictEqual(L.present(pq(), false, seqRng(4)).question, 'PERとは?');
});

test('present: number type has no choices and passes answer through', () => {
  const q = { id: 'n1', level: 'basic', field: 'basics', type: 'number', question: '1+1?', answer: 2, explain: 'x', term: 't' };
  const p = L.present(q, true, seqRng(1));
  assert.strictEqual(p.choices, null);
  assert.strictEqual(p.correctIndex, -1);
  assert.strictEqual(p.answer, 2);
  assert.strictEqual(p.type, 'number');
});

test('present: does not mutate q', () => {
  const q = pq(); const copy = JSON.stringify(q);
  L.present(q, true, seqRng(1)); L.present(q, false, seqRng(2));
  assert.strictEqual(JSON.stringify(q), copy);
});

test('present: number question uses the variant\'s own answer on retry', () => {
  const q = { id: 'n2', level: 'basic', field: 'basics', type: 'number', question: '10の2割は?', answer: 2, explain: 'x', term: 't',
    variants: [{ question: '50の2割は?', answer: 10 }] };
  const p = L.present(q, true, seqRng(1));
  assert.strictEqual(p.question, '50の2割は?');
  assert.strictEqual(p.answer, 10);
  assert.strictEqual(L.present(q, false, seqRng(1)).answer, 2);
});

test('present: variant whose answer is not in its choices falls back to the original', () => {
  const q = pq();
  q.variants = [{ question: '壊れた言い換え', choices: ['A', 'B', 'C', 'D'], answer: 'Z' }];
  for (let s = 1; s <= 10; s++) {
    const p = L.present(q, true, seqRng(s));
    assert.strictEqual(p.question, q.question);
    assert.strictEqual(p.choices[p.correctIndex], '株価収益率');
  }
});

// ---- Task 5: stats, level suggestion, badges, number answers, staleness ----
test('addStat: creates nested stats, counts right only if correct, returns new state', () => {
  const s0 = {};
  const s1 = L.addStat(s0, { field: 'basics', level: 'basic' }, true);
  const s2 = L.addStat(s1, { field: 'basics', level: 'basic' }, false);
  assert.deepStrictEqual(s2.stats.basics.basic, { right: 1, total: 2 });
  assert.deepStrictEqual(s2.recent, [1, 0]);
  assert.strictEqual(s0.stats, undefined);
  assert.deepStrictEqual(s1.stats.basics.basic, { right: 1, total: 1 });
});

test('addStat: recent keeps only the last 20', () => {
  let s = {};
  for (let i = 0; i < 25; i++) s = L.addStat(s, { field: 'f', level: 'mid' }, i >= 5);
  assert.strictEqual(s.recent.length, 20);
  assert.ok(s.recent.every(x => x === 1));
});

function withRecent(right, total, level) {
  const recent = [];
  for (let i = 0; i < total; i++) recent.push(i < right ? 1 : 0);
  return { recent, level };
}

test('suggestLevel: 17/20 suggests next, 16/20 (exactly 80%) does not', () => {
  assert.strictEqual(L.suggestLevel(withRecent(17, 20)), 'mid');
  assert.strictEqual(L.suggestLevel(withRecent(16, 20)), null);
  assert.strictEqual(L.suggestLevel(withRecent(17, 20, 'mid')), 'adv');
});

test('suggestLevel: null when adv, fewer than 20, or no recent', () => {
  assert.strictEqual(L.suggestLevel(withRecent(20, 20, 'adv')), null);
  assert.strictEqual(L.suggestLevel(withRecent(19, 19)), null);
  assert.strictEqual(L.suggestLevel({}), null);
});

test('badgesFor: first, streak7, streak30, q100; missing keys do not throw', () => {
  assert.deepStrictEqual(L.badgesFor({}), []);
  assert.deepStrictEqual(L.badgesFor({ stats: { a: { basic: { right: 1, total: 1 } } } }), ['first']);
  const b = L.badgesFor({ streak: 7, stats: { a: { basic: { right: 50, total: 60 } }, b: { mid: { right: 30, total: 40 } } } });
  assert.deepStrictEqual(b, ['first', 'streak7', 'q100']);
  assert.ok(L.badgesFor({ streak: 30, stats: {} }).includes('streak30'));
  assert.ok(!L.badgesFor({ streak: 6, stats: {} }).includes('streak7'));
});

test('numberAnswerOk: full-width, commas, units, tolerance, invalid', () => {
  assert.strictEqual(L.numberAnswerOk('１５．２', 15.2, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('15.2倍', 15.2, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('1,234 円', 1234, 0), true);
  assert.strictEqual(L.numberAnswerOk('１，２３４', 1234, 0), true);
  assert.strictEqual(L.numberAnswerOk('3.5％', 3.5, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('－2', -2, 0), true);
  assert.strictEqual(L.numberAnswerOk('15.4', 15.2, 0.1), false);
  assert.strictEqual(L.numberAnswerOk('', 1, 1), false);
  assert.strictEqual(L.numberAnswerOk('abc', 1, 1), false);
});

test('isStale: 90 days not stale, 91 stale, no asof false', () => {
  assert.strictEqual(L.isStale({ asof: '2026-07-27' }, '2026-10-25'), false);
  assert.strictEqual(L.isStale({ asof: '2026-07-26' }, '2026-10-25'), true);
  assert.strictEqual(L.isStale({}, '2026-10-25'), false);
});

test('numberAnswerOk: tolerance edge is inclusive despite float error', () => {
  assert.strictEqual(L.numberAnswerOk('15.3', 15.2, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('1.1', 1, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('15.4', 15.2, 0.1), false);
});

// ---- Task 6: emptyState / loadState / serialize ----
const KEYS = ['streak', 'lastDoneDate', 'doneLog', 'wrongList', 'stats', 'recent', 'seen', 'level', 'badges', 'reports'];

test('emptyState has all keys with defaults', () => {
  const s = L.emptyState();
  assert.deepStrictEqual(Object.keys(s).sort(), KEYS.slice().sort());
  assert.strictEqual(s.streak, 0);
  assert.strictEqual(s.lastDoneDate, null);
  assert.strictEqual(s.level, 'basic');
  assert.deepStrictEqual(s.stats, {});
  assert.deepStrictEqual(s.wrongList, []);
  assert.notStrictEqual(L.emptyState().wrongList, s.wrongList);
});

test('loadState survives null, broken JSON, non-objects, wrong types', () => {
  const empty = L.emptyState();
  assert.deepStrictEqual(L.loadState(null), empty);
  assert.deepStrictEqual(L.loadState(undefined), empty);
  assert.deepStrictEqual(L.loadState('{broken'), empty);
  assert.deepStrictEqual(L.loadState('[]'), empty);
  assert.deepStrictEqual(L.loadState('null'), empty);
  assert.deepStrictEqual(L.loadState('5'), empty);
  assert.deepStrictEqual(L.loadState('{"streak":"x"}'), empty);
  const s = L.loadState('{"streak":3,"level":"zzz","lastDoneDate":"bad","recent":"x"}');
  assert.strictEqual(s.streak, 3);
  assert.strictEqual(s.level, 'basic');
  assert.strictEqual(s.lastDoneDate, null);
  assert.deepStrictEqual(s.recent, []);
  assert.strictEqual(L.loadState('{"streak":-2}').streak, 0);
});

test('loadState sanitizes list fields', () => {
  const raw = JSON.stringify({
    recent: [1, 0, 2, 'a', 1], seen: ['a', 1, null, 'b'], badges: ['x', 3], reports: ['q1', {}],
    doneLog: [{ date: '2026-10-01', time: 't' }, null, { date: 5 }, 7],
    stats: { stock: { basic: { right: 1, total: 2 }, mid: { right: 'x' } }, bad: 5, bad2: { basic: null } }
  });
  const s = L.loadState(raw);
  assert.deepStrictEqual(s.recent, [1, 0, 1]);
  assert.deepStrictEqual(s.seen, ['a', 'b']);
  assert.deepStrictEqual(s.badges, ['x']);
  assert.deepStrictEqual(s.reports, ['q1']);
  assert.strictEqual(s.doneLog.length, 1);
  assert.strictEqual(s.doneLog[0].date, '2026-10-01');
  assert.deepStrictEqual(s.stats.stock, { basic: { right: 1, total: 2 } });
  assert.strictEqual(s.stats.bad, undefined);
  const many = L.loadState(JSON.stringify({ recent: new Array(30).fill(1).map((_, i) => i % 2) }));
  assert.strictEqual(many.recent.length, 20);
});

test('corrupted wrongList is sanitized and logic functions do not throw', () => {
  const raw = JSON.stringify({
    wrongList: [null, 5, 'x', {}, { id: 'a' }, { id: '', nextDue: '2026-10-01' },
      { id: 'b', nextDue: '2026-10-20' },
      { id: 'c', stage: 'x', okInRow: null, nextDue: '2026-10-10' },
      { id: 'd', stage: 2, okInRow: 1, nextDue: 'tomorrow' }]
  });
  const s = L.loadState(raw);
  assert.deepStrictEqual(s.wrongList, [
    { id: 'b', stage: 0, nextDue: '2026-10-20', okInRow: 0 },
    { id: 'c', stage: 0, nextDue: '2026-10-10', okInRow: 0 }
  ]);
  assert.doesNotThrow(() => L.dueWrong(s, '2026-10-25'));
  assert.doesNotThrow(() => L.recordAnswer(s, { id: 'b' }, true, '2026-10-25'));
  assert.doesNotThrow(() => L.recordAnswer(s, { id: 'zz' }, false, '2026-10-25'));
  for (const bad of ['{"wrongList":[null]}', '{"wrongList":{}}', '{"wrongList":[{"id":"a"}]}']) {
    const t = L.loadState(bad);
    assert.deepStrictEqual(t.wrongList, []);
    assert.doesNotThrow(() => L.dueWrong(t, '2026-10-25'));
    assert.doesNotThrow(() => L.recordAnswer(t, { id: 'a' }, false, '2026-10-25'));
  }
});

test('serialize/loadState round trip', () => {
  const s = L.emptyState();
  s.streak = 4; s.lastDoneDate = '2026-10-24'; s.level = 'mid';
  s.doneLog = [{ date: '2026-10-24', time: '07:00' }];
  s.wrongList = [{ id: 'q1', stage: 1, nextDue: '2026-10-27', okInRow: 1 }];
  s.stats = { stock: { basic: { right: 3, total: 5 } } };
  s.recent = [1, 0, 1]; s.seen = ['q1', 'q2']; s.badges = ['b1']; s.reports = ['q9'];
  const str = L.serialize(s);
  assert.strictEqual(typeof str, 'string');
  assert.deepStrictEqual(L.loadState(str), s);
});

test('pickDaily: not-yet-due wrong-list items are not served when other questions exist', () => {
  const Q = mkQ(12);
  const seen = Q.map(q => q.id);
  const wrong = ['q0', 'q1', 'q2'].map(id => ({ id, stage: 0, nextDue: '2026-10-26', okInRow: 0 }));
  for (let seed = 1; seed <= 30; seed++) {
    const r = L.pickDaily({ seen, wrongList: wrong }, Q, '2026-10-25', 5, seqRng(seed));
    assert.strictEqual(r.length, 5);
    assert.ok(dupFree(r));
    assert.ok(!r.some(q => ['q0', 'q1', 'q2'].includes(q.id)), 'not-due wrong item served');
  }
});

test('pickDaily: last resort still returns distinct questions when the pool is tiny', () => {
  const Q = mkQ(5);
  const wrong = Q.map(q => ({ id: q.id, stage: 0, nextDue: '2026-10-26', okInRow: 0 }));
  const r = L.pickDaily({ seen: Q.map(q => q.id), wrongList: wrong }, Q, '2026-10-25', 5, seqRng(9));
  assert.strictEqual(r.length, 5);
  assert.ok(dupFree(r));
});

test('pickDaily: due wrong-list items are still served', () => {
  const Q = mkQ(12);
  const state = { seen: Q.map(q => q.id), wrongList: [{ id: 'q3', stage: 0, nextDue: '2026-10-25', okInRow: 0 }] };
  const r = L.pickDaily(state, Q, '2026-10-25', 5, seqRng(5));
  assert.ok(r.some(q => q.id === 'q3'));
});

test('numberAnswerOk: trailing unit text is stripped', () => {
  assert.strictEqual(L.numberAnswerOk('4033億ドル', 4033, 0), true);
  assert.strictEqual(L.numberAnswerOk('120万円', 120, 0), true);
  assert.strictEqual(L.numberAnswerOk('35.4万台', 35.4, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('３５．４ 万台', 35.4, 0.1), true);
  assert.strictEqual(L.numberAnswerOk('12kg', 12, 0), true);
  assert.strictEqual(L.numberAnswerOk('$12', 12, 0), false);
  assert.strictEqual(L.numberAnswerOk('abc', 1, 1), false);
  assert.strictEqual(L.numberAnswerOk('', 1, 1), false);
  assert.strictEqual(L.numberAnswerOk('1 2', 12, 0), false);
  assert.strictEqual(L.numberAnswerOk('1,2,3x4', 1234, 0), false);
  assert.strictEqual(L.numberAnswerOk('約12', 12, 0), false);
  assert.strictEqual(L.numberAnswerOk('4033億ドル', 4000, 0), false);
});

test('isStale: checked date and stale:false', () => {
  assert.strictEqual(L.isStale({ asof: '2025-01-01', checked: '2026-10-25' }, '2026-10-25'), false);
  assert.strictEqual(L.isStale({ asof: '2026-10-01', checked: '2026-07-26' }, '2026-10-25'), true);
  assert.strictEqual(L.isStale({ asof: '2026-10-01', checked: '2026-07-27' }, '2026-10-25'), false);
  assert.strictEqual(L.isStale({ asof: '2020-01-01', stale: false }, '2026-10-25'), false);
});
