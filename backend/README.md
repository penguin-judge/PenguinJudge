## Requirement

- python3
- postgres
- rabbitmq
- docker

## Configure

create config.ini with reference to config.ini.template.
`sqlalchemy.url` and `mq.url` must be specified.

## Install

```
$ pip install
```

## How to run

### api and db server

```
$ penguin_judge api -c config.ini
$ penguin_judge db -c config.ini
```
### worker server

sudo is required for run containers(docker).

```
$ sudo penguin_judge api -c config.ini
```

## for developer information