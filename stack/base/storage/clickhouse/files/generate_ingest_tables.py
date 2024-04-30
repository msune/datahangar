#!/usr/bin/python3
import json
import re
from jinja2 import Environment, FileSystemLoader
import os, sys
import subprocess

sys.path.append("/etc/datahangar/")
from dh_conf_parser_lib import *

DH_CONF_FOLDER="/etc/datahangar/"
DRY_RUN=False

def gen_ingest_tables(name, pipeline, cols, template):
    #Generate and add KAFKA secrets
    data = {
        'kafkaDbIngestionTopic': pipeline["kafka.dbIngestionTopic"],
        'dbTableName': pipeline["dbTableName"],
        'clickhouse_cols': cols
    }
    return template.render(data)

if __name__ == "__main__":
    pipelines=get_pipelines()

    file_content=""
    template = Environment(loader=FileSystemLoader('/tmp/conf')).get_template('create_tables_script.sql.j2')
    for name, pipeline in pipelines.items():
        #Ignore disabled pipelines
        if not pipeline["enabled"]:
            print(f"WARNING: pipeline '{pipeline}' is disabled")
            continue

        cols = get_db_cols("clickhouse", pipeline)

        print(f"Generating '{name}' ingestion tables...")
        file_content=file_content+gen_ingest_tables(name, pipeline, cols, template)

    #Create tmp file
    with open("/tmp/create_tables_script.sql", 'w') as f:
        f.write(file_content)

    print("Executing: \n"+file_content)
    subprocess.run(["clickhouse-client", "-h", "clickhouse-headless-service", "--queries-file", "/tmp/create_tables_script.sql"])
