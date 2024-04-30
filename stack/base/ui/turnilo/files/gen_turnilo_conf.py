#!/usr/bin/python3
import json
import re
from jinja2 import Environment, FileSystemLoader
import sys, os
import requests

sys.path.append("/etc/datahangar/")
from dh_conf_parser_lib import *

if __name__ == "__main__":
    pipelines=get_pipelines()

    template = Environment(loader=FileSystemLoader('/tmp/conf')).get_template('turnilo_conf.yaml.j2')

    data_cubes = {}
    for name, pipeline in pipelines.items():
        if not pipeline["enabled"]:
            print(f"WARNING: pipeline '{pipeline}' is disabled")
            continue
        cols = get_db_cols("druid", pipeline)
        data_cubes[name] = {}
        data_cubes[name]["db_table_name"] = pipeline["dbTableName"]
        data_cubes[name]["description"] = pipeline["description"]
        data_cubes[name]["cols"] = cols

    with open("/turnilo_config.yaml", 'w') as f:
        f.write(template.render({"data_cubes" : data_cubes}))
