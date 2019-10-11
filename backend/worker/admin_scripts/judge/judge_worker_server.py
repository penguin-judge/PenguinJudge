from argparse import ArgumentParser, Namespace
from concurrent.futures import ProcessPoolExecutor

import pika

from run_container import Run

def get_server_option() -> Namespace:
    argparser = ArgumentParser()
    argparser.add_argument('-t', '--maxprocess', type=int,
                            default=1,
                            help='The number of worker process')
    argparser.add_argument('-pmq', '--portmq', type=int,
                            default=5672,
                            help='The port number of rabbitmq')
    argparser.add_argument('-hmq', '--hostmq', type=str,
                            default="127.0.0.1",
                            help='The hostname of rabbitmq')
    argparser.add_argument('-pdb', '--portdb', type=str,
                            default='5432',
                            help='The port number of DB')
    argparser.add_argument('-hdb', '--hostdb', type=str,
                            default="127.0.0.1",
                            help='The hostname of DB')
    return argparser.parse_args()

def run_judge(body : bytes) -> None:
    Run(Args.hostdb, Args.portdb, body)

def callback(ch : pika.channel.Channel,
             method : pika.spec.Basic.Return,
             properties : pika.spec.BasicProperties,
             body : bytes ) -> None:
    Executor.submit(run_judge(body))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main() -> None:
    global Args
    global Executor
    
    Args = get_server_option()
    Executor = ProcessPoolExecutor(max_workers=Args.maxprocess)

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=Args.hostmq,
                                  port=Args.portmq)
    )
    channel = connection.channel()
    channel.queue_declare(queue='worker_queue')
    channel.basic_qos(prefetch_count=Args.maxprocess)
    channel.basic_consume(queue='worker_queue', 
                          on_message_callback=callback)

    print("Start PenguinJudge worker server")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Shutdown PenguinJudge worker server")
        channel.close()
        connection.close()
        Executor.shutdown

if __name__ == "__main__":
    main()
