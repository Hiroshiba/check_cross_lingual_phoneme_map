#!/usr/bin/env python3
"""
日本語テキストからOpenJTalk音素ラベル列への変換、およびIPA音声記号列への変換

pyopenjtalkを使用して日本語テキストをOpenJTalkの音素ラベル列に変換し、
カスタムEpitranを使用してIPA音声記号列に変換する。

OpenJTalkの音素ラベル:
- 子音: b, d, f, g, h, j, k, m, n, p, r, s, t, v, w, y, z
- 複合子音: by, ch, dy, gy, gw, hy, ky, kw, my, ny, py, ry, sh, ts, ty
- 有声母音: a, i, u, e, o
- 無声母音: A, I, U, E, O
- 特殊: N(撥音), cl(促音)
"""

import argparse
import csv
import os
import unicodedata
from collections import defaultdict

import pyopenjtalk
import regex
from epitran.rules import Rules
from epitran.simple import SimpleEpitran


# =============================================================================
# OpenJTalk音素ラベル用Epitranクラス
# =============================================================================


class OpenJTalkLabelEpitran(SimpleEpitran):
    """
    OpenJTalk音素ラベルからIPAへ変換するEpitran

    SimpleEpitranを継承し、以下を修正:
    - 大文字小文字を区別（regex.Iフラグ削除、.lower()削除）
    - カスタムCSVファイルを使用
    """

    def __init__(self, map_file: str, post_file: str | None = None, **kwargs):
        """
        Args:
            map_file: マッピングCSVファイルのパス（必須）
            post_file: ポストプロセッサルールファイルのパス（任意）
        """
        self._custom_map_file = map_file
        self._custom_post_file = post_file

        # 親のコンストラクタ呼び出し
        # 'dummy-Latn'は存在しないが、後でg2pを上書きするので問題ない
        super().__init__("dummy-Latn", preproc=False, postproc=False, **kwargs)

        # カスタムpostprocessorを設定
        if post_file:
            self.postprocessor = _CustomProcessor(post_file)
            self.postproc = True

    def _load_g2p_map(self, code: str, rev: bool):
        """カスタムファイルからマッピングを読み込む（大文字小文字を区別）"""
        g2p = defaultdict(list)
        if not os.path.exists(self._custom_map_file):
            return g2p

        with open(self._custom_map_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダー(Orth,Phon)をスキップ
            for row in reader:
                if len(row) < 2:
                    continue
                graph, phon = row[0], row[1]
                graph = unicodedata.normalize("NFD", graph)
                phon = unicodedata.normalize("NFD", phon)
                if not self.tones:
                    phon = regex.sub("[˩˨˧˦˥]", "", phon)
                g2p[graph].append(phon)
        return g2p

    def _construct_regex(self, g2p_keys):
        """正規表現を構築（大文字小文字を区別、regex.Iなし）"""
        graphemes = sorted(g2p_keys, key=len, reverse=True)
        if not graphemes:
            return regex.compile(r"(.)")  # フォールバック
        return regex.compile(f"({'|'.join(regex.escape(g) for g in graphemes)})")

    def general_trans(
        self, text: str, filter_func, normpunc: bool = False, ligatures: bool = False
    ) -> str:
        """
        変換処理（大文字小文字を区別、.lower()なし）

        親クラスのgeneral_transをオーバーライドし、
        text.lower()を削除して大文字小文字を区別する。
        """
        # .lower()を削除（これが重要な変更点）
        text = unicodedata.normalize("NFD", text)

        # strip_diacriticsはダミー言語なのでスキップ可能
        # text = self.strip_diacritics.process(text)

        if self.preproc:
            text = self.preprocessor.process(text)

        tr_list = []
        while text:
            m = self.regexp.match(text)
            if m:
                source = m.group(0)
                try:
                    target = self.g2p[source][0]
                except (KeyError, IndexError):
                    target = source
                tr_list.append((target, True))
                text = text[len(source) :]
            else:
                tr_list.append((text[0], False))
                text = text[1:]

        text = "".join([s for (s, _) in filter(filter_func, tr_list)])

        if self.postproc:
            text = self.postprocessor.process(text)

        if ligatures or self.ligatures:
            from epitran.ligaturize import ligaturize

            text = ligaturize(text)

        if normpunc:
            text = self.puncnorm.norm(text)

        return unicodedata.normalize("NFC", text)


class _CustomProcessor:
    """カスタムルールファイル用プロセッサ"""

    def __init__(self, rule_file: str):
        self.rules = Rules([rule_file])

    def process(self, word: str) -> str:
        return self.rules.apply(word)


# =============================================================================
# 変換関数
# =============================================================================

# デフォルトのファイルパス
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MAP_FILE = os.path.join(_BASE_DIR, "hiho_data", "openjtalk_to_ipa.csv")
_POST_FILE = os.path.join(
    _BASE_DIR,
    ".venv/lib/python3.13/site-packages/epitran/data/post/jpn-Kana.txt",
)

# グローバルインスタンス（遅延初期化）
_epitran_instance: OpenJTalkLabelEpitran | None = None


def _get_epitran() -> OpenJTalkLabelEpitran:
    """Epitranインスタンスを取得（シングルトン）"""
    global _epitran_instance
    if _epitran_instance is None:
        _epitran_instance = OpenJTalkLabelEpitran(_MAP_FILE, post_file=_POST_FILE)
    return _epitran_instance


def text_to_phoneme_labels(text: str) -> str:
    """
    日本語テキストをOpenJTalk音素ラベル列に変換する

    Args:
        text: 日本語テキスト

    Returns:
        スペース区切りの音素ラベル列
    """
    return pyopenjtalk.g2p(text)


def text_to_phoneme_list(text: str) -> list[str]:
    """
    日本語テキストをOpenJTalk音素ラベルのリストに変換する

    Args:
        text: 日本語テキスト

    Returns:
        音素ラベルのリスト
    """
    phonemes = pyopenjtalk.g2p(text)
    return phonemes.split(" ") if phonemes else []


def phoneme_labels_to_ipa(phoneme_labels: str) -> str:
    """
    OpenJTalk音素ラベル列をIPA音声記号列に変換する

    pauラベルがある場合は、pauで分割して各部分を変換し、
    スペースで結合して返す。

    Args:
        phoneme_labels: スペース区切りの音素ラベル列

    Returns:
        IPA音声記号列（pauがあった場合はスペース区切り）
    """
    # pauで分割
    segments = split_by_pau(phoneme_labels)

    # 各セグメントを変換
    epi = _get_epitran()
    ipa_segments = []
    for segment in segments:
        # スペースを削除してモーラ単位の文字列にする
        labels_no_space = segment.replace(" ", "")
        if labels_no_space:  # 空でない場合のみ変換
            ipa = epi.transliterate(labels_no_space)
            ipa_segments.append(ipa)

    return " ".join(ipa_segments)


def split_by_pau(phoneme_labels: str) -> list[str]:
    """
    音素ラベル列をpauで分割する

    Args:
        phoneme_labels: スペース区切りの音素ラベル列

    Returns:
        pauで分割されたセグメントのリスト
    """
    phonemes = phoneme_labels.split(" ")
    segments = []
    current_segment = []

    for phoneme in phonemes:
        if phoneme == "pau":
            if current_segment:
                segments.append(" ".join(current_segment))
                current_segment = []
        else:
            current_segment.append(phoneme)

    # 最後のセグメントを追加
    if current_segment:
        segments.append(" ".join(current_segment))

    return segments


def text_to_ipa(text: str) -> str:
    """
    日本語テキストをIPA音声記号列に変換する

    Args:
        text: 日本語テキスト

    Returns:
        IPA音声記号列
    """
    phoneme_labels = text_to_phoneme_labels(text)
    return phoneme_labels_to_ipa(phoneme_labels)


# =============================================================================
# 分析・表示関数
# =============================================================================


def analyze_text(text: str) -> None:
    """
    テキストの音素変換結果を詳細に分析して表示する

    Args:
        text: 日本語テキスト
    """
    print(f"入力テキスト: {text}")
    print("-" * 50)

    # 音素ラベル列を取得
    phoneme_str = text_to_phoneme_labels(text)
    phoneme_list = text_to_phoneme_list(text)

    print(f"OpenJTalk音素: {phoneme_str}")
    print(f"音素数: {len(phoneme_list)}")

    # IPA変換
    ipa = phoneme_labels_to_ipa(phoneme_str)
    print(f"IPA: {ipa}")
    print()

    # 音素の分類
    vowels = {"a", "i", "u", "e", "o"}
    voiceless_vowels = {"A", "I", "U", "E", "O"}
    special = {"N", "cl"}

    voiced_vowel_count = 0
    voiceless_vowel_count = 0
    consonant_count = 0
    special_count = 0

    print("音素の内訳:")
    for phoneme in phoneme_list:
        if phoneme in vowels:
            voiced_vowel_count += 1
            print(f"  {phoneme:5} - 有声母音")
        elif phoneme in voiceless_vowels:
            voiceless_vowel_count += 1
            print(f"  {phoneme:5} - 無声母音")
        elif phoneme in special:
            special_count += 1
            print(f"  {phoneme:5} - 特殊音素")
        else:
            consonant_count += 1
            print(f"  {phoneme:5} - 子音")

    print()
    print("集計:")
    print(f"  有声母音: {voiced_vowel_count}")
    print(f"  無声母音: {voiceless_vowel_count}")
    print(f"  子音: {consonant_count}")
    print(f"  特殊音素: {special_count}")


def show_examples() -> None:
    """いくつかの例を表示する"""
    print("=" * 70)
    print("日本語テキスト → OpenJTalk音素ラベル列 → IPA音声記号列の例")
    print("=" * 70)
    print()

    examples = [
        "こんにちは",
        "おはようございます",
        "きつね",  # 無声母音（I）を含む
        "すし",  # 基本
        "菊",  # 無声化
        "北",  # 無声化
        "サッカー",  # 促音・長音
        "ニッポン",  # 促音・撥音
        "東京",  # 複合子音
        "シャンプー",  # 拗音・長音
    ]

    print(f"{'テキスト':15} {'OpenJTalk':25} {'IPA'}")
    print("-" * 70)
    for text in examples:
        phonemes = text_to_phoneme_labels(text)
        ipa = phoneme_labels_to_ipa(phonemes)
        print(f"{text:15} {phonemes:25} {ipa}")

    print()
    print("=" * 70)
    print("凡例")
    print("=" * 70)
    print("OpenJTalk:")
    print("  - 大文字の母音(A,I,U,E,O): 無声母音")
    print("  - 小文字の母音(a,i,u,e,o): 有声母音")
    print("  - N: 撥音（ン）")
    print("  - cl: 促音（ッ）")
    print("  - sh, ch, ts, etc.: 複合子音")
    print()
    print("IPA:")
    print("  - 無声母音は下付きの丸（◌̥）で表記")
    print("  - 長音は ː で表記")
    print("  - 撥音は環境により変化（ɴ, m, n, ŋ等）")


def show_mapping_debug() -> None:
    """マッピングの詳細デバッグ情報を表示"""
    print("=" * 70)
    print("マッピングデバッグ情報")
    print("=" * 70)
    print()

    epi = _get_epitran()
    print(f"マッピングファイル: {_MAP_FILE}")
    print(f"ポストプロセッサファイル: {_POST_FILE}")
    print(f"マッピング数: {len(epi.g2p)}")
    print(f"postproc有効: {epi.postproc}")
    print()

    # 無声母音のマッピングを表示
    print("無声母音のマッピング:")
    for label in ["A", "I", "U", "E", "O"]:
        if label in epi.g2p:
            print(f"  {label} → {epi.g2p[label][0]}")

    # 特殊音素のマッピング
    print()
    print("特殊音素のマッピング:")
    for label in ["N", "cl"]:
        if label in epi.g2p:
            print(f"  {label} → {epi.g2p[label][0]}")

    # いくつかの複合子音+母音のマッピング
    print()
    print("複合子音+母音の例:")
    for label in ["sha", "shI", "chi", "chI", "tsu", "tsU"]:
        if label in epi.g2p:
            print(f"  {label} → {epi.g2p[label][0]}")


def main():
    parser = argparse.ArgumentParser(
        description="日本語テキストからOpenJTalk音素ラベル列・IPA音声記号列への変換"
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="変換する日本語テキスト",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="音素の詳細分析を表示する",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="いくつかの例を表示する",
    )
    parser.add_argument(
        "--phoneme-only",
        action="store_true",
        help="OpenJTalk音素ラベル列のみを表示（IPAなし）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="マッピングのデバッグ情報を表示",
    )

    args = parser.parse_args()

    if args.debug:
        show_mapping_debug()
        return

    if args.examples:
        show_examples()
        return

    if args.text:
        if args.analyze:
            analyze_text(args.text)
        elif args.phoneme_only:
            result = text_to_phoneme_labels(args.text)
            print(result)
        else:
            phonemes = text_to_phoneme_labels(args.text)
            print(f"テキスト: {args.text}")
            print(f"OpenJTalk: {phonemes}")

            # pauで分割して表示
            segments = split_by_pau(phonemes)
            if len(segments) > 1:
                print()
                print(f"pauで分割されたセグメント数: {len(segments)}")
                print("-" * 50)
                epi = _get_epitran()
                for i, segment in enumerate(segments):
                    labels_no_space = segment.replace(" ", "")
                    ipa = epi.transliterate(labels_no_space) if labels_no_space else ""
                    print(f"セグメント{i+1}:")
                    print(f"  OpenJTalk: {segment}")
                    print(f"  IPA: {ipa}")
                print("-" * 50)
                print(f"IPA (結合): {phoneme_labels_to_ipa(phonemes)}")
            else:
                ipa = phoneme_labels_to_ipa(phonemes)
                print(f"IPA: {ipa}")
    else:
        if not args.examples and not args.debug:
            parser.print_help()


if __name__ == "__main__":
    main()
