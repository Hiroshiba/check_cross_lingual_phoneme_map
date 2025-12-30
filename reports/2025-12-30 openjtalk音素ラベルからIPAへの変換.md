# OpenJTalk音素ラベル → IPA変換の調査レポート

## 1. 調査概要

### 目的
OpenJTalkの音素ラベル（無声母音含む）をepit ranの仕組みを利用してIPAに変換できるか調査する。

### 結論
**可能。** ただし、以下の修正が必要：
- `SimpleEpitran`の`.lower()`と`regex.I`を削除して大文字小文字を区別
- スペース区切りの入力を前提とし、postprocessorでスペース削除後にjpn-Kana同等の後処理を適用

---

## 2. OpenJTalkの音素ラベル

### 情報源
- VOICEVOX/voicevox_engine リポジトリ
  - `voicevox_engine/tts_pipeline/phoneme.py` - 音素の型定義、無声母音の定義
  - `voicevox_engine/tts_pipeline/mora_mapping.py` - モーラと音素の対応表

### 音素一覧

#### 子音（Consonant）
| 種別 | ラベル |
|------|--------|
| 単独 | `b`, `d`, `f`, `g`, `h`, `j`, `k`, `m`, `n`, `p`, `r`, `s`, `t`, `v`, `w`, `y`, `z` |
| 複合 | `by`, `ch`, `dy`, `gy`, `gw`, `hy`, `ky`, `kw`, `my`, `ny`, `py`, `ry`, `sh`, `ts`, `ty` |

#### 母音（Vowel）
| 種別 | ラベル |
|------|--------|
| 有声 | `a`, `i`, `u`, `e`, `o` |
| 無声 | `A`, `I`, `U`, `E`, `O` |

#### 特殊
| ラベル | 意味 |
|--------|------|
| `N` | 撥音（ン） |
| `cl` | 促音（ッ） |
| `pau` | ポーズ（今回は来ない想定） |

### 重要な特徴
1. **大文字小文字で有声/無声を区別** - `a`（有声）vs `A`（無声）
2. **2文字の複合子音がある** - `ky`, `sh`, `ch`など
3. **`N`と`n`の区別が必要** - `N`（撥音）vs `n`（ナ行子音）
4. **`cl`と`ch`の区別** - 両方`c`で始まるが2文字目で区別可能

---

## 3. epitranの仕組み

### 3.1 SimpleEpitran（jpn-Kana等で使用）

#### 情報源
- dmort27/epitran リポジトリ
  - `epitran/simple.py` - SimpleEpitranクラスの実装

#### マッチング方式
1. CSVからマッピングを読み込み（`_load_g2p_map`）
2. **長さ降順でソート**して正規表現を構築（`_construct_regex`）
3. 最長一致でマッチング（`general_trans`）

#### 問題点：大文字小文字の同一視
- `simple.py` 134行目付近: `text = unicodedata.normalize('NFD', text.lower())`
- `simple.py` 68行目付近: `regex.compile(..., regex.I)`

これにより`N`と`n`、`A`と`a`が区別できない。

### 3.2 Flite（ARPABET用）

#### 情報源
- dmort27/epitran リポジトリ
  - `epitran/flite.py` - Fliteクラスの実装
  - `epitran/data/arpabet.csv` - ARPABET→IPAマッピング

#### 処理方式
1. **スペースで分割**（`arpa_text_to_list`: `arpa_text.split(' ')`）
2. 各音素を**単純な辞書ルックアップ**で変換
3. 結合して出力

#### 重要な発見
ARPABETの処理は**スペース区切りを前提**としており、SimpleEpitranの正規表現マッチングとは全く異なるアプローチ。

### 3.3 postprocessor

#### 情報源
- epitran/data/post/jpn-Kana.txt - 日本語の後処理ルール
- epitran/rules.py - Rulesクラスの実装

#### jpn-Kanaの後処理内容
1. 長母音変換（`aa`→`aː`等）- 将来的に不要になる可能性あり
2. 特殊な長母音（`ei`→`eː`等）- 同上
3. ラ行の異音（`ɾ`→`ɖ`）
4. ザ行の異音（`z`→`d͡z`等）
5. 撥音の異音（`ɴ`→`m`/`n`/`ŋ`等、環境依存）
6. 促音の異音（`ʔ`→次の子音）

