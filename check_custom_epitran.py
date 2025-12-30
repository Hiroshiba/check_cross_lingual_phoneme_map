#!/usr/bin/env python3
"""
CustomEpitranクラスの実装とテスト

カスタムマッピングファイルを使用するEpitranを実装し、
jpn-Kanaと同じCSVを使って結果が一致することを確認する。
"""

import csv
import unicodedata
from collections import defaultdict

import epitran
import regex
from epitran.rules import Rules
from epitran.simple import SimpleEpitran

# =============================================================================
# CustomEpitranクラスの実装
# =============================================================================


class CustomEpitran(SimpleEpitran):
    """カスタムマッピングファイルを使用するEpitran"""

    def __init__(
        self, map_file: str, pre_file: str = None, post_file: str = None, **kwargs
    ):
        """
        Args:
            map_file: マッピングCSVファイルのパス（必須）
            pre_file: プリプロセッサルールファイルのパス（任意）
            post_file: ポストプロセッサルールファイルのパス（任意）
        """
        self._custom_map_file = map_file
        # 親のコンストラクタで'dummy-Latn'を探すが、存在しないので空になる（問題なし）
        super().__init__("dummy-Latn", preproc=False, postproc=False, **kwargs)

        # カスタムpre/postプロセッサを設定
        if pre_file:
            self.preprocessor = _CustomProcessor(pre_file)
            self.preproc = True
        if post_file:
            self.postprocessor = _CustomProcessor(post_file)
            self.postproc = True

    def _load_g2p_map(self, code: str, rev: bool):
        """カスタムファイルからマッピングを読み込む"""
        g2p = defaultdict(list)
        with open(self._custom_map_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダー(Orth,Phon)をスキップ
            for graph, phon in reader:
                graph = unicodedata.normalize("NFD", graph)
                phon = unicodedata.normalize("NFD", phon)
                if not self.tones:
                    phon = regex.sub("[˩˨˧˦˥]", "", phon)
                g2p[graph].append(phon)
        return g2p


class _CustomProcessor:
    """カスタムルールファイル用プロセッサ"""

    def __init__(self, rule_file: str):
        self.rules = Rules([rule_file])

    def process(self, word: str) -> str:
        return self.rules.apply(word)


# =============================================================================
# テスト
# =============================================================================


def main():
    # ファイルパス
    base_path = "/home/hihok/Github/check_cross_lingual_phoneme_map/.venv/lib/python3.13/site-packages/epitran/data"
    map_file = f"{base_path}/map/jpn-Kana.csv"
    post_file = f"{base_path}/post/jpn-Kana.txt"

    print("=" * 60)
    print("CustomEpitran テスト")
    print("=" * 60)
    print(f"map_file:  {map_file}")
    print(f"post_file: {post_file}")
    print()

    # 通常のEpitran
    epi_original = epitran.Epitran("jpn-Kana")

    # カスタムEpitran
    epi_custom = CustomEpitran(map_file, post_file=post_file)

    # テストケース
    test_cases = [
        "テスト",
        "コンピューター",
        "カタカナ",
        "ラーメン",
        "シャンプー",
        "サッカー",
        "ジャンプ",
        "キャンプ",
        "ッツ",
        "ンン",
        "アンカンサンタンナンア",
    ]

    print("テスト結果:")
    print("-" * 60)
    print(f"{'入力':<15} {'オリジナル':<20} {'カスタム':<20} {'一致'}")
    print("-" * 60)

    all_match = True
    for text in test_cases:
        original = epi_original.transliterate(text)
        custom = epi_custom.transliterate(text)
        match = "✓" if original == custom else "✗"
        if original != custom:
            all_match = False
        print(f"{text:<15} {original:<20} {custom:<20} {match}")

    print("-" * 60)

    if all_match:
        print("\n全てのテストケースで結果が一致しました！")
    else:
        print("\n一部のテストケースで結果が異なります。")
        print("詳細を確認してください。")

    # 追加: 内部状態の比較
    print("\n" + "=" * 60)
    print("内部状態の比較")
    print("=" * 60)
    print(
        f"g2pマッピング数: オリジナル={len(epi_original.epi.g2p)}, カスタム={len(epi_custom.g2p)}"
    )
    print(
        f"preproc有効: オリジナル={epi_original.epi.preproc}, カスタム={epi_custom.preproc}"
    )
    print(
        f"postproc有効: オリジナル={epi_original.epi.postproc}, カスタム={epi_custom.postproc}"
    )


if __name__ == "__main__":
    main()
