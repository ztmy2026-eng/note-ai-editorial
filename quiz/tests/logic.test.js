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
