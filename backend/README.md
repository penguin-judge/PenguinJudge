# software
- docker
- docker-py
- sqlalchemy
- psycopg2
- rabbitmq
- erlang
- pika

# How to run

## Configure

create config.ini with reference to config.ini.template.
`sqlalchemy.url` and `mq.url` must be specified.

## Install & Run

```
$ pip install
$ penguin_judge api -c config.ini
```

# How to run (obsolete)
- worker server
- sudo python3 /judge/backend/worker/admin_scripts/judge_worker_server.py

- db server
- sudo python3 /judge/backend/db/judge_db_server.py

