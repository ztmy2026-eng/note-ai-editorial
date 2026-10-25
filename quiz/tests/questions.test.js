const test = require('node:test');
const assert = require('node:assert');
const { QUESTIONS } = require('../questions.js');

// 後続の分野を足したら、ここに追加する(例: 'semi_ai', 'energy', 'health', 'robotics')
const EXPECTED_FIELDS = ['basics'];
const LEVELS = ['basic', 'mid', 'adv'];
const FIELDS = ['basics', 'semi_ai', 'energy', 'health', 'robotics'];
const TYPES = ['choice', 'number'];
const TODAY = '2026-10-25';
const DIGIT = /[0-9０-９]/;
const FORBIDDEN = ['買うべき', '売るべき', 'おすすめ銘柄'];
const nonEmpty = (s) => typeof s === 'string' && s.trim().length > 0;

test('ids are unique', () => {
  const ids = QUESTIONS.map((q) => q.id);
  assert.strictEqual(new Set(ids).size, ids.length);
});

for (const q of QUESTIONS) {
  test(`schema: ${q.id}`, () => {
    assert.ok(LEVELS.includes(q.level), 'level');
    assert.ok(FIELDS.includes(q.field), 'field');
    assert.ok(TYPES.includes(q.type), 'type');
    assert.ok(q.id.startsWith(`${q.field}-${q.level}-`), 'id prefix');
    assert.ok(nonEmpty(q.question), 'question');
    assert.ok(nonEmpty(q.explain), 'explain');
    assert.ok(nonEmpty(q.term), 'term');
    assert.ok(nonEmpty(q.termDef), 'termDef');
    if (q.type === 'choice') {
      assert.ok(Array.isArray(q.choices) && q.choices.length === 4, '4 choices');
      assert.ok(q.choices.every(nonEmpty), 'choices non-empty');
      assert.strictEqual(new Set(q.choices).size, 4, 'distinct choices');
      assert.ok(q.choices.includes(q.answer), 'answer in choices');
    } else {
      assert.strictEqual(typeof q.answer, 'number');
      assert.strictEqual(typeof q.tol, 'number');
      assert.ok(q.tol >= 0);
      assert.ok(typeof q.unit === 'string', 'unit');
    }
  });

  test(`asof/source: ${q.id}`, () => {
    assert.strictEqual('asof' in q, 'source' in q, 'asof and source must come together');
    if (q.asof !== undefined) {
      assert.match(q.asof, /^\d{4}-\d{2}-\d{2}$/);
      assert.ok(q.asof <= TODAY, 'asof is in the future');
      assert.ok(q.source && nonEmpty(q.source.name), 'source.name');
      assert.match(q.source.url || '', /^https:\/\/\S+/);
      assert.ok(q.question.includes(q.asof.slice(0, 4)), 'asof year should appear in question text');
    }
  });

  test(`no undated numbers: ${q.id}`, () => {
    // 数字を含む問題は、(例題) と書くか asof を持つ(実在の数字)かのどちらか。
    const hasDigit = DIGIT.test(q.question) || (q.choices || []).some((c) => DIGIT.test(c));
    if (hasDigit && q.asof === undefined) assert.ok(q.question.includes('例題'), 'digits without 例題 or asof');
    for (const v of q.variants || []) {
      const vd = DIGIT.test(v.question) || (v.choices || []).some((c) => DIGIT.test(c));
      if (vd && q.asof === undefined) assert.ok(v.question.includes('例題'), 'variant digits without 例題');
    }
  });

  test(`no advice phrases / variants shape: ${q.id}`, () => {
    for (const w of FORBIDDEN) {
      assert.ok(!q.question.includes(w) && !q.explain.includes(w), w);
    }
    for (const v of q.variants || []) {
      assert.ok(nonEmpty(v.question));
      for (const w of FORBIDDEN) assert.ok(!v.question.includes(w), w);
      if (q.type === 'choice') {
        if (v.choices !== undefined) {
          assert.strictEqual(v.choices.length, 4);
          assert.strictEqual(new Set(v.choices).size, 4);
          assert.ok(v.choices.includes(v.answer), 'variant answer in variant choices');
        } else if (v.answer !== undefined) {
          assert.ok(q.choices.includes(v.answer));
        }
      } else if (v.answer !== undefined) {
        assert.strictEqual(typeof v.answer, 'number');
      }
    }
  });
}

test('coverage: each expected field x level has at least 3 questions', () => {
  for (const f of EXPECTED_FIELDS) {
    for (const l of LEVELS) {
      const n = QUESTIONS.filter((q) => q.field === f && q.level === l).length;
      assert.ok(n >= 3, `${f}/${l} has ${n}`);
    }
  }
});

test('basics has at least 8 questions per level and half have variants', () => {
  const b = QUESTIONS.filter((q) => q.field === 'basics');
  for (const l of LEVELS) assert.ok(b.filter((q) => q.level === l).length >= 8, l);
  assert.ok(b.filter((q) => q.variants && q.variants.length).length * 2 >= b.length);
});
