"""
epitranのword_to_tuplesを使って、カタカナとIPA/X-SAMPAの対応関係を取得し、
処理過程を詳細に分析するスクリプト

使い方:
    uv run python check_kana.py                          # デフォルトのサンプル単語で実行
    uv run python check_kana.py -w カタカナ コーヒー      # 指定した単語を分析
    uv run python check_kana.py -w サッカー --detail     # 詳細な処理過程を表示
    uv run python check_kana.py --diff                   # マップとポストプロセッサの差異を分析
"""

import argparse
import epitran
from epitran.xsampa import XSampa


def get_alignment(word: str, epi: epitran.Epitran, xs: XSampa) -> list[dict]:
    """
    カタカナ列に対して、各カタカナ→IPA→X-SAMPAの対応関係を取得する

    Returns:
        list of dict: [{'kana': 'カ', 'ipa': 'ka', 'xsampa': 'ka', 'segments': [...]}]
    """
    result = []

    tuples = epi.word_to_tuples(word)

    for t in tuples:
        # タプルの構造: (category, is_upper, orth, phon, segments)
        category, _is_upper, orth, phon, segments = t

        # IPAをX-SAMPAに変換
        xsampa = xs.ipa2xs(phon) if phon else ""

        # セグメントごとのX-SAMPA
        seg_xsampa = []
        if segments:
            for seg, vector in segments:
                seg_xsampa.append(
                    {
                        "ipa_segment": seg,
                        "xsampa_segment": xs.ipa2xs(seg),
                        "feature_vector": vector,
                    }
                )

        result.append(
            {
                "category": category,  # L=Letter, P=Punctuation, etc.
                "kana": orth,
                "ipa": phon,
                "xsampa": xsampa,
                "segments": seg_xsampa,
            }
        )

    return result


def print_basic_alignment(word: str, epi: epitran.Epitran, xs: XSampa) -> None:
    """
    基本的な対応関係を表示
    """
    alignment = get_alignment(word, epi, xs)

    print(f"\n【{word}】の対応関係")
    print("=" * 70)
    print(f"{'カタカナ':<8} {'IPA':<12} {'X-SAMPA':<12} {'セグメント詳細'}")
    print("-" * 70)

    for item in alignment:
        kana = item["kana"]
        ipa = item["ipa"]
        xsampa = item["xsampa"]
        segments = item["segments"]

        # セグメント詳細
        seg_detail = ""
        if segments:
            seg_strs = [f"{s['ipa_segment']}→{s['xsampa_segment']}" for s in segments]
            seg_detail = ", ".join(seg_strs)

        print(f"{kana:<8} {ipa:<12} {xsampa:<12} {seg_detail}")

    # 全体の変換結果も表示
    full_ipa = epi.transliterate(word)
    full_xsampa = xs.ipa2xs(full_ipa)

    print("-" * 70)
    print(f"全体IPA:     {full_ipa}")
    print(f"全体X-SAMPA: {full_xsampa}")


def print_detail_alignment(word: str, epi: epitran.Epitran, xs: XSampa) -> None:
    """
    詳細な対応関係を表示（タプルの生データ、特徴量ベクトルを含む）
    """
    print(f"\n【{word}】の詳細分析")
    print("=" * 70)

    tuples = epi.word_to_tuples(word)
    print(f"word_to_tuples結果 (タプル数: {len(tuples)})")
    print("-" * 70)

    for i, t in enumerate(tuples):
        category, is_upper, orth, phon, segments = t
        xsampa = xs.ipa2xs(phon) if phon else ""

        print(f"\n[{i}] カタカナ: '{orth}' → IPA: '{phon}' → X-SAMPA: '{xsampa}'")
        print(f"    カテゴリ: {category} (L=Letter, P=Punctuation)")
        print(f"    大文字: {is_upper}")

        if segments:
            print(f"    セグメント ({len(segments)}個):")
            for j, (seg, vector) in enumerate(segments):
                seg_xs = xs.ipa2xs(seg)
                print(f"      [{j}] IPA: '{seg}' → X-SAMPA: '{seg_xs}'")
                print(f"          特徴量ベクトル ({len(vector)}次元): {vector}")
        else:
            print("    セグメント: なし（長音記号など）")

    # 全体の変換結果
    full_ipa = epi.transliterate(word)
    full_xsampa = xs.ipa2xs(full_ipa)
    map_ipa = "".join(t[3] for t in tuples)  # word_to_tuplesのIPAを連結
    map_xsampa = xs.ipa2xs(map_ipa)

    print("\n" + "-" * 70)
    print("【処理結果の比較】")
    print(f"  マップ後IPA（word_to_tuples連結）:     {map_ipa}")
    print(f"  最終IPA（transliterate）:             {full_ipa}")
    print(f"  マップ後X-SAMPA:                      {map_xsampa}")
    print(f"  最終X-SAMPA:                          {full_xsampa}")

    if map_ipa != full_ipa:
        print("\n  ※ ポストプロセッサによる変換が適用されています")


