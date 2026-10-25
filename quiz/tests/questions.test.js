const test = require('node:test');
const assert = require('node:assert');
const { QUESTIONS } = require('../questions.js');

// 後続の分野を足したら、ここに追加する(例: 'semi_ai', 'energy', 'health', 'robotics')
const EXPECTED_FIELDS = ['basics', 'semi_ai', 'energy', 'health', 'robotics'];
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
      // WebFetchできない公式ページは検索結果で確認したので、出典名の末尾に印を付ける
      assert.ok(q.source.name.endsWith('(検索結果で確認)'), 'source.name must end with (検索結果で確認)');
      assert.ok(q.question.includes(q.asof.slice(0, 4)), 'asof year should appear in question text');
    }
  });

  test(`checked/stale: ${q.id}`, () => {
    if (q.checked !== undefined) {
      assert.ok(q.asof !== undefined, 'checked requires asof');
      assert.match(q.checked, /^\d{4}-\d{2}-\d{2}$/);
      assert.ok(!Number.isNaN(Date.parse(q.checked)), 'valid date');
      assert.ok(q.checked <= TODAY, 'checked in the future');
    }
    if (q.stale !== undefined) assert.strictEqual(q.stale, false);
    if (q.asof !== undefined) assert.ok(q.checked !== undefined || q.stale === false, 'real number needs checked or stale:false');
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

test('basics has at least 6 real-number questions spread over levels', () => {
  const r = QUESTIONS.filter((q) => q.field === 'basics' && q.asof);
  assert.ok(r.length >= 6);
  for (const l of LEVELS) assert.ok(r.some((q) => q.level === l), l);
});

test('semi_ai has at least 7 questions per level and half have variants', () => {
  const b = QUESTIONS.filter((q) => q.field === 'semi_ai');
  for (const l of LEVELS) assert.ok(b.filter((q) => q.level === l).length >= 7, l);
  assert.ok(b.filter((q) => q.variants && q.variants.length).length * 2 >= b.length);
});

test('energy has at least 7 questions per level and half have variants', () => {
  const b = QUESTIONS.filter((q) => q.field === 'energy');
  for (const l of LEVELS) assert.ok(b.filter((q) => q.level === l).length >= 7, l);
  assert.ok(b.length >= 21);
  assert.ok(b.filter((q) => q.variants && q.variants.length).length * 2 >= b.length);
});

test('health has at least 7 questions per level and half have variants', () => {
  const b = QUESTIONS.filter((q) => q.field === 'health');
  for (const l of LEVELS) assert.ok(b.filter((q) => q.level === l).length >= 7, l);
  assert.ok(b.length >= 21);
  assert.ok(b.filter((q) => q.variants && q.variants.length).length * 2 >= b.length);
});

test('robotics has at least 7 questions per level and half have variants', () => {
  const b = QUESTIONS.filter((q) => q.field === 'robotics');
  for (const l of LEVELS) assert.ok(b.filter((q) => q.level === l).length >= 7, l);
  assert.ok(b.length >= 21);
  assert.ok(b.filter((q) => q.variants && q.variants.length).length * 2 >= b.length);
});

test('each expected field has at least 4 real-number questions over at least 2 levels', () => {
  for (const f of EXPECTED_FIELDS) {
    const r = QUESTIONS.filter((q) => q.field === f && q.asof);
    assert.ok(r.length >= 4, `${f} has ${r.length} real-number questions`);
    assert.ok(new Set(r.map((q) => q.level)).size >= 2, `${f} real-number levels`);
  }
});

test('whole file: at least 110 questions and every field has at least 7 per level', () => {
  assert.ok(QUESTIONS.length >= 110, `total ${QUESTIONS.length}`);
  for (const f of FIELDS) {
    for (const l of LEVELS) {
      const n = QUESTIONS.filter((q) => q.field === f && q.level === l).length;
      assert.ok(n >= 7, `${f}/${l} has ${n}`);
    }
  }
});

// ---- 選択肢の長さで答えが分からないこと ----
function choiceSets() {
  const sets = [];
  for (const q of QUESTIONS) {
    if (q.type !== 'choice') continue;
    sets.push({ id: q.id, field: q.field, choices: q.choices, answer: q.answer });
    (q.variants || []).forEach((v, i) => {
      if (v.choices) sets.push({ id: `${q.id}#v${i}`, field: q.field, choices: v.choices, answer: v.answer });
    });
  }
  return sets;
}
const LENGTH_ALLOWLIST = []; // 比が本当に取れない場合だけ、ここに id を足す
const meanOf = (a) => a.reduce((x, y) => x + y, 0) / a.length;

test('choice length: keyed answer is within 0.7-1.4x of the mean distractor length', () => {
  for (const s of choiceSets()) {
    if (LENGTH_ALLOWLIST.includes(s.id)) continue;
    const k = s.answer.length;
    const mean = meanOf(s.choices.filter((c) => c !== s.answer).map((c) => c.length));
    if (Math.max(...s.choices.map((c) => c.length)) <= 12) {
      assert.ok(Math.abs(k - mean) <= 6, `${s.id}: short choices differ by ${Math.abs(k - mean).toFixed(1)}`);
    } else {
      const r = k / mean;
      assert.ok(r >= 0.7 && r <= 1.4, `${s.id}: ratio ${r.toFixed(2)}`);
    }
  }
});

test('choice length: per field, keyed answer is the unique longest / shortest in at most 40% of sets', () => {
  for (const f of FIELDS) {
    const ss = choiceSets().filter((s) => s.field === f);
    let longest = 0, shortest = 0;
    for (const s of ss) {
      const k = s.answer.length;
      const all = s.choices.map((c) => c.length);
      if (all.filter((x) => x === k).length !== 1) continue;
      if (k === Math.max(...all)) longest++;
      if (k === Math.min(...all)) shortest++;
    }
    assert.ok(longest / ss.length <= 0.4, `${f}: unique longest ${longest}/${ss.length}`);
    assert.ok(shortest / ss.length <= 0.4, `${f}: unique shortest ${shortest}/${ss.length}`);
  }
});

test('choice wording: keyed answer is not the only hedged choice while distractors use absolutes', () => {
  const HEDGE = /(やすい|にくい|一般に|傾向|とされる|考えられ|おそれ|ことがある|場合がある|ほとんど|限らない|目安)/;
  const ABS = /(必ず|だけ|のみ|保証|まったく|全く|絶対|一切|すべて|全て|ゼロ|永久|常に|いつも|自動的|決まっ)/;
  for (const s of choiceSets()) {
    const ds = s.choices.filter((c) => c !== s.answer);
    const bad = HEDGE.test(s.answer) && !ds.some((d) => HEDGE.test(d)) && ds.some((d) => ABS.test(d));
    assert.ok(!bad, `${s.id}: only the keyed answer is hedged`);
  }
});
