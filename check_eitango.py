"""
英単語からARPABET列を取得し、それをIPA/X-SAMPAに変換する処理を分析するスクリプト

処理の流れ:
1. 英単語 → ARPABET (CMUdict辞書 または lex_lookupコマンド)
2. ARPABET → IPA (epitran FliteLexLookup.arpa_map)
3. IPA → X-SAMPA (epitran XSampa.ipa2xs)

使い方:
    uv run python check_eitango.py                          # デフォルトのサンプル単語で実行
    uv run python check_eitango.py -w hello world           # 指定した単語を分析
    uv run python check_eitango.py -w beautiful --detail    # 詳細な処理過程を表示
    uv run python check_eitango.py --arpabet-map            # ARPABETマッピング表を表示
    uv run python check_eitango.py --raw                    # 生のARPABETデータを表示
    uv run python check_eitango.py --use-flite              # lex_lookupを使用（Fliteインストール必須）
"""

import argparse
import re
import subprocess
import unicodedata
from typing import Optional

import cmudict
from epitran.flite import FliteLexLookup
from epitran.xsampa import XSampa
import panphon

# CMUdictを読み込み
CMUDICT = cmudict.dict()

# epitranのFliteLexLookupインスタンス（ARPABET→IPA変換用）
FLITE = FliteLexLookup()

# panphonのFeatureTable（特徴量ベクトル取得用）
FT = panphon.FeatureTable()


def remove_stress(arpa: str) -> str:
    """
    ARPABET音素からストレス情報（0, 1, 2）を除去する

    Args:
        arpa: 'AH0', 'OW1', 'AE2' など

    Returns:
        'AH', 'OW', 'AE' など
    """
    return re.sub(r"[012]$", "", arpa)


def get_arpabet_from_cmudict(word: str) -> Optional[tuple[list[str], list[list[str]]]]:
    """
    CMUdictから英単語のARPABET列を取得する

    Returns:
        tuple: (最初の発音のARPABETリスト, すべての発音バリエーション)
        None: 単語が見つからない場合
    """
    word_lower = word.lower()
    if word_lower in CMUDICT:
        pronunciations = CMUDICT[word_lower]
        return pronunciations[0], pronunciations
    return None


def get_arpabet_from_flite(word: str) -> Optional[list[str]]:
    """
    lex_lookupコマンドを直接呼び出してARPABET列を取得する

    Returns:
        list[str]: ARPABETのリスト (例: ["HH", "AX", "L", "OW"])
        None: エラー時
    """
    try:
        # lex_lookupは小文字を期待
        word_normalized = unicodedata.normalize("NFD", word)
        word_normalized = "".join(filter(lambda x: x.isascii(), word_normalized))
        word_lower = word_normalized.lower()

        result = subprocess.check_output(["lex_lookup", word_lower])
        arpa_text = result.decode("utf-8").strip()
        # 複数行の場合は最初の行を取得
        lines = arpa_text.splitlines()
        if not lines:
            return None

        arpa_raw = lines[0]
        # 括弧を除去してスペースで分割、大文字に変換
        if arpa_raw.startswith("(") and arpa_raw.endswith(")"):
            arpa_raw = arpa_raw[1:-1]
        return [p.upper() for p in arpa_raw.split()]
    except FileNotFoundError:
        return None
    except subprocess.CalledProcessError:
        return None


