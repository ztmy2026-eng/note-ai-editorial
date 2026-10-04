"""コマンド入口。  使い方: python -m note_editorial <コマンド> --help"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import analytics, artifacts, articles, auto, chief, collect, export, figures, images, learn, limits, runs, weekly


def _cmd_check_articles(args) -> int:
    root = Path(args.root)
    result, source = articles.load_with_fallback(root)
    s = articles.summarize(result.articles)
    label = "サンプル(架空)データ" if source == "samples" else "data/past_articles"
    print(f"読み込み元: {label}")
    print(f"記事数: {s['count']}(数値あり {s['with_metrics']} / 数値なし {s['without_metrics']})")
    print(f"テーマ別: {s['by_theme']}")
    for p in result.problems:
        print(f"[問題] {p}")
    return 1 if result.problems else 0


def _cmd_themes(args) -> int:
    for t in sorted(runs.load_themes(Path(args.root)), key=lambda t: t.get("priority", 99)):
        mark = "有効" if t.get("active", True) else "無効"
        print(f"{t['priority']}. {t['id']:<10} {t['name']} [{mark}]")
    return 0


def _cmd_new_run(args) -> int:
    root = Path(args.root)
    if args.plan:
        found = weekly.item_for(root, limits.today_local(root))
        if not found:
            raise runs.RunError("今日の週次企画がありません(plans/<週の月曜>/plan.yaml)。`next-theme` で選んで `new-run --theme` を使ってください")
        data, it = found
        run_id = runs.create_run(root, it["theme"])
        weekly.attach_to_run(root, run_id, data, it)
        print(run_id)
        return 0
    if not args.theme:
        raise runs.RunError("--theme か --plan のどちらかを指定してください")
    print(runs.create_run(root, args.theme))
    return 0


def _cmd_today_plan(args) -> int:
    root = Path(args.root)
    found = weekly.item_for(root, limits.today_local(root))
    if not found:
        print("今日の週次企画はありません(従来どおり next-theme でテーマを選ぶ)")
        return 1
    print(weekly.render_item(*found), end="")
    return 0


def _cmd_check_plan(args) -> int:
    from datetime import date as _date
    root = Path(args.root)
    start = _date.fromisoformat(args.week) if args.week else weekly.week_start(limits.today_local(root))
    problems = weekly.validate_plan(root, start)
    for pr in problems:
        print(f"  - {pr}")
    print(f"週次企画 {start.isoformat()}: " + ("合格" if not problems else "不合格"))
    return 1 if problems else 0


def _cmd_make_figures(args) -> int:
    try:
        made = figures.make_figures(Path(args.root), args.run_id)
    except figures.FigureError as e:
        print(f"[エラー] {e}", file=sys.stderr)
        return 2
    for p in made:
        print(p)
    print(f"{len(made)}枚作りました。Readで1枚ずつ目視し、文字の重なり・はみ出し・表の崩れがあれば figures.json を直して作り直してください")
    return 0


def _cmd_complete(args) -> int:
    problems = runs.complete_step(Path(args.root), args.run_id, args.step)
    if problems:
        print(f"[不合格] {args.step}:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"[合格] {args.step} を完了として記録しました")
    return 0


def _cmd_validate(args) -> int:
    rdir = runs.run_path(Path(args.root), args.run_id)
    problems = artifacts.validate(args.step, rdir / artifacts.FILES[args.step], rdir)
    for p in problems:
        print(f"  - {p}")
    print("合格" if not problems else "不合格")
    return 1 if problems else 0


def _cmd_approve_idea(args) -> int:
    runs.approve_idea(Path(args.root), args.run_id, args.number)
    print(f"【承認1】候補{args.number}を採用しました")
    return 0


def _cmd_approve_publish(args) -> int:
    ready = runs.approve_publish(Path(args.root), args.run_id)
    print(f"【承認2】公開準備完了: {ready}\n※ noteへの投稿はあなたが手動で行います(このシステムは送信しません)")
    return 0


def _cmd_approve_sns(args) -> int:
    runs.approve_sns(Path(args.root), args.run_id)
    print("【承認3】SNS投稿案を承認しました\n※ 投稿はあなたが手動で行います(このシステムは送信しません)")
    return 0


def _cmd_analyze(args) -> int:
    root = Path(args.root)
    result, source = articles.load_with_fallback(root)
    for p in result.problems:
        print(f"[問題] {p}")
    out = root / "analytics" / "facts.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text(analytics.render_facts(analytics.compute_facts(result.articles)), encoding="utf-8")
    print(f"集計を書き出しました: {out}(読み込み元: {source})")
    return 0


def _cmd_validate_hypotheses(args) -> int:
    problems = analytics.validate_hypotheses(Path(args.root) / "analytics" / "hypotheses.md")
    for p in problems:
        print(f"  - {p}")
    print("合格" if not problems else "不合格")
    return 1 if problems else 0


def _cmd_briefing(args) -> int:
    path = chief.write_briefing(Path(args.root))
    print(path.read_text(encoding="utf-8"))
    return 0


def _cmd_export_note(args) -> int:
    out = export.export_note(Path(args.root), args.run_id)
    print(f"note貼り付け用を作りました: {out}/title.txt(タイトル欄) と {out}/body.md(本文欄)")
    return 0


def _cmd_make_images(args) -> int:
    try:
        made = images.make_images(Path(args.root), args.run_id)
    except images.ImageError as e:
        print(f"[エラー] {e}", file=sys.stderr)
        return 2
    for p in made:
        print(p)
    print(f"{len(made)}枚作りました(文字入りカード。内容を確認してから使ってください)")
    return 0


def _cmd_check_limits(args) -> int:
    root = Path(args.root)
    for key, (used, cap) in limits.usage(root).items():
        print(f"{limits.LABELS[key]}: {used} / {cap}")
    reasons = limits.reached(root, new_run=args.new_run)
    for r in reasons:
        print(f"[停止] {r}")
    print("上限に達しています。新しい作業は始めません" if reasons else "OK(まだ作業できます)")
    return 1 if reasons else 0


def _cmd_auto_approve(args) -> int:
    results = auto.auto_approve(Path(args.root), args.run_id)
    for r in results or ["自動で進める承認はありませんでした"]:
        print(r)
    return 1 if any(r.startswith("停止") for r in results) else 0


def _cmd_mark_posted(args) -> int:
    url = export.clean_url(args.url) if args.url else ""
    runs.mark_posted(Path(args.root), args.run_id, url)
    print("投稿済みとして記録しました(次の記事を作れるようになります)")
    if url:
        ready = export.fill_article_url(Path(args.root), args.run_id, url)
        if ready:
            print(f"URL入りのSNS案を作りました: {ready}")
    if (Path(args.root) / "runs" / args.run_id / "note_post" / "title.txt").exists():
        print(f"あなたのデータとして登録しました: {learn.add_posted_article(Path(args.root), args.run_id)}(数値は空。record-metrics で追記)")
    return 0


def _cmd_export_metrics(args) -> int:
    import json
    text = json.dumps(learn.export_metrics(Path(args.root)), ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"書き出しました: {args.out}")
    else:
        print(text)
    return 0


def _cmd_import_metrics(args) -> int:
    import json
    try:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise runs.RunError(f"読み込めません: {e}") from e
    rows = data["articles"] if isinstance(data, dict) else data
    for line in learn.import_metrics(Path(args.root), rows) or ["取り込む手入力の変更はありませんでした"]:
        print(line)
    return 0


def _cmd_mark_skipped(args) -> int:
    runs.mark_skipped(Path(args.root), args.run_id, args.reason)
    print("見送りとして記録しました(未投稿の在庫から外れます)")
    return 0


def _cmd_collect_metrics(args) -> int:
    for line in collect.collect(Path(args.root), Path(args.file)):
        print(line)
    return 0


def _cmd_record_metrics(args) -> int:
    path = learn.record_metrics(Path(args.root), args.run_id, impressions=args.impressions, pv=args.pv, likes=args.likes,
                                revenue=args.revenue, followers_gained=args.followers)
    print(f"数値を記録しました: {path}")
    return 0


def _cmd_next_theme(args) -> int:
    print(chief.next_theme(Path(args.root)))
    return 0


def _cmd_reopen(args) -> int:
    dest = runs.reopen(Path(args.root), args.run_id, args.step)
    print(f"{args.step} 以降をやり直します。古い成果物は {dest} に退避しました")
    return 0


def _cmd_status(args) -> int:
    root = Path(args.root)
    ids = [args.run_id] if args.run_id else sorted(p.parent.name for p in (root / "runs").glob("*/run.json"))
    for rid in ids:
        d = runs.read_run(root, rid)
        print(f"{rid} [{d['theme_name']}] 状態={d['status']} 完了={','.join(d['steps_done']) or '-'}"
              f" 承認1={'済' if d['approvals']['idea'] else '未'} 承認2={'済' if d['approvals']['publish'] else '未'}"
              f" 承認3={'済' if d['approvals'].get('sns') else '未'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="note_editorial", description="note AI編集部")
    p.add_argument("--root", default=".", help="プロジェクトのフォルダ(通常は変更不要)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-articles", help="過去記事を読み込んで集計").set_defaults(fn=_cmd_check_articles)
    sub.add_parser("themes", help="テーマ一覧").set_defaults(fn=_cmd_themes)
    s = sub.add_parser("new-run", help="新しい実行を作る")
    s.add_argument("--theme", default="")
    s.add_argument("--plan", action="store_true", help="今日の週次企画(plans/)を使って実行を作る")
    s.set_defaults(fn=_cmd_new_run)
    for name, fn, h in (("complete", _cmd_complete, "成果物を検査して完了を記録"), ("validate", _cmd_validate, "検査のみ(記録しない)")):
        s = sub.add_parser(name, help=h)
        s.add_argument("run_id")
        s.add_argument("step", choices=artifacts.STEPS)
        s.set_defaults(fn=fn)
    s = sub.add_parser("approve-idea", help="【承認1】企画を採用")
    s.add_argument("run_id")
    s.add_argument("number", type=int)
    s.set_defaults(fn=_cmd_approve_idea)
    s = sub.add_parser("approve-publish", help="【承認2】公開してよいと承認")
    s.add_argument("run_id")
    s.set_defaults(fn=_cmd_approve_publish)
    s = sub.add_parser("approve-sns", help="【承認3】SNS投稿案を承認")
    s.add_argument("run_id")
    s.set_defaults(fn=_cmd_approve_sns)
    sub.add_parser("analyze", help="過去記事を集計(分析の事実部分)").set_defaults(fn=_cmd_analyze)
    sub.add_parser("validate-hypotheses", help="仮説台帳の形式検査").set_defaults(fn=_cmd_validate_hypotheses)
    sub.add_parser("briefing", help="編集長の朝のブリーフィングを作る").set_defaults(fn=_cmd_briefing)
    for name, fn, h in (("export-note", _cmd_export_note, "note貼り付け用のタイトル・本文を作る(承認2の後)"),
                        ("make-images", _cmd_make_images, "note見出し画像とInstagram画像を自動作成")):
        s = sub.add_parser(name, help=h)
        s.add_argument("run_id")
        s.set_defaults(fn=fn)
    s = sub.add_parser("check-limits", help="1日の上限の使用状況(上限に達していれば終了コード1)")
    s.add_argument("--new-run", action="store_true", help="新しい実行を作る前の確認(実行数・在庫の上限も見る)。付けない場合は、作業中の実行の続きの確認(Agent作業数だけ見る)")
    s.set_defaults(fn=_cmd_check_limits)
    s = sub.add_parser("auto-approve", help="承認なしモード:承認1〜3を自動で通す(検品は人間の承認と同じ条件)")
    s.add_argument("run_id")
    s.set_defaults(fn=_cmd_auto_approve)
    s = sub.add_parser("mark-posted", help="noteに投稿したことを記録")
    s.add_argument("run_id")
    s.add_argument("--url", default="", help="公開した記事のURL")
    s.set_defaults(fn=_cmd_mark_posted)
    s = sub.add_parser("export-metrics", help="ダッシュボード用に数値を書き出す(JSON)")
    s.add_argument("--out", default="")
    s.set_defaults(fn=_cmd_export_metrics)
    s = sub.add_parser("import-metrics", help="ダッシュボードで直した数字(手入力)を取り込む")
    s.add_argument("file")
    s.set_defaults(fn=_cmd_import_metrics)
    s = sub.add_parser("mark-skipped", help="この記事は投稿しない、と記録")
    s.add_argument("run_id")
    s.add_argument("--reason", default="")
    s.set_defaults(fn=_cmd_mark_skipped)
    s = sub.add_parser("collect-metrics", help="通知メールから集めたデータ(JSON)を集計して記録")
    s.add_argument("file")
    s.set_defaults(fn=_cmd_collect_metrics)
    s = sub.add_parser("record-metrics", help="投稿した記事の反応の数値を記録(手入力・メール収集の共通の入口)")
    s.add_argument("run_id")
    for opt in ("impressions", "pv", "likes", "revenue", "followers"):
        s.add_argument(f"--{opt}", type=int, default=None)
    s.set_defaults(fn=_cmd_record_metrics)
    sub.add_parser("next-theme", help="次に記事を作るテーマを選ぶ").set_defaults(fn=_cmd_next_theme)
    sub.add_parser("today-plan", help="今日の週次企画を表示(無ければ終了コード1)").set_defaults(fn=_cmd_today_plan)
    s = sub.add_parser("check-plan", help="週次企画(plans/<週の月曜>/plan.yaml)の形式検査")
    s.add_argument("--week", default="", help="週の開始日(月曜, YYYY-MM-DD)。省略時は今週")
    s.set_defaults(fn=_cmd_check_plan)
    s = sub.add_parser("make-figures", help="runs/<ID>/figures.json から本文の図・見出し画像を作る(週次方針の仕様)")
    s.add_argument("run_id")
    s.set_defaults(fn=_cmd_make_figures)
    s = sub.add_parser("reopen", help="draft/critique/revised 以降をやり直す(古い版は退避)")
    s.add_argument("run_id")
    s.add_argument("step", choices=["draft", "critique", "revised", "sns"])
    s.set_defaults(fn=_cmd_reopen)
    s = sub.add_parser("status", help="実行の状態")
    s.add_argument("run_id", nargs="?")
    s.set_defaults(fn=_cmd_status)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except runs.RunError as e:
        print(f"[エラー] {e}", file=sys.stderr)
        return 2
