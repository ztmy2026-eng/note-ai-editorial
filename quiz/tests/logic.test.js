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
