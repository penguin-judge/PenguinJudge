# PenguinJudge

プライベート競技プログラミングコンテスト用の
ジャッジシステムです。

## 必要なもの

* Python 3.8
* Docker
* PostgreSQL
* RabbitMQ

## DockerHub

|Image Name||
|--|--|
|[penguinjudge/backend](https://hub.docker.com/r/penguinjudge/backend)|[![DockerHub Backend Version](https://img.shields.io/docker/v/penguinjudge/backend?sort=semver)](https://hub.docker.com/r/penguinjudge/backend)|
|[penguinjudge/frontend](https://hub.docker.com/r/penguinjudge/frontend)|[![DockerHub Frontend Version](https://img.shields.io/docker/v/penguinjudge/frontend?sort=semver)](https://hub.docker.com/r/penguinjudge/frontend)|

|Language|Compile Image|Judge Image|
|--|--|--|
|C (gcc)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_c_compile?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_c_compile)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_c_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_c_judge)|
|C++ (gcc)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_cpp_compile?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_cpp_compile)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_cpp_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_cpp_judge)|
|Rust|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_rust_compile?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_rust_compile)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_rust_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_rust_judge)|
|Go|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_go_compile?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_go_compile)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_go_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_go_judge)|
|Java|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_java_compile?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_java_compile)|[![ver](https://img.shields.io/docker/v/penguinjudge/agent_java_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_java_judge)|
|Python||[![ver](https://img.shields.io/docker/v/penguinjudge/agent_python_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_python_judge)|
|Python(pypy)||[![ver](https://img.shields.io/docker/v/penguinjudge/agent_pypy3.6_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_pypy3.6_judge)|
|JavaScript (node.js)||[![ver](https://img.shields.io/docker/v/penguinjudge/agent_node_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_node_judge)|
|Ruby||[![ver](https://img.shields.io/docker/v/penguinjudge/agent_ruby_judge?sort=semver)](https://hub.docker.com/r/penguinjudge/agent_ruby_judge)|

## 起動方法

### docker

### docker-compose

docker-composeを使った起動方法

```
$ cd container
$ ./build.sh
$ cd ..
$ docker-compose up --build
```
# 設計

* すべてのデータはRDBMS(PostgreSQL)に保存

   * 問題
   * テストデータ / 正答
   * ユーザ投稿コード

* プロセス
   * ステートレス (スケールアウト可能)
      * 静的ファイル配布サーバ (nginx等)
      * RESTful APIサーバ
      * ジャッジ用ワーカ
   * ステートフル
      * PostgreSQL
      * RabbitMQ

* 答え合わせの方式
   * AtCoder方式
      * 標準入力でテストデータを注入
      * 標準出力と、正答を比較し、一致するかどうかのみを返却
      * RE / TLE
