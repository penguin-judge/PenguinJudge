from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import Callable, Dict

import pika  # type: ignore

from penguin_judge.models import configure, config as db_config
from penguin_judge.mq import get_mq_conn_params
from penguin_judge.run_container import run


def configure_db(config: Dict[str, str], f: Callable) -> None:
    configure(**config)
    f()


def callback(
        executor: ProcessPoolExecutor,
        ch: pika.channel.Channel,
        method: pika.spec.Basic.Return,
        properties: pika.spec.BasicProperties,
        body: bytes) -> None:
    executor.submit(configure_db, db_config, partial(run, body))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def main(max_processes: int) -> None:
    executor = ProcessPoolExecutor(max_workers=max_processes)
    connection = pika.BlockingConnection(get_mq_conn_params())
    channel = connection.channel()
    channel.queue_declare(queue='worker_queue')
    channel.basic_qos(prefetch_count=max_processes)
    channel.basic_consume(queue='worker_queue',
                          on_message_callback=partial(callback, executor))

    print("Start PenguinJudge worker server")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Shutdown PenguinJudge worker server")
        channel.close()
        connection.close()
        executor.shutdown
