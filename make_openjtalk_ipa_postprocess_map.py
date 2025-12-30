#!/usr/bin/env python3
"""
jpn-Kana.txtから、OpenJTalkラベル用のpostprocessファイルを生成する。

変更点:
- 長母音変換（aa -> aː 等）を削除：長音記号ːを使わない
- 特殊長母音（ei -> eː, oɯ -> oː）を削除
- シンボル定義から長音記号付き母音を削除

残すもの:
- 異音変換（ラ行、ザ行、撥音、促音、口蓋化同化）：実際の発音に近いIPAを保持
"""

import re
from pathlib import Path


def remove_long_vowels_from_symbol(line: str) -> str:
    """シンボル定義から長音記号付き母音（aː, iː等）を削除する"""
    # シンボル定義の形式: ::name:: = value1|value2|...
    match = re.match(r"(::\w+::)\s*=\s*(.+)", line)
    if not match:
        return line

    symbol_name = match.group(1)
    values = match.group(2)

    # |で分割して、長音記号付きのものを除外
    parts = values.split("|")
    filtered_parts = [p for p in parts if "ː" not in p]

    if filtered_parts:
        return f"{symbol_name} = {'|'.join(filtered_parts)}"
    else:
        # 全部除外されたら空のシンボルになるが、それは問題
        # （実際には起きないはず）
        return line


def main():
    # パスの設定
    project_root = Path(__file__).parent
    input_path = (
        project_root
        / ".venv/lib/python3.13/site-packages/epitran/data/post/jpn-Kana.txt"
    )
    output_path = project_root / "hiho_data" / "openjtalk_postprocess.txt"

    print("=" * 60)
    print("OpenJTalkラベル用 postprocess ファイル生成")
    print("=" * 60)
    print(f"入力: {input_path}")
    print(f"出力: {output_path}")
    print()

    # 削除するルール
    rules_to_remove = {
        # 長母音変換（VV to Vː）
        "aa -> aː / _",
        "ee -> eː / _",
        "ii -> iː / _",
        "oo -> oː / _",
        "ɯɯ -> ɯː / _",
        # 特殊長母音
        "ei -> eː / _",
        "oɯ -> oː / _",
    }

    # 削除するコメント
    comments_to_remove = {
        "%VV to Vː",
        "%Some special notations for long vowels",
    }

    # jpn-Kana.txtを読み込み
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 変更を追跡
    removed_lines = []
    modified_lines = []
    output_lines = []

    for line in lines:
        stripped = line.strip()

        # 削除対象のルールかチェック
        if stripped in rules_to_remove:
            removed_lines.append(stripped)
            continue

        # 削除対象のコメントかチェック
        if stripped in comments_to_remove:
            removed_lines.append(stripped)
            continue

        # シンボル定義の場合、長音記号付き母音を削除
        if stripped.startswith("::") and "=" in stripped:
            new_line = remove_long_vowels_from_symbol(stripped)
            if new_line != stripped:
                modified_lines.append(f"{stripped} → {new_line}")
                output_lines.append(new_line + "\n")
                continue

        output_lines.append(line)

    # 出力
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print("削除されたルール/コメント:")
    for rule in removed_lines:
        print(f"  - {rule}")
    print()

    if modified_lines:
        print("変更されたシンボル定義:")
        for mod in modified_lines:
            print(f"  {mod}")
        print()

    print(f"出力ファイル: {output_path}")
    print()

    # 変更内容を表示
    print("=" * 60)
    print("生成されたファイルの内容")
    print("=" * 60)
    with open(output_path, "r", encoding="utf-8") as f:
        print(f.read())


if __name__ == "__main__":
    main()