---

## 4. 設計方針

### 4.1 スペース区切りの採用

#### 理由
1. ARPABETと同様に曖昧さを排除できる
2. `pau`と「パウ」（`p a u`）の衝突を回避（今回pauは来ないが）
3. epitranの正規表現マッチングをそのまま活用可能（スペースは素通り）

#### 処理フロー
```
入力: "ky a N sh i"
  ↓ SimpleEpitranの正規表現マッチング（スペースは素通り）
中間: "kʲ a ɴ ɕ i"
  ↓ postprocessor（スペース削除 → jpn-Kana同等ルール）
出力: "kʲaɴɕi"
```

### 4.2 大文字小文字の区別

#### 必要な修正箇所
- `_construct_regex`: `regex.I`フラグを削除
- `general_trans`: `.lower()`を削除

#### 参考実装
- 本リポジトリの`check_custom_epitran.py` - CustomEpitranクラス

### 4.3 postprocessorの設計

#### 方針
1. **最初にスペース削除**
2. その後、jpn-Kana同等のルールを適用

#### 注意点
- ルールは記述順に適用される（`epitran/rules.py`参照）
- スペースがあるとルールがマッチしないため、最初に削除が必須

---

## 5. 必要な実装

### 5.1 OpenJTalkPhonemeLabelEpitranクラス

#### 親クラス
`SimpleEpitran`を継承（`check_custom_epitran.py`のCustomEpitranを参考）

#### オーバーライドが必要なメソッド
| メソッド | 修正内容 |
|----------|----------|
| `_construct_regex` | `regex.I`を削除 |
| `general_trans` | `.lower()`を削除 |
| `_load_g2p_map` | カスタムCSVを読み込むように変更（CustomEpitranと同様） |

### 5.2 CSVマッピングファイル

#### 必要なエントリ
| OpenJTalkラベル | IPA |
|-----------------|-----|
| 複合子音（`ky`, `sh`等） | 対応するIPA |
| 単独子音（`k`, `s`等） | 対応するIPA |
| 有声母音（`a`, `i`等） | 対応するIPA |
| 無声母音（`A`, `I`等） | 無声化記号付きIPA（`ḁ`, `i̥`等） |
| `N` | `ɴ` |
| `cl` | `ʔ` |

#### 参考
- `epitran/data/map/jpn-Kana.csv` - 既存のカタカナ→IPAマッピング
- 上記を参考に、OpenJTalkラベル用に再構成

### 5.3 postprocessorファイル

#### 構成
```
% スペース削除（最初に実行）
  ->  / _

% 以下、jpn-Kana.txtの内容を必要に応じて調整
```

#### 参考
- `epitran/data/post/jpn-Kana.txt` - 既存の後処理ルール

---

## 6. 参考リソースまとめ

### epitranリポジトリ（dmort27/epitran）
| ファイル | 内容 |
|----------|------|
| `epitran/simple.py` | SimpleEpitranの実装、マッチング処理 |
| `epitran/flite.py` | ARPABET処理の実装、スペース分割方式 |
| `epitran/rules.py` | postprocessorのルール適用ロジック |
| `epitran/data/map/jpn-Kana.csv` | カタカナ→IPAマッピング |
| `epitran/data/post/jpn-Kana.txt` | 日本語の後処理ルール |
| `epitran/data/arpabet.csv` | ARPABET→IPAマッピング |

### VOICEVOXリポジトリ（VOICEVOX/voicevox_engine）
| ファイル | 内容 |
|----------|------|
| `voicevox_engine/tts_pipeline/phoneme.py` | 音素の型定義、有声/無声の区別 |
| `voicevox_engine/tts_pipeline/mora_mapping.py` | モーラと音素の対応表 |

### 本リポジトリ
| ファイル | 内容 |
|----------|------|
| `check_custom_epitran.py` | カスタムCSVを使うEpitranの参考実装 |
| `.venv/lib/python3.13/site-packages/epitran/data/` | インストール済みepitranのデータファイル |

---

## 7. 今後の検討事項（メモ）

- 長音変換（`aa`→`aː`）を将来的にやめる場合、postprocessorの該当ルールを削除
- `ei`→`eː`変換も同様
- panphonとの互換性は確認済み（無声母音に対応）