def get_alignment(word: str, xs: XSampa, use_flite: bool = False) -> list[dict]:
    """
    英単語に対して、各ARPABET音素→IPA→X-SAMPAの対応関係を取得する

    Returns:
        list of dict: [{'arpabet': 'HH', 'arpabet_clean': 'hh', 'ipa': 'h', 'xsampa': 'h', 'segments': [...]}]
        または [{'error': 'エラーメッセージ'}] の場合
    """
    arpa_list = None
    all_pronunciations = None
    source = None

    if use_flite:
        arpa_list = get_arpabet_from_flite(word)
        if arpa_list is not None:
            source = "flite"
        else:
            return [
                {
                    "error": "lex_lookupが使用できません（Fliteをインストールしてください）"
                }
            ]
    else:
        result = get_arpabet_from_cmudict(word)
        if result is not None:
            arpa_list, all_pronunciations = result
            source = "cmudict"
        else:
            # CMUdictにない場合、Fliteを試す
            arpa_list = get_arpabet_from_flite(word)
            if arpa_list is not None:
                source = "flite"
            else:
                return [
                    {
                        "error": f"'{word}'はCMUdictに存在せず、lex_lookupも使用できません"
                    }
                ]

    result_list = []

    for arpa in arpa_list:
        # ストレス情報を除去して小文字に変換（arpa_mapのキー形式）
        arpa_clean = remove_stress(arpa).lower()

        # epitranのarpa_mapを使ってIPAを取得
        ipa = FLITE.arpa_map.get(arpa_clean, "")

        # epitranのXSampaを使ってX-SAMPAに変換
        xsampa = xs.ipa2xs(ipa) if ipa else ""

        # セグメントごとのX-SAMPAと特徴量ベクトル
        seg_info = []
        if ipa:
            # word_ftsでSegmentオブジェクトを取得（.numeric()で数値ベクトル取得可能）
            seg_objs = FT.word_fts(ipa)
            ipa_segs = FT.ipa_segs(ipa)
            if seg_objs and ipa_segs:
                for seg_str, seg_obj in zip(ipa_segs, seg_objs):
                    seg_xsampa = xs.ipa2xs(seg_str)
                    # Segment.numeric()で数値形式のベクトルを取得
                    vec = seg_obj.numeric()
                    seg_info.append(
                        {
                            "ipa_segment": seg_str,
                            "xsampa_segment": seg_xsampa,
                            "feature_vector": vec,
                        }
                    )

        result_list.append(
            {
                "arpabet": arpa,  # 元のARPABET（ストレス付き）
                "arpabet_clean": arpa_clean,  # ストレス除去後（小文字）
                "ipa": ipa,
                "xsampa": xsampa,
                "segments": seg_info,
            }
        )

    # メタ情報を最初の要素に追加
    if result_list:
        result_list[0]["_meta"] = {
            "word": word,
            "source": source,
            "all_pronunciations": all_pronunciations,
        }

    return result_list


def print_basic_alignment(word: str, xs: XSampa, use_flite: bool = False) -> None:
    """
    基本的な対応関係を表示（check_kana.pyと同様の表形式）
    """
    alignment = get_alignment(word, xs, use_flite)

    if alignment and "error" in alignment[0]:
        print(f"\n【{word}】: {alignment[0]['error']}")
        return

    # メタ情報を取得
    meta = alignment[0].get("_meta", {})
    source = meta.get("source", "unknown")
    all_pronunciations = meta.get("all_pronunciations")

    print(f"\n【{word}】の対応関係")
    print("=" * 70)
    print(f"データソース: {source}")

    # 複数の発音バリエーションがある場合
    if all_pronunciations and len(all_pronunciations) > 1:
        print(f"発音バリエーション数: {len(all_pronunciations)}")

    print(
        f"{'ARPABET':<10} {'(clean)':<8} {'IPA':<12} {'X-SAMPA':<12} {'セグメント詳細'}"
    )
    print("-" * 70)

    for item in alignment:
        arpa = item["arpabet"]
        arpa_clean = item["arpabet_clean"]
        ipa = item["ipa"]
        xsampa = item["xsampa"]
        segments = item["segments"]

        # セグメント詳細
        seg_detail = ""
        if segments:
            seg_strs = [f"{s['ipa_segment']}→{s['xsampa_segment']}" for s in segments]
            seg_detail = ", ".join(seg_strs)

        print(f"{arpa:<10} {arpa_clean:<8} {ipa:<12} {xsampa:<12} {seg_detail}")

    # 全体の変換結果も表示
    arpa_list_for_epitran = (
        "(" + " ".join([item["arpabet_clean"] for item in alignment]) + ")"
    )
    full_ipa = FLITE.arpa_to_ipa(arpa_list_for_epitran)
    full_xsampa = xs.ipa2xs(full_ipa)

    print("-" * 70)
    print(f"全体ARPABET:  {' '.join([item['arpabet'] for item in alignment])}")
    print(f"全体IPA:      {full_ipa}")
    print(f"全体X-SAMPA:  {full_xsampa}")


