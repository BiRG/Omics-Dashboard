import requests
import os
jobserver_url = os.environ['COMPUTESERVER']


# use this module to debug the jobserver via docker exec
def get_jobs():
    url = f'{jobserver_url}/jobs'
    return requests.get(url).json()


def get_job(job_id):
    url = f'{jobserver_url}/jobs/{job_id}'
    return requests.get(url).json()


def get_job_log(job_id):
    url = f'{jobserver_url}/jobs/{job_id}/log'
    return requests.get(url).text


def cancel_job(job_id):
    url = f'{jobserver_url}/jobs/{job_id}?action=cancel'    
    return requests.post(url).json()


def pause_job(job_id):
    url = f'{jobserver_url}/jobs/{job_id}?action=pause'
    return requests.post(url).json()


def resume_job(job_id):
    url = f'{jobserver_url}/jobs/{job_id}?action=resume'
    return requests.post(url).json()

