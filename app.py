from flask import Flask, request, jsonify
from flask_cors import CORS
from celery import Celery
import os

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

# Configure Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Import the Celery tasks
from celery_worker import run_simulation

@app.route('/simulate-lab1', methods=['POST'])
def simulate():
    data = request.json
    task = run_simulation.apply_async(args=[data])
    return jsonify({"task_id": task.id}), 202

@app.route('/results/<task_id>', methods=['GET'])
def get_results(task_id):
    task = run_simulation.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'result': task.result
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
