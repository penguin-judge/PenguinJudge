from argparse import ArgumentParser
import pickle
import sys

import pika


def main():
    parser = ArgumentParser()
    parser.add_argument('ContestID', type=str)
    parser.add_argument('ProblemID', type=str)
    parser.add_argument(
        'SubmissionID', type=int, nargs='+')
    parser.add_argument(
        '--url', help='RabbitMQ URL',
        default='amqp://guest:guest@localhost:5672/')
    args = parser.parse_args()

    conn = pika.BlockingConnection(pika.URLParameters(args.url))
    ch = conn.channel()
    ch.queue_declare(queue='judge_queue')
    for sid in args.SubmissionID:
        ch.basic_publish(
            exchange='', routing_key='judge_queue', body=pickle.dumps(
                (args.ContestID, args.ProblemID, sid)))
    ch.close()
    conn.close()


if __name__ == '__main__':
    main()
