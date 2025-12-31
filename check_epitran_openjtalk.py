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

import panphon
import pyopenjtalk
import regex
from epitran.rules import Rules
from epitran.simple import SimpleEpitran
from epitran.xsampa import XSampa

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
                self.nils[text[0]] += 1
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

    def transliterate(
        self, text: str, normpunc: bool = False, ligatures: bool = False
    ) -> str:
        """
        音素ラベル列をIPAに変換（未知文字の検証付き）
        """
        self.nils.clear()
        result = super().transliterate(text, normpunc=normpunc, ligatures=ligatures)
        unknown_chars = {
            char: count for char, count in self.nils.items() if char not in (" ",)
        }
        if unknown_chars:
            char_list = ", ".join(
                f"'{char}' ({count}回)" for char, count in unknown_chars.items()
            )
            raise ValueError(
                f"Unknown phoneme label(s) detected: {char_list}\n"
                f"Input: {text}\n"
                f"Mapping file: {self._custom_map_file}"
            )
        return result


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
_POST_FILE = os.path.join(_BASE_DIR, "hiho_data", "openjtalk_postprocess.txt")

# グローバルインスタンス（遅延初期化）
_epitran_instance: OpenJTalkLabelEpitran | None = None

# panphonのFeatureTable（特徴量ベクトル取得用）
_FT = panphon.FeatureTable()

# XSampaインスタンス（IPA→X-SAMPA変換用）
_XS = XSampa()


def _get_epitran() -> OpenJTalkLabelEpitran:
    """Epitranインスタンスを取得（シングルトン）"""
    global _epitran_instance
    if _epitran_instance is None:
        _epitran_instance = OpenJTalkLabelEpitran(_MAP_FILE, post_file=_POST_FILE)
    return _epitran_instance


