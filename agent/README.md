# Agent

コンパイル/ジャッジ制御用エージェント.

静的バイナリにビルドしてコンテナ内にコピーして使う。
静的バイナリのビルドには `build_static_binary.sh` を実行する (要 x86_64-unknown-linux-musl ターゲット)

## ビルド/テスト方法

```
$ cargo build
$ cargo test
```

## 静的バイナリビルド方法

```
$ rustup target add x86_64-unknown-linux-musl
$ ./build_static_binary.sh
```

## 仕様

標準入出力のみを用いて、Judge Workerと通信する。
シリアライズ形式はMessagePack。プロトコルは models.rs や Worker側の実装を参照のこと。

言語に依存する設定はコンテナ内の`/config.json`に記述する。
おおよそ以下のような形式で設定を書き込む (詳細は `config.rs` を参照)。

```
{
 "compile": { <- オプション
   "path": "<Agentが書き込むソースコードのパス>",
   "output": "<コンパイラのバイナリ出力パス>",
   "cmd": "<コンパイラのパス>"
   "args": [
     "<コンパイラの引数1>",
     "<コンパイラの引数2>"
   ]
 },
 "test": {    <- 必須
   "path": "<Agentが書き込むバイナリ/スクリプトのパス>",
   "cmd": "<プログラム実行形式のパス>",
   "args": [
     "<cmdに渡す引数1>",
     "<cmdに渡す引数2>"
   ]
 }
}
```
