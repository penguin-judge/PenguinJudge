import pika
import json

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='judge_queue')

message = {}
message['contest_id'] = '1'
message['problem_id'] = '1'
message['submission_id'] = 1
message['user_id'] = '1'

channel.basic_publish(exchange='', routing_key='judge_queue',
                      body=json.dumps(message))
print(" [x] Sent 'test!'")
connection.close()
