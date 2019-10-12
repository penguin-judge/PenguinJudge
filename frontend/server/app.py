from flask import Flask, render_template, request, redirect, url_for
import sys
sys.path.append('../../backend/db/model')
from model import *
import json

app = Flask(__name__, static_folder="../client/")

@app.route('/')
def index():
    return "Penguin Judge"

@app.route('/admin/console/<filename>', methods=['GET'])
def get_admin_console(filename):
    return app.send_static_file('admin/'+filename)

@app.route('/console/<filename>', methods=['GET'])
def get_user_console(filename):
    return app.send_static_file('user/'+filename)

@app.route('/admin/users', methods=['GET'])
def get_user_list():
    configure()
    users = []
    with transaction() as s:
        users = s.query(User).all()
        user_list_data = {}
        for user in users:
            user_list_data[user.id] = {}
            user_list_data[user.id]['name'] = user.name
            user_list_data[user.id]['salt'] = str(user.salt)
            user_list_data[user.id]['password'] = str(user.password)
            user_list_data[user.id]['created'] = \
                user.created.strftime('%Y/%m/%d %H:%M:%S')
    return json.dumps(user_list_data)

if __name__ == '__main__':
    app.run(host='192.168.56.105',port="8080")