def print_detail_alignment(word: str, xs: XSampa, use_flite: bool = False) -> None:
    """
    詳細な対応関係を表示（タプルの生データ、特徴量ベクトルを含む）
    """
    alignment = get_alignment(word, xs, use_flite)

    if alignment and "error" in alignment[0]:
        print(f"\n【{word}】: {alignment[0]['error']}")
        return

    # メタ情報を取得
    meta = alignment[0].get("_meta", {})
    source = meta.get("source", "unknown")
    all_pronunciations = meta.get("all_pronunciations")

    print(f"\n【{word}】の詳細分析")
    print("=" * 70)
    print(f"データソース: {source}")
    print(f"ARPABET音素数: {len(alignment)}")

    # 複数の発音バリエーションがある場合
    if all_pronunciations and len(all_pronunciations) > 1:
        print(f"\n発音バリエーション ({len(all_pronunciations)}種):")
        for i, pron in enumerate(all_pronunciations):
            print(f"  [{i}] {' '.join(pron)}")

    print("-" * 70)

    for i, item in enumerate(alignment):
        arpa = item["arpabet"]
        arpa_clean = item["arpabet_clean"]
        ipa = item["ipa"]
        xsampa = item["xsampa"]
        segments = item["segments"]

        print(
            f"\n[{i}] ARPABET: '{arpa}' (clean: '{arpa_clean}') → IPA: '{ipa}' → X-SAMPA: '{xsampa}'"
        )

        if segments:
            print(f"    セグメント ({len(segments)}個):")
            for j, seg in enumerate(segments):
                seg_ipa = seg["ipa_segment"]
                seg_xs = seg["xsampa_segment"]
                vec = seg["feature_vector"]
                print(f"      [{j}] IPA: '{seg_ipa}' → X-SAMPA: '{seg_xs}'")
                if vec:
                    print(f"          特徴量ベクトル ({len(vec)}次元): {vec}")
        else:
            print("    セグメント: なし")

    # 全体の変換結果
    arpa_list_for_epitran = (
        "(" + " ".join([item["arpabet_clean"] for item in alignment]) + ")"
    )
    full_ipa = FLITE.arpa_to_ipa(arpa_list_for_epitran)
    full_xsampa = xs.ipa2xs(full_ipa)
    map_ipa = "".join([item["ipa"] for item in alignment])
    map_xsampa = "".join([item["xsampa"] for item in alignment])

    print("\n" + "-" * 70)
    print("【処理結果の比較】")
    print(f"  マップ後IPA（arpa_map連結）:           {map_ipa}")
    print(f"  最終IPA（arpa_to_ipa）:               {full_ipa}")
    print(f"  マップ後X-SAMPA:                      {map_xsampa}")
    print(f"  最終X-SAMPA:                          {full_xsampa}")

    if map_ipa != full_ipa:
        print("\n  ※ arpa_to_ipaによる追加処理が適用されています")


def print_raw_data(word: str, use_flite: bool = False) -> None:
    """
    生のARPABETデータを表示（check_kana.pyのprint_raw_tuplesに相当）
    """
    print(f"\n【{word}】の生データ")
    print("=" * 70)

    # ARPABETを取得
    if use_flite:
        arpa_list = get_arpabet_from_flite(word)
        source = "flite"
    else:
        result = get_arpabet_from_cmudict(word)
        if result is not None:
            arpa_list, _ = result
            source = "cmudict"
        else:
            arpa_list = get_arpabet_from_flite(word)
            source = "flite" if arpa_list else None

    if arpa_list is None:
        print(f"エラー: '{word}'のARPABET取得に失敗")
        return

    print(f"データソース: {source}")
    print(f"ARPABET音素数: {len(arpa_list)}")
    print()

    print("【CMUdictの生出力】")
    if source == "cmudict":
        word_lower = word.lower()
        raw_pronunciations = CMUDICT.get(word_lower, [])
        for i, pron in enumerate(raw_pronunciations):
            print(f"  [{i}] {pron}")
    else:
        print("  (CMUdictに存在しません)")

    print()
    print("【epitran arpa_map 参照】")
    for i, arpa in enumerate(arpa_list):
        arpa_clean = remove_stress(arpa).lower()
        ipa = FLITE.arpa_map.get(arpa_clean, "(未定義)")
        print(f"  [{i}] '{arpa}' → clean: '{arpa_clean}' → arpa_map: '{ipa}'")


