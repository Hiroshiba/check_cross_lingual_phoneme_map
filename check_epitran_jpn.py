"""
epitranのjpn-Kanaを使って、対応する全カタカナとそのIPA/X-SAMPA変換を確認するスクリプト
"""

import epitran
from epitran.xsampa import XSampa


def get_all_katakana_mappings():
    """
    epitranのjpn-Kanaで対応する全カタカナとそのIPA変換を取得する
    """
    print("=" * 60)
    print("epitran jpn-Kana の対応カタカナ一覧")
    print("=" * 60)

    # epitranのインスタンスを作成
    # jpn-Kana: カタカナ, jpn-Hira: ひらがな, jpn-Jpan: 漢字含む
    # まずjpn-Kanaを試す
    code = "jpn-Kana"
    print(f"使用コード: {code}")
    epi = epitran.Epitran(code)
    xs = XSampa()

    # 基本カタカナ（ア行〜ワ行、ン）
    basic_katakana = [
        # ア行
        "ア",
        "イ",
        "ウ",
        "エ",
        "オ",
        # カ行
        "カ",
        "キ",
        "ク",
        "ケ",
        "コ",
        # サ行
        "サ",
        "シ",
        "ス",
        "セ",
        "ソ",
        # タ行
        "タ",
        "チ",
        "ツ",
        "テ",
        "ト",
        # ナ行
        "ナ",
        "ニ",
        "ヌ",
        "ネ",
        "ノ",
        # ハ行
        "ハ",
        "ヒ",
        "フ",
        "ヘ",
        "ホ",
        # マ行
        "マ",
        "ミ",
        "ム",
        "メ",
        "モ",
        # ヤ行
        "ヤ",
        "ユ",
        "ヨ",
        # ラ行
        "ラ",
        "リ",
        "ル",
        "レ",
        "ロ",
        # ワ行
        "ワ",
        "ヲ",
        # ン
        "ン",
    ]

    # 濁音・半濁音
    dakuon_handakuon = [
        # ガ行
        "ガ",
        "ギ",
        "グ",
        "ゲ",
        "ゴ",
        # ザ行
        "ザ",
        "ジ",
        "ズ",
        "ゼ",
        "ゾ",
        # ダ行
        "ダ",
        "ヂ",
        "ヅ",
        "デ",
        "ド",
        # バ行
        "バ",
        "ビ",
        "ブ",
        "ベ",
        "ボ",
        # パ行
        "パ",
        "ピ",
        "プ",
        "ペ",
        "ポ",
    ]

    # 拗音（小さいャュョ）
    youon = [
        # キャ行
        "キャ",
        "キュ",
        "キョ",
        # シャ行
        "シャ",
        "シュ",
        "ショ",
        # チャ行
        "チャ",
        "チュ",
        "チョ",
        # ニャ行
        "ニャ",
        "ニュ",
        "ニョ",
        # ヒャ行
        "ヒャ",
        "ヒュ",
        "ヒョ",
        # ミャ行
        "ミャ",
        "ミュ",
        "ミョ",
        # リャ行
        "リャ",
        "リュ",
        "リョ",
        # ギャ行
        "ギャ",
        "ギュ",
        "ギョ",
        # ジャ行
        "ジャ",
        "ジュ",
        "ジョ",
        # ビャ行
        "ビャ",
        "ビュ",
        "ビョ",
        # ピャ行
        "ピャ",
        "ピュ",
        "ピョ",
    ]

    # 特殊音（外来語用）
    special = [
        # ファ行など
        "ファ",
        "フィ",
        "フェ",
        "フォ",
        # ティ・ディ
        "ティ",
        "ディ",
        # トゥ・ドゥ
        "トゥ",
        "ドゥ",
        # ツァ行
        "ツァ",
        "ツィ",
        "ツェ",
        "ツォ",
        # ウィ・ウェ・ウォ
        "ウィ",
        "ウェ",
        "ウォ",
        # ヴァ行
        "ヴァ",
        "ヴィ",
        "ヴ",
        "ヴェ",
        "ヴォ",
        # シェ・ジェ・チェ
        "シェ",
        "ジェ",
        "チェ",
        # イェ
        "イェ",
        # クァ行など
        "クァ",
        "クィ",
        "クェ",
        "クォ",
        # グァ行
        "グァ",
        "グィ",
        "グェ",
        "グォ",
        # テュ・デュ
        "テュ",
        "デュ",
        # フュ
        "フュ",
    ]

    # 促音・長音
    special_marks = [
        "ッ",  # 促音
        "ー",  # 長音
    ]

    # 小さい文字
    small_kana = [
        "ァ",
        "ィ",
        "ゥ",
        "ェ",
        "ォ",
        "ャ",
        "ュ",
        "ョ",
        "ヮ",
    ]

    all_categories = [
        ("基本カタカナ", basic_katakana),
        ("濁音・半濁音", dakuon_handakuon),
        ("拗音", youon),
        ("外来語用特殊音", special),
        ("促音・長音", special_marks),
        ("小さい文字", small_kana),
    ]

    results = {}

    for category_name, katakana_list in all_categories:
        print(f"\n【{category_name}】")
        print("-" * 50)
        print(f"{'カタカナ':<8} {'IPA':<15} {'X-SAMPA':<15}")
        print("-" * 50)

        for kana in katakana_list:
            try:
                ipa = epi.transliterate(kana)
                xsampa = xs.ipa2xs(ipa)
                print(f"{kana:<8} {ipa:<15} {xsampa:<15}")
                results[kana] = {"ipa": ipa, "xsampa": xsampa}
            except Exception as e:
                print(f"{kana:<8} エラー: {e}")
                results[kana] = {"ipa": None, "xsampa": None, "error": str(e)}

    return results


