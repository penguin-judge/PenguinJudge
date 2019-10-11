from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

def picked_up():
    messages = ["test"]
    return "test"

@app.route('/')
def index():
    title = "test"
    message = picked_up()
    return render_template('index.html',message=message, title=title)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port="8080")
