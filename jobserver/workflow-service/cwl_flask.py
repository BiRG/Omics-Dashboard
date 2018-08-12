from flask import Flask, Response, request, redirect, jsonify
import subprocess
import tempfile
import json
import yaml
import signal
import threading
import time
import copy
import requests
import os
from datetime import datetime

app = Flask(__name__)

jobs_lock = threading.Lock()
jobs = []
OMICSSERVER = os.environ['OMICSSERVER'] if 'OMICSSERVER' in os.environ else 'localhost:8080'
TMPDIR = f'{os.environ["DATADIR"]}/tmp' if 'DATADIR' in os.environ else '/tmp'
log_file_name = f'{os.environ["DATADIR"]}/logs/jobserver.log'


def log_error(e):
    with open(log_file_name, 'a+') as log_file:
        log_file.write(f'{datetime.now().replace(microsecond=0).isoformat(" ")}: {str(e)}\n\n')


def log_exception(status, e):
    with open(log_file_name, 'a+') as log_file:
        log_file.write(f'{datetime.now().replace(microsecond=0).isoformat(" ")} [{status}]: {str(e)}\n')


# handle any exception thrown by a datamanip function
# this is used for the restful api only
def handle_exception(e):
    log_exception(500, e)
    return jsonify({'message': str(e)}), 500


class Job(threading.Thread):
    def __init__(self, job_id, path, input_obj, token='', data_type='collection', owner=-1, name=''):
        super(Job, self).__init__()
        if not name:
            self.name = f'Job {job_id}'
        self.job_id = job_id
        self.path = path
        self.input_obj = input_obj
        self.owner = owner
        self.token = token
        self.data_type = data_type
        self.update_lock = threading.Lock()
        self.begin()

    def begin(self):
        log_handle, self.log_name = tempfile.mkstemp()
        with self.update_lock:
            self.outdir = f'{TMPDIR}/{self.token}'
            self.proc = subprocess.Popen(['cwl-runner', self.path, '-'],
                                         stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=log_handle,
                                         close_fds=True,
                                         cwd=self.outdir)
            self.status = {
                'id': self.job_id,
                'name': self.name,
                'owner': self.owner,
                'run': self.path,
                'state': 'Running',
                'input': json.loads(self.input_obj),
                'log': None,
                'output': None}

    def run(self):
        self.stdout_data, self.stderr_data = self.proc.communicate(self.input_obj)
        if self.proc.returncode == 0:
            out_obj = yaml.load(self.stdout_data)
            # with self.update_lock:
            self.status['state'] = 'Success'
            self.status['output'] = out_obj
            with open(self.log_name, 'r') as log_file:
                self.status['log'] = log_file.read()
            # send cleanup request to omics server
            # print(f'finalize request:\ntoken{self.token}')
            print('finalize request:')
            res = requests.post(f'{OMICSSERVER}/api/finalize',
                                headers={'Authorization': self.token},
                                json=self.status.copy(),
                                params={'data_type': self.data_type})
            print(f'status {res.status}')

        else:
            # with self.update_lock:
            self.status['state'] = 'Failed'
            log_error(str(log_spooler(self.job_id)))
            # failures are not cleaned up for debug purposes

    def get_status(self):
        # with self.update_lock:
        return self.status.copy()

    def cancel(self):
        if self.status['state'] == 'Running':
            self.proc.send_signal(signal.SIGQUIT)
            # with self.update_lock:
            self.status['state'] = 'Canceled'

    def pause(self):
        if self.status['state'] == 'Running':
            self.proc.send_signal(signal.SIGTSTP)
            # with self.update_lock:
            self.status['state'] = 'Paused'

    def resume(self):
        if self.status['state'] == 'Paused':
            self.proc.send_signal(signal.SIGCONT)
            # with self.update_lock:
            self.status['state'] = 'Running'


@app.route('/run', methods=['POST'])
def run_workflow():
    try:
        path = request.args['wf']
        token = request.headers['Authorization']
        data_type = request.args['data_type']
        with jobs_lock:
            job_id = len(jobs)
            job = Job(job_id, path, request.stream.read(), token=token, data_type=data_type, owner=(request.args['owner'] if 'owner' in request.args else -1))
            job.start()
            jobs.append(job)
        return jsonify(job.get_status())
    except Exception as e:
        return handle_exception(e)


@app.route('/jobs/<int:job_id>', methods=['GET', 'POST'])
def job_control(job_id):
    try:
        with jobs_lock:
            job = jobs[job_id]
        if request.method == 'POST':
            action = request.args.get('action')
            if action:
                if action == 'cancel':
                    job.cancel()
                elif action == 'pause':
                    job.pause()
                elif action == 'resume':
                    job.resume()
        return jsonify(job.get_status())
    except Exception as e:
        return handle_exception(e)


def log_spooler(job):
    with open(job.log_name, 'r') as f:
        while True:
            r = f.read(4096)
            if r:
                yield r
            else:
                with job.update_lock:
                    if job.status['state'] != 'Running':
                        break
                time.sleep(1)


@app.route('/jobs/<int:job_id>/log', methods=['GET'])
def get_log(job_id):
    try:
        with jobs_lock:
            job = jobs[job_id]
        return Response(log_spooler(job), mimetype='text/plain')
    except Exception as e:
        return handle_exception(e)


@app.route('/jobs', methods=['GET'])
def get_jobs():
    try:
        with jobs_lock:
            jobs_copy = copy.copy(jobs)

        def spool(jc):
            yield '['
            first = True
            for j in jc:
                if first:
                    yield json.dumps(j.get_status(), indent=4)
                    first = False
                else:
                    yield ', ' + json.dumps(j.get_status(), indent=4)
            yield ']'
        return Response(spool(jobs_copy), mimetype='application/json')
    except Exception as e:
        return handle_exception(e)


if __name__ == '__main__':
    # omics_dashboard.debug = True
    app.run()
