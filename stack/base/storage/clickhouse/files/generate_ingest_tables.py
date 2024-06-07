#!/usr/bin/python3
import json
import re
from jinja2 import Environment, FileSystemLoader
import os, sys
import subprocess

DH_CONF_FOLDER="/etc/datahangar/"
DRY_RUN=False

sys.path.append(DH_CONF_FOLDER)
sys.path.append(DH_CONF_FOLDER+"/lib/")
from dh_conf import datahangar_load_conf, datahangar_pipeline_db_get_cols

def gen_ingest_tables(conf, name, pipeline, template):
    #Generate and add KAFKA secrets
    data = {
        'kafkaDbIngestionTopic': pipeline["kafka"]["topic-db-ingestion"],
        'dbTableName': pipeline["db"]["table-name"],
        'clickhouse_cols': datahangar_pipeline_db_get_cols(conf, pipeline, "clickhouse")
    }
    return template.render(data)

if __name__ == "__main__":
    conf = datahangar_load_conf(DH_CONF_FOLDER)

    file_content=""
    template = Environment(loader=FileSystemLoader('/tmp/gen/')).get_template('create_tables_script.sql.j2')

    for name, pipeline in conf["pipelines"].items():
        #Ignore disabled pipelines
        if "disabled" in pipeline and pipeline["disabled"]:
            print(f"WARNING: pipeline '{name}' is disabled")
            continue

        print(f"Generating '{name}' ingestion tables...")
        file_content=file_content+gen_ingest_tables(conf, name, pipeline, template)

    #Create tmp file
    with open("/tmp/create_tables_script.sql", 'w') as f:
        f.write(file_content)

    print("Executing: \n"+file_content)
    subprocess.run(["clickhouse-client", "-h", "clickhouse-headless-service", "--queries-file", "/tmp/create_tables_script.sql"])
