#!/usr/bin/env python3
"""
日本語テキストからOpenJTalk音素ラベル列への変換

pyopenjtalkを使用して日本語テキストをOpenJTalkの音素ラベル列に変換する。

OpenJTalkの音素ラベル:
- 子音: b, d, f, g, h, j, k, m, n, p, r, s, t, v, w, y, z
- 複合子音: by, ch, dy, gy, gw, hy, ky, kw, my, ny, py, ry, sh, ts, ty
- 有声母音: a, i, u, e, o
- 無声母音: A, I, U, E, O
- 特殊: N(撥音), cl(促音)
"""

import argparse

import pyopenjtalk


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


def analyze_text(text: str) -> None:
    """
    テキストの音素変換結果を詳細に分析して表示する

    Args:
        text: 日本語テキスト
    """
    print(f"入力テキスト: {text}")
    print("-" * 40)

    # 音素ラベル列を取得
    phoneme_str = text_to_phoneme_labels(text)
    phoneme_list = text_to_phoneme_list(text)

    print(f"音素ラベル列: {phoneme_str}")
    print(f"音素数: {len(phoneme_list)}")
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


def main():
    parser = argparse.ArgumentParser(
        description="日本語テキストからOpenJTalk音素ラベル列への変換"
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

    args = parser.parse_args()

    if args.examples:
        print("=" * 60)
        print("日本語テキスト → OpenJTalk音素ラベル列の例")
        print("=" * 60)
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

        for text in examples:
            phonemes = text_to_phoneme_labels(text)
            print(f"{text:15} → {phonemes}")

        print()
        print("=" * 60)
        print("凡例")
        print("=" * 60)
        print("- 大文字の母音(A,I,U,E,O): 無声母音")
        print("- 小文字の母音(a,i,u,e,o): 有声母音")
        print("- N: 撥音（ン）")
        print("- cl: 促音（ッ）")
        print("- sh, ch, ts, etc.: 複合子音")
        return

    if args.text:
        if args.analyze:
            analyze_text(args.text)
        else:
            result = text_to_phoneme_labels(args.text)
            print(result)
    else:
        if not args.examples:
            parser.print_help()


if __name__ == "__main__":
    main()
