import argparse
import pika
from concurrent.futures import ProcessPoolExecutor
from run_judge_server import Run

def get_server_option() -> argparse.Namespace:
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-t', '--maxthread', type=int,
                            default=1,
                            help='The number of thread')
    argparser.add_argument('-pmq', '--portmq', type=int,
                            default=5672,
                            help='The port number of rabbitmq')
    argparser.add_argument('-hmq', '--hostmq', type=str,
                            default="127.0.0.1",
                            help='The hostname of rabbitmq')
    argparser.add_argument('-pdb', '--portdb', type=int,
                            default=5672,
                            help='The port number of DB')
    argparser.add_argument('-hdb', '--hostdb', type=str,
                            default="127.0.0.1",
                            help='The hostname of DB')
    return argparser.parse_args()

def run_judge(body):
    print("judge container start")
    Run(Args.hostdb, Args.portdb, body)
    print("judge container end")

def callback(ch, method, properties, body):
    Executor.submit(run_judge(body))
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main() -> None:
    global Args
    Args = get_server_option()
    global Executor
    Executor = ProcessPoolExecutor(max_workers=Args.maxthread)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=Args.hostmq,
                                    port=Args.portmq)
    )
    channel = connection.channel()
    channel.queue_declare(queue='worker_queue')

    channel.basic_qos(prefetch_count=Args.maxthread)
    channel.basic_consume(queue='worker_queue', 
                            on_message_callback=callback)

    print("Start worker server...")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("The channel closing...")
        channel.close()
        print("The connection closing...")
        connection.close()
        print("The process is shutdown...")
        Executor.shutdown

if __name__ == "__main__":
    main()
