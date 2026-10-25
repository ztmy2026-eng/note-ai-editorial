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
