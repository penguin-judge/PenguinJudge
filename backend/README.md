## Requirement

- python3
- pip
- postgres
- rabbitmq
- docker

## Configure

create config.ini with reference to config.ini.template.  
`sqlalchemy.url` and `mq.url` must be specified.  
make user of postgres and rabbitmq.  
make `penguin_judge` Virtual host in rabbitmq.  
make `penguin_judge` Database in postgres.  

## Install

```
$ pip install
```

## How to run

### api

```
$ penguin_judge api -c config.ini
```
### worker server

sudo is required for run containers(docker).

```
$ penguin_judge worker -c config.ini (if you belong to a docker group)
$ sudo penguin_judge worker -c config.ini (otherwise)
```

## for developer information

developerの皆様には、pipenvを使った仮想環境をオススメいたします。

### Additional Requirement
- pipenv

### How to build develop env

```
$ pipenv --python 3.7
$ pipenv install --dev
$ pipenv shell
$ pip install -e .
```

これで（多分）動く環境は一応できます。  
注意点として、workerは`docker.sock`に接続する必要があるためworkerを実行するユーザをdockerグループ等に所属させるなどが必要です。