def read_lab_file(lab_file: str) -> str:
    """
    labファイルから音素ラベル列を読み込む

    Args:
        lab_file: labファイルのパス

    Returns:
        スペース区切りの音素ラベル列
    """
    from pathlib import Path

    labels = []
    with Path(lab_file).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                label = parts[2]
                labels.append(label)
    return " ".join(labels)


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

    pauまたはsilラベルがある場合は、それらで分割して各部分を変換し、
    スペースで結合して返す。

    Args:
        phoneme_labels: スペース区切りの音素ラベル列

    Returns:
        IPA音声記号列（pauまたはsilがあった場合はスペース区切り）
    """
    # pauまたはsilで分割
    segments = split_by_silence_markers(phoneme_labels)

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


def split_by_silence_markers(phoneme_labels: str) -> list[str]:
    """
    音素ラベル列をpauまたはsilで分割する

    Args:
        phoneme_labels: スペース区切りの音素ラベル列

    Returns:
        pauまたはsilで分割されたセグメントのリスト
    """
    phonemes = phoneme_labels.split(" ")
    segments = []
    current_segment = []

    for phoneme in phonemes:
        if phoneme == "pau" or phoneme == "sil":
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


def analyze_phoneme_labels_detail(
    phoneme_str: str, source_label: str = "音素ラベル"
) -> None:
    """
    音素ラベル列のIPA変換結果について特徴量ベクトルを含む詳細分析を表示

    Args:
        phoneme_str: スペース区切りの音素ラベル列
        source_label: 入力ソースのラベル（"テキスト"や"labファイル"など）
    """
    print(f"【{source_label}】の詳細分析")
    print("-" * 70)

    print(f"OpenJTalk:    {phoneme_str}")

    # IPA変換
    ipa = phoneme_labels_to_ipa(phoneme_str)
    print(f"IPA:          {ipa}")

    # X-SAMPA変換
    xsampa = _XS.ipa2xs(ipa)
    print(f"X-SAMPA:      {xsampa}")
    print()

    # IPA全体のセグメント分析
    print("IPAセグメント分析:")
    seg_objs = _FT.word_fts(ipa)
    ipa_segs = _FT.ipa_segs(ipa)

    if seg_objs and ipa_segs:
        print(f"  セグメント数: {len(seg_objs)}")
        print(f"  {'IPA':<10} {'X-SAMPA':<12} {'特徴量ベクトル'}")
        print("  " + "-" * 66)

        for seg_str, seg_obj in zip(ipa_segs, seg_objs):
            seg_xsampa = _XS.ipa2xs(seg_str)
            vec = seg_obj.numeric()
            print(f"  {seg_str:<10} {seg_xsampa:<12} {vec}")
    else:
        print("  セグメント情報なし")

    print()


def analyze_text_detail(text: str) -> None:
    """
    単一テキストのIPA変換結果について特徴量ベクトルを含む詳細分析を表示

    Args:
        text: 日本語テキスト
    """
    phoneme_str = text_to_phoneme_labels(text)
    analyze_phoneme_labels_detail(phoneme_str, source_label=text)


def show_detail_analysis() -> None:
    """
    サンプルテキストのIPA変換結果について特徴量ベクトルを含む詳細分析を表示
    """
    print("=" * 70)
    print("詳細分析（特徴量ベクトル含む）")
    print("=" * 70)
    print()

    examples = [
        "こんにちは",
        "きつね",
        "サッカー",
    ]

    for text in examples:
        analyze_text_detail(text)
        print()


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
    parser.add_argument(
        "--detail",
        action="store_true",
        help="特徴量ベクトルを含む詳細分析を表示",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="すべての分析モードを実行（examples、debug、detail）",
    )
    parser.add_argument(
        "--lab",
        type=str,
        help="音素ラベルを読み込むlabファイルのパス",
    )

    args = parser.parse_args()

    # textとlabは排他的
    if args.text and args.lab:
        parser.error("textとlabは同時に指定できません")

    # labファイルが指定された場合
    if args.lab:
        if not args.detail and not args.all:
            parser.error("--labオプションは--detailまたは--allと併用してください")

        phoneme_str = read_lab_file(args.lab)
        source_label = args.lab

        if args.all:
            print("=" * 70)
            print(f"【{source_label}】の全分析")
            print("=" * 70)
            print()

            ipa = phoneme_labels_to_ipa(phoneme_str)
            xsampa = _XS.ipa2xs(ipa)
            print(f"labファイル:  {source_label}")
            print(f"OpenJTalk:    {phoneme_str}")
            print(f"IPA:          {ipa}")
            print(f"X-SAMPA:      {xsampa}")
            print()

            print("-" * 70)
            print("マッピング情報:")
            print("-" * 70)
            epi = _get_epitran()
            print(f"マッピングファイル: {_MAP_FILE}")
            print(f"ポストプロセッサファイル: {_POST_FILE}")
            print(f"postproc有効: {epi.postproc}")
            print()

            print("-" * 70)
            print("詳細分析:")
            print("-" * 70)
            analyze_phoneme_labels_detail(phoneme_str, source_label=source_label)
            print()
        elif args.detail:
            analyze_phoneme_labels_detail(phoneme_str, source_label=source_label)
        return

    # デフォルトのサンプルテキスト
    default_texts = [
        "こんにちは",
        "おはようございます",
        "きつね",
    ]

    # テキストが指定されていない場合はデフォルトを使用
    texts = [args.text] if args.text else default_texts

    # --allオプション：全ての分析モードを実行
    if args.all:
        for text in texts:
            print("=" * 70)
            print(f"【{text}】の全分析")
            print("=" * 70)
            print()

            # 基本的な変換結果
            phonemes = text_to_phoneme_labels(text)
            ipa = phoneme_labels_to_ipa(phonemes)
            xsampa = _XS.ipa2xs(ipa)
            print(f"テキスト:     {text}")
            print(f"OpenJTalk:    {phonemes}")
            print(f"IPA:          {ipa}")
            print(f"X-SAMPA:      {xsampa}")
            print()

            # マッピングデバッグ情報（最初の1回のみ）
            if text == texts[0]:
                print("-" * 70)
                print("マッピング情報:")
                print("-" * 70)
                epi = _get_epitran()
                print(f"マッピングファイル: {_MAP_FILE}")
                print(f"ポストプロセッサファイル: {_POST_FILE}")
                print(f"postproc有効: {epi.postproc}")
                print()

            # 詳細分析
            print("-" * 70)
            print("詳細分析:")
            print("-" * 70)
            analyze_text_detail(text)
            print()
        return

    # --debugオプション：マッピングデバッグ情報のみ
    if args.debug:
        show_mapping_debug()
        return

    # --examplesオプション：サンプル例のみ
    if args.examples:
        show_examples()
        return

    # --detailオプション：詳細分析のみ（デフォルトサンプルまたは指定テキスト）
    if args.detail:
        if args.text:
            analyze_text_detail(args.text)
        else:
            show_detail_analysis()
        return

    # テキスト引数が指定されている場合
    if args.text:
        if args.phoneme_only:
            result = text_to_phoneme_labels(args.text)
            print(result)
        else:
            phonemes = text_to_phoneme_labels(args.text)
            print(f"テキスト: {args.text}")
            print(f"OpenJTalk: {phonemes}")

            # pauまたはsilで分割して表示
            segments = split_by_silence_markers(phonemes)
            if len(segments) > 1:
                print()
                print(f"pauで分割されたセグメント数: {len(segments)}")
                print("-" * 50)
                epi = _get_epitran()
                for i, segment in enumerate(segments):
                    labels_no_space = segment.replace(" ", "")
                    ipa = epi.transliterate(labels_no_space) if labels_no_space else ""
                    print(f"セグメント{i + 1}:")
                    print(f"  OpenJTalk: {segment}")
                    print(f"  IPA: {ipa}")
                print("-" * 50)
                print(f"IPA (結合): {phoneme_labels_to_ipa(phonemes)}")
            else:
                ipa = phoneme_labels_to_ipa(phonemes)
                print(f"IPA: {ipa}")
    else:
        if not args.examples and not args.debug and not args.detail and not args.all:
            parser.print_help()


if __name__ == "__main__":
    main()
