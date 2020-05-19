# register_environments.py

`register_environments.py`に直接埋め込まれている言語環境情報を登録します

```
$ python ./register_environments.py
```

# register_contest.py

```
$ python ./register_contest.py <コンテストディレクトリ>
```

コンテストディレクトリは以下の構成としてください

```
<コンテストID>
   ├── README.md -- コンテストの説明
   ├── <問題ID>
   │      ├── README.md -- 問題の説明
   │      ├── input -- テストケース入力データフォルダ
   │      │     ├── <テストケース名>.in
   │      │     :
   │      └── output -- テストケース解答データフォルダ
   │            ├── <テストケース名>.out
   :            :
```

README.mdの最初の一行はコンテストおよび問題のタイトルとなります。
問題の場合は、最初の一行は説明文から除外されます。

コンテストのREADME.mdの場合は3行目にISO8601形式で日付時刻(タイムゾーンも必須)を指定すると、
開始・終了日時となります。またその行は取り除かれます。

問題のREADME.mdの場合は3行目に次の形式で各種制限を記入します。
「実行制限時間: 5 sec / メモリ制限: 512 MB / 配点: 100点」

## README.md (コンテスト用) のサンプル

```
# テストコンテスト

2019-12-25T21:00:00+09:00 - 2019-12-26T00:00:00+09:00

コンテストの説明がここに入ります
```

## README.md (問題用) のサンプル

```
# 問題A

実行制限時間: 5 sec / メモリ制限: 512 MB / 配点: 100点

問題の説明がここに入ります
```

# load_test.py

負荷試験ツール

# reset_password.py

パスワードリセットツール

環境変数 PENGUIN_DB_URL に DSN をセットし、 `./reset_password.py admin` とやれば admin のパスワードを変更できる

```
$ ./reset_password.py admin
New Passowrd: 
```
