#!/usr/bin/python3
import json
import re
from jinja2 import Environment, FileSystemLoader
import os, sys
import requests
import pprint

DH_CONF_FOLDER="/etc/datahangar/"
DRY_RUN=False

sys.path.append(DH_CONF_FOLDER)
sys.path.append(DH_CONF_FOLDER+"/lib/")
from dh_conf import datahangar_load_conf, datahangar_pipeline_db_get_cols

def submit_ingestion_task(conf: dict, name:str, pipeline: dict) -> None:
    #Generate and add KAFKA secrets
    data = {
        'kafkaDbIngestionTopic': pipeline["kafka"]["topic-db-ingestion"],
        'dbTableName': pipeline["db"]["table-name"],
        'druid_cols': datahangar_pipeline_db_get_cols(conf, pipeline, "druid")
    }

    template = Environment(loader=FileSystemLoader('/tmp/')).get_template('kafka_ingest_spec.json.j2')
    spec = template.render(data)
    print(f"Spec (JSON pre-credentials):\n{spec}")

    #Doing this just to not print the credentials in the log...
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
    conf = datahangar_load_conf(DH_CONF_FOLDER)

    for name, pipeline in conf["pipelines"].items():
        #Ignore disabled pipelines
        if "disabled" in pipeline and pipeline["disabled"]:
            print(f"WARNING: pipeline '{name}' is disabled")
            continue

        print(f"Generating and submitting '{name}' ingestion task...")
        submit_ingestion_task(conf, name, pipeline)