def analyze_diff(word: str, use_flite: bool = False) -> None:
    """
    arpa_mapによる個別マッピングとarpa_to_ipaの差異を詳細分析
    （check_kana.pyのanalyze_diffに相当）
    """
    print(f"\n【{word}】のマップ vs arpa_to_ipa分析")
    print("=" * 70)

    # ARPABETを取得
    if use_flite:
        arpa_list = get_arpabet_from_flite(word)
        source = "flite"
    else:
        result = get_arpabet_from_cmudict(word)
        if result is not None:
            arpa_list, _ = result
            source = "cmudict"
        else:
            arpa_list = get_arpabet_from_flite(word)
            source = "flite" if arpa_list else None

    if arpa_list is None:
        print(f"エラー: '{word}'のARPABET取得に失敗")
        return

    # arpa_mapで個別に変換したIPAを連結
    map_ipa_parts = []
    for arpa in arpa_list:
        arpa_clean = remove_stress(arpa).lower()
        ipa = FLITE.arpa_map.get(arpa_clean, "")
        map_ipa_parts.append(ipa)
    map_ipa = "".join(map_ipa_parts)

    # arpa_to_ipaで変換
    arpa_list_for_epitran = (
        "(" + " ".join([remove_stress(a).lower() for a in arpa_list]) + ")"
    )
    final_ipa = FLITE.arpa_to_ipa(arpa_list_for_epitran)

    print(f"入力単語:            {word}")
    print(f"データソース:        {source}")
    print(f"ARPABET:             {' '.join(arpa_list)}")
    print(f"マップ後IPA:         {map_ipa}")
    print(f"最終IPA:             {final_ipa}")
    print("-" * 70)

    if map_ipa == final_ipa:
        print("→ arpa_to_ipaによる変更なし")
    else:
        print("→ arpa_to_ipaによる変更あり")
        print()
        print("変更箇所の分析:")

        # 変換パターンの検出
        print("\n推定される変換パターン:")
        detected_patterns = []

        # 母音の長さなど
        if len(map_ipa) != len(final_ipa):
            detected_patterns.append(
                f"文字数変化: {len(map_ipa)} → {len(final_ipa)}"
            )

        # 具体的な差異を表示
        if not detected_patterns:
            detected_patterns.append("（差異の詳細分析には追加実装が必要）")

        for pattern in detected_patterns:
            print(f"  - {pattern}")


def main():
    parser = argparse.ArgumentParser(
        description="英単語のARPABET/IPA/X-SAMPA変換を分析する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  uv run python check_eitango.py                          # デフォルトのサンプル単語
  uv run python check_eitango.py -w hello world           # 指定した単語を分析
  uv run python check_eitango.py -w beautiful --detail    # 詳細表示
  uv run python check_eitango.py --diff                   # マップとarpa_to_ipaの差異分析
  uv run python check_eitango.py --raw                    # 生のARPABETデータを表示
  uv run python check_eitango.py --use-flite              # lex_lookupを使用（Fliteインストール必須）
        """,
    )

    parser.add_argument(
        "-w",
        "--words",
        nargs="*",
        default=None,
        help="分析する英単語（スペース区切りで複数指定可能）",
    )

    parser.add_argument(
        "--detail",
        action="store_true",
        help="詳細な処理過程を表示（特徴量ベクトルを含む）",
    )

    parser.add_argument(
        "--diff",
        action="store_true",
        help="マップ結果とarpa_to_ipa適用後の差異を分析",
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="生のARPABETデータを表示",
    )

    parser.add_argument(
        "--use-flite",
        action="store_true",
        help="CMUdictの代わりにFliteのlex_lookupを使用（Fliteのインストールが必要）",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="すべての分析モードを実行",
    )

    args = parser.parse_args()

    # XSampaインスタンス
    xs = XSampa()

    print("=" * 70)
    print("英単語 → ARPABET → IPA → X-SAMPA 変換分析")
    print("(ARPABET→IPA: epitran FliteLexLookup.arpa_map)")
    print("(IPA→X-SAMPA: epitran XSampa.ipa2xs)")
    print("=" * 70)

    if args.use_flite:
        print("ARPABETソース: Flite (lex_lookup)")
    else:
        print("ARPABETソース: CMUdict")

    # デフォルトのサンプル単語
    default_words = [
        "hello",
        "world",
        "beautiful",
        "computer",
        "language",
        "phoneme",
        "synthesize",
        "pronunciation",
    ]

    words = args.words if args.words else default_words

    for word in words:
        if args.all:
            # すべてのモードを実行
            print_raw_data(word, args.use_flite)
            print_detail_alignment(word, xs, args.use_flite)
            analyze_diff(word, args.use_flite)
        elif args.raw:
            print_raw_data(word, args.use_flite)
        elif args.detail:
            print_detail_alignment(word, xs, args.use_flite)
        elif args.diff:
            analyze_diff(word, args.use_flite)
        else:
            # デフォルト: 基本的な対応関係
            print_basic_alignment(word, xs, args.use_flite)

        print()


if __name__ == "__main__":
    main()