def analyze_diff(word: str, epi: epitran.Epitran) -> None:
    """
    マップ結果とポストプロセッサ適用後の差異を詳細分析
    """
    print(f"\n【{word}】のマップ vs ポストプロセッサ分析")
    print("=" * 70)

    tuples = epi.word_to_tuples(word)

    # マップ後のIPAを連結
    map_ipa = "".join(t[3] for t in tuples)
    # ポストプロセッサ適用後
    final_ipa = epi.transliterate(word)

    print(f"入力カタカナ:       {word}")
    print(f"マップ後IPA:        {map_ipa}")
    print(f"最終IPA:            {final_ipa}")
    print("-" * 70)

    if map_ipa == final_ipa:
        print("→ ポストプロセッサによる変更なし")
    else:
        print("→ ポストプロセッサによる変更あり")
        print()
        print("変更箇所の分析:")

        # 変換パターンの検出
        print("\n推定される変換パターン:")
        detected_patterns = []

        # 促音（ッ）の同化: ʔC → CC
        if "ʔ" in map_ipa and "ʔ" not in final_ipa:
            detected_patterns.append("促音同化: ʔ + 子音 → 子音の重複")

        # 撥音（ン）の同化
        if "ɴ" in map_ipa:
            if "m" in final_ipa or "n" in final_ipa or "ŋ" in final_ipa or "ɲ" in final_ipa:
                if "ɴ" not in final_ipa or map_ipa.count("ɴ") != final_ipa.count("ɴ"):
                    detected_patterns.append("撥音同化: ɴ → m/n/ŋ/ɲ（後続子音に依存）")
            if "ã" in final_ipa or "ĩ" in final_ipa or "ɯ̃" in final_ipa:
                detected_patterns.append("撥音→鼻母音化: ɴ → 鼻母音（母音+継続音の前）")

        # 長音化
        long_vowels = ["aː", "iː", "ɯː", "eː", "oː"]
        for lv in long_vowels:
            if lv in final_ipa and lv not in map_ipa:
                detected_patterns.append(f"長音化: 母音連続 → {lv}")

        # ei → eː, oɯ → oː
        if "eː" in final_ipa and "ei" in map_ipa:
            detected_patterns.append("長音化: ei → eː")
        if "oː" in final_ipa and "oɯ" in map_ipa:
            detected_patterns.append("長音化: oɯ → oː")

        if detected_patterns:
            for pattern in detected_patterns:
                print(f"  - {pattern}")
        else:
            print("  （パターン特定できず）")


def print_raw_tuples(word: str, epi: epitran.Epitran) -> None:
    """
    word_to_tuplesの生の出力を表示
    """
    print(f"\n【{word}】のword_to_tuples生出力")
    print("=" * 70)

    tuples = epi.word_to_tuples(word)
    print(f"タプル数: {len(tuples)}")
    print()

    for i, t in enumerate(tuples):
        print(f"  [{i}] {t}")


def main():
    parser = argparse.ArgumentParser(
        description="epitranを使ってカタカナとIPA/X-SAMPAの対応関係を分析する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  uv run python check_kana.py                          # デフォルトのサンプル単語
  uv run python check_kana.py -w カタカナ コーヒー      # 指定した単語を分析
  uv run python check_kana.py -w サッカー --detail     # 詳細表示
  uv run python check_kana.py --diff                   # マップとポストプロセッサの差異分析
  uv run python check_kana.py --raw                    # 生のタプルデータを表示
        """,
    )

    parser.add_argument(
        "-w",
        "--words",
        nargs="*",
        default=None,
        help="分析するカタカナ単語（スペース区切りで複数指定可能）",
    )

    parser.add_argument(
        "--detail",
        action="store_true",
        help="詳細な処理過程を表示（特徴量ベクトルを含む）",
    )

    parser.add_argument(
        "--diff",
        action="store_true",
        help="マップ結果とポストプロセッサ適用後の差異を分析",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="word_to_tuplesの生のタプルデータを表示",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="すべての分析モードを実行",
    )

    args = parser.parse_args()

    # デフォルトのサンプル単語
    default_words = [
        "カタカナ",
        "コーヒー",
        "サッカー",
        "トウキョウ",
        "ファイル",
        "キョウト",
        "シュミレーション",
        "アンカンサンタンナンハンマンヤンランワンア",
    ]

    words = args.words if args.words else default_words

    # epitranとXSampaのインスタンスを作成
    epi = epitran.Epitran("jpn-Kana")
    xs = XSampa()

    print("=" * 70)
    print("epitran カタカナ → IPA/X-SAMPA 対応関係分析")
    print("=" * 70)

    for word in words:
        if args.all:
            # すべてのモードを実行
            print_raw_tuples(word, epi)
            print_detail_alignment(word, epi, xs)
            analyze_diff(word, epi)
        elif args.raw:
            print_raw_tuples(word, epi)
        elif args.detail:
            print_detail_alignment(word, epi, xs)
        elif args.diff:
            analyze_diff(word, epi)
        else:
            # デフォルト: 基本的な対応関係
            print_basic_alignment(word, epi, xs)

        print()


if __name__ == "__main__":
    main()
