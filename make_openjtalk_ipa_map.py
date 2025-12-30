#!/usr/bin/env python3
"""
mora_mapping.pyとjpn-Kana.csvから、OpenJTalk音素ラベル→IPAの変換マップCSVを生成する。

- mora_mapping.pyの_mora_list_minimumを使用（_mora_list_additionalは無視）
- jpn-Kana.csvからカタカナ→IPAの対応を取得
- 無声母音バージョン（A, I, U, E, O）も生成
"""

import csv
import sys
import warnings
from pathlib import Path

# voicevox_engineをインポートするためにパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent / "voicevox_engine"))

from voicevox_engine.tts_pipeline.mora_mapping import _mora_list_minimum


def load_kana_to_ipa_map(csv_path: Path) -> dict[str, str]:
    """jpn-Kana.csvからカタカナ→IPAのマッピングを読み込む"""
    kana_to_ipa: dict[str, str] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # ヘッダー(Orth,Phon)をスキップ
        for row in reader:
            if len(row) >= 2:
                kana, ipa = row[0], row[1]
                kana_to_ipa[kana] = ipa
    return kana_to_ipa


def add_voiceless_diacritic(ipa: str) -> str:
    """
    IPA文字列の母音に無声化記号（̥ U+0325）を付加する。
    母音は文字列の末尾にあると仮定。
    """
    # IPA母音の一覧
    vowels = set("aeiouɯɔəɪʊɛæɑʌɒɐɘɤɵœøyɶ")

    if not ipa:
        return ipa

    # 末尾から母音を探して無声化記号を付加
    result = list(ipa)
    for i in range(len(result) - 1, -1, -1):
        if result[i] in vowels:
            result[i] = result[i] + "\u0325"  # 無声化記号
            break

    return "".join(result)


def main():
    # パスの設定
    project_root = Path(__file__).parent
    kana_csv_path = (
        project_root
        / ".venv/lib/python3.13/site-packages/epitran/data/map/jpn-Kana.csv"
    )
    output_csv_path = project_root / "hiho_data" / "openjtalk_to_ipa.csv"

    print("=" * 60)
    print("OpenJTalk音素ラベル → IPA 変換マップ生成")
    print("=" * 60)
    print(f"入力: jpn-Kana.csv from {kana_csv_path}")
    print(f"出力: {output_csv_path}")
    print()

    # jpn-Kana.csvを読み込み
    kana_to_ipa = load_kana_to_ipa_map(kana_csv_path)
    print(f"jpn-Kana.csvから読み込んだエントリ数: {len(kana_to_ipa)}")

    # 変換マップを構築
    openjtalk_to_ipa: dict[str, str] = {}
    missing_kana: list[str] = []

    print(f"\nmora_mapping.pyの_mora_list_minimumのエントリ数: {len(_mora_list_minimum)}")
    print()

    for kana, consonant, vowel in _mora_list_minimum:
        # OpenJTalkの音素ラベル（子音+母音）を構築
        openjtalk_label = (consonant or "") + vowel

        # カタカナに対応するIPAを取得
        if kana in kana_to_ipa:
            ipa = kana_to_ipa[kana]
            openjtalk_to_ipa[openjtalk_label] = ipa

            # 無声母音バージョンを生成（a, i, u, e, o のみ）
            if vowel in ("a", "i", "u", "e", "o"):
                voiceless_vowel = vowel.upper()
                voiceless_label = (consonant or "") + voiceless_vowel
                voiceless_ipa = add_voiceless_diacritic(ipa)
                openjtalk_to_ipa[voiceless_label] = voiceless_ipa
        else:
            missing_kana.append(kana)

    if missing_kana:
        warnings.warn(
            f"jpn-Kana.csvに見つからなかったカタカナ: {missing_kana}",
            stacklevel=2,
        )

    # ヴァ行をv系IPAに上書き（jpn-Kana.csvではb系になっているため）
    v_overrides = {
        "va": "va",
        "vA": "v" + "a\u0325",  # 無声化
        "vi": "vi",
        "vI": "v" + "i\u0325",
        "vu": "vɯ",
        "vU": "vɯ\u0325",
        "ve": "ve",
        "vE": "v" + "e\u0325",
        "vo": "vo",
        "vO": "v" + "o\u0325",
    }
    openjtalk_to_ipa.update(v_overrides)

    # CSVに出力
    with open(output_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Orth", "Phon"])
        # 長さ降順でソート（SimpleEpitranの最長一致マッチングのため）
        for label in sorted(openjtalk_to_ipa.keys(), key=len, reverse=True):
            writer.writerow([label, openjtalk_to_ipa[label]])

    print(f"生成されたエントリ数: {len(openjtalk_to_ipa)}")
    print(f"出力ファイル: {output_csv_path}")

    # 内容を表示
    print()
    print("=" * 60)
    print("生成されたマッピング（一部抜粋）")
    print("=" * 60)
    print(f"{'OpenJTalkラベル':<15} {'IPA':<20}")
    print("-" * 35)

    # サンプルを表示
    samples = ["shi", "shI", "ki", "kI", "tsu", "tsU", "N", "cl", "a", "A"]
    for sample in samples:
        if sample in openjtalk_to_ipa:
            print(f"{sample:<15} {openjtalk_to_ipa[sample]:<20}")

    print()
    print("=" * 60)
    print("全エントリ")
    print("=" * 60)
    for label in sorted(openjtalk_to_ipa.keys(), key=len, reverse=True):
        print(f"{label:<15} {openjtalk_to_ipa[label]}")


if __name__ == "__main__":
    main()
