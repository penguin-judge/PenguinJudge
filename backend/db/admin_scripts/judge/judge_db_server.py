import pika
import json
from argparse import ArgumentParser
from model.model import *
import datetime
import json

def callback(ch, method, properties, body):
    message = json.loads(body)
    print(message)
    configure()
    with transaction() as s:

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=Args.host, port=Args.port))
        channel = connection.channel()
        channel.queue_declare(queue='worker_queue')

        submission = s.query(Submission).\
                filter(Submission.contest_id == message['contest_id']).\
                filter(Submission.problem_id == message['problem_id']).\
                filter(Submission.id == message['submission_id']).\
                filter(Submission.user_id == message['user_id']).\
                all()
        for submit in submission:
            testcases = s.query(TestCase).\
                        filter(TestCase.contest_id == submit.contest_id).\
                        filter(TestCase.problem_id == submit.problem_id).\
                        all()
            for test in testcases:
                result = JudgeResult()
                result.contest_id = test.contest_id
                result.problem_id = test.problem_id
                result.submission_id = submit.id
                result.test_id = test.id
                s.add(result)
        
        channel.basic_publish(exchange='', 
                        routing_key='worker_queue', 
                        body=json.dumps(message))
        
        channel.close()
        connection.close()
        

def get_server_option():
    argparser = ArgumentParser()
    argparser.add_argument('-p', '--port', type=int,
                            default=5672,
                            help='The port number of rabbitmq')
    argparser.add_argument('-o', '--host', type=str,
                            default="localhost",
                            help='The hostname address of rabbitmq')
    return argparser.parse_args()

def main():

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=Args.host, port=Args.port))
    channel = connection.channel()
    channel.queue_declare(queue='judge_queue')
    channel.basic_consume(
       queue='judge_queue', on_message_callback=callback, auto_ack=True)
    
    print(' [*] Waiting for messages. To exit press CTRL+C')
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("The channel closing...")
        channel.close()
        print("The connection closing...")
        connection.close()

if __name__ == "__main__":
    global Args
    Args = get_server_option()
    print("The rabbitmq status")
    print("address is : " + Args.host)
    print("port is : " + str(Args.port))
    main()
    
