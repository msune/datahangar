#!/usr/bin/python3
import json
import re
from jinja2 import Environment, FileSystemLoader
import os, sys
import requests

sys.path.append("/etc/datahangar/")
from dh_conf_parser_lib import *

DH_CONF_FOLDER="/etc/datahangar/"
DRY_RUN=False

def submit_ingestion_task(name, pipeline, cols, template):
    #Generate and add KAFKA secrets
    data = {
        'kafkaDbIngestionTopic': pipeline["kafka.dbIngestionTopic"],
        'dbTableName': pipeline["dbTableName"],
        'druid_cols': cols
    }
    spec = template.render(data)
    print(f"Spec (JSON pre-credentials):\n{spec}")
    spec = spec.replace("__KAFKA_USERNAME__", os.environ.get('KAFKA_USERNAME'))
    spec = spec.replace("__KAFKA_PASSWORD__", os.environ.get('KAFKA_PASSWORD'))

    #Submit
    url = "http://druid-cluster-coordinators:8088/druid/indexer/v1/supervisor"
    headers = {'Content-Type': 'application/json'}
    print(f"Attempting to submit '{name}' to {url}...")
    if not DRY_RUN:
        response = requests.post(url, headers=headers, data=spec)
        if response.status_code != 200:
            raise Exception(f"ERROR({response.status_code}): submitting ingestion task: {response.text}")

if __name__ == "__main__":
    pipelines=get_pipelines()

    template = Environment(loader=FileSystemLoader('.')).get_template('kafka_ingest_spec.json.j2')
    for name, pipeline in pipelines.items():
        #Ignore disabled pipelines
        if not pipeline["enabled"]:
            print(f"WARNING: pipeline '{pipeline}' is disabled")
            continue

        cols = get_db_cols("druid", pipeline)

        print(f"Generating and submitting '{name}' ingestion task...")
        submit_ingestion_task(name, pipeline, cols, template)
