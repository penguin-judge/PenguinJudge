from argparse import ArgumentParser, Namespace
import datetime
import json
import os
import sys

import pika

script_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_path + '/../../')
from model.model import *

def callback(ch : pika.channel.Channel,
             method : pika.spec.Basic.Return,
             properties : pika.spec.BasicProperties,
             body : bytes ) -> None:
    
    message = json.loads(body)

    print("Ready for judge")
    print(message)
    configure(host=Args.hostdb, port=Args.portdb)
    with transaction() as s:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=Args.hostmq, port=Args.portmq))
        channel = connection.channel()
        channel.queue_declare(queue='worker_queue')

        submission = s.query(Submission).\
                filter(Submission.contest_id == message['contest_id']).\
                filter(Submission.problem_id == message['problem_id']).\
                filter(Submission.id == message['submission_id']).\
                filter(Submission.user_id == message['user_id']).\
                all()
        
        if len(submission) != 1:
            return
        
        submission = submission[0]

        testcases = s.query(TestCase).\
                    filter(TestCase.contest_id == submission.contest_id).\
                    filter(TestCase.problem_id == submission.problem_id).\
                    all()
        for test in testcases:
            result = JudgeResult()
            result.contest_id = test.contest_id
            result.problem_id = test.problem_id
            result.submission_id = submission.id
            result.test_id = test.id
            s.add(result)
        
        channel.basic_publish(exchange='', 
                        routing_key='worker_queue', 
                        body=json.dumps(message))
        
        channel.close()
        connection.close()
    
    print('judge queue pushed')
        

def get_server_option() -> Namespace:
    argparser = ArgumentParser()
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

def main() -> None:
    global Args

    Args = get_server_option()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=Args.hostmq, port=Args.portmq))
    channel = connection.channel()
    channel.queue_declare(queue='judge_queue')
    channel.basic_consume(
       queue='judge_queue', on_message_callback=callback, auto_ack=True)
    
    print("Start PenguinJudge db server")
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Shutdown PenguinJudge db server")
        channel.close()
        connection.close()

if __name__ == "__main__":
    main()
    
