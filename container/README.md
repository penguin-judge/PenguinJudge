# コンパイル/ジャッジ用コンテナイメージ作成スクリプト

## フォルダ構造とDockerイメージ名

* `言語名/Dockerfile.:<tag>`: Python等コンパイルが不要な場合

   * `penguin_judge_言語名:<tag>` というイメージ名になる

* `言語名/Dockerfile.(compile|judge):<tag>`: compile/judgeの箇所は任意の文字列でも可能

   * `penguin_judge_言語名_(compile|judge):<tag>` というイメージ名になる

## ビルド方法

以下のコマンドを実行するとすべてのイメージをビルドします

```
$ ./build.sh
```
