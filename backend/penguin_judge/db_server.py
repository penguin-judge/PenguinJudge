import json

import pika  # type: ignore

from penguin_judge.models import (
    transaction, Submission, TestCase, JudgeResult)
from penguin_judge.mq import get_mq_conn_params


def callback(ch: pika.channel.Channel,
             method: pika.spec.Basic.Return,
             properties: pika.spec.BasicProperties,
             body: bytes) -> None:

    message = json.loads(body)

    print("Ready for judge")
    print(message)
    with transaction() as s:
        connection = pika.BlockingConnection(get_mq_conn_params())
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


def main() -> None:
    connection = pika.BlockingConnection(get_mq_conn_params())
    channel = connection.channel()
    channel.queue_declare(queue='judge_queue')
    channel.basic_consume(queue='judge_queue',
                          on_message_callback=callback, auto_ack=True)
    print("Start PenguinJudge db server")

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Shutdown PenguinJudge db server")
        channel.close()
        connection.close()