def get_epitran_map_data():
    """
    epitranの内部マッピングデータを取得する
    """
    print("\n" + "=" * 60)
    print("epitran 内部マッピングデータの確認")
    print("=" * 60)

    try:
        epi = epitran.Epitran("jpn-Kana")

        # SimpleEpitranの内部構造を確認
        if hasattr(epi, "epi"):
            inner_epi = epi.epi
            print(f"内部クラス: {type(inner_epi).__name__}")

            # マッピングテーブルを確認
            if hasattr(inner_epi, "g2p"):
                g2p_map = inner_epi.g2p
                print(f"g2pオブジェクトの型: {type(g2p_map)}")
                print(f"\nマッピングエントリ数: {len(g2p_map)}")

                # defaultdictをdictに変換して内容を表示
                g2p_dict = dict(g2p_map)
                print("\n【epitran内部マッピング全一覧】")
                print("-" * 50)
                print(f"{'カタカナ':<10} {'IPA':<20}")
                print("-" * 50)

                for orth, phon in sorted(g2p_dict.items()):
                    # phonがリストの場合は結合
                    if isinstance(phon, list):
                        phon_str = "".join(phon)
                    else:
                        phon_str = str(phon)
                    print(f"  {orth:<10} {phon_str:<20}")

                return g2p_dict

    except Exception as e:
        print(f"エラー: {e}")
        import traceback

        traceback.print_exc()

    return None


def test_sample_words():
    """
    サンプル単語でテスト
    """
    print("\n" + "=" * 60)
    print("サンプル単語のテスト")
    print("=" * 60)

    epi = epitran.Epitran("jpn-Kana")
    xs = XSampa()

    test_words = [
        "カタカナ",
        "アリガトウ",
        "コンニチハ",
        "サッカー",
        "キョウト",
        "ニッポン",
        "トウキョウ",
        "コーヒー",
        "ファイル",
        "ティッシュ",
        "ヴァイオリン",
        "シュミレーション",
        "アンカンサンタンナンハンマンヤンランワンア",
    ]

    print(f"{'単語':<15} {'IPA':<20} {'X-SAMPA':<20}")
    print("-" * 55)

    for word in test_words:
        try:
            ipa = epi.transliterate(word)
            xsampa = xs.ipa2xs(ipa)
            print(f"{word:<15} {ipa:<20} {xsampa:<20}")
        except Exception as e:
            print(f"{word:<15} エラー: {e}")


if __name__ == "__main__":
    # 全カタカナのマッピングを取得
    results = get_all_katakana_mappings()

    # 内部マッピングデータを確認
    map_data = get_epitran_map_data()

    # サンプル単語テスト
    test_sample_words()

    # 結果のサマリー
    print("\n" + "=" * 60)
    print("サマリー")
    print("=" * 60)
    print(f"テストしたカタカナ数: {len(results)}")
    success_count = sum(1 for r in results.values() if r.get("ipa") is not None)
    print(f"変換成功: {success_count}")
    print(f"変換失敗: {len(results) - success_count}")

    if map_data:
        print(f"\nepitran内部マッピングエントリ数: {len(map_data)}")
