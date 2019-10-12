from concurrent.futures import ProcessPoolExecutor
from functools import partial

import pika  # type: ignore

from penguin_judge.mq import get_mq_conn_params
from penguin_judge.run_container import run


def callback(
        executor: ProcessPoolExecutor,
        ch: pika.channel.Channel,
        method: pika.spec.Basic.Return,
        properties: pika.spec.BasicProperties,
        body: bytes) -> None:
    executor.submit(run, body)
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
