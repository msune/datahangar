#!/usr/bin/python3
import json
import re
from jinja2 import Environment, FileSystemLoader
import sys, os
import requests

DH_CONF_FOLDER="/etc/datahangar/"

if __name__ == "__main__":
    sys.path.append(DH_CONF_FOLDER)
    sys.path.append(DH_CONF_FOLDER+"/lib/")
    from dh_conf import datahangar_load_conf, datahangar_pipeline_db_get_cols

    conf = datahangar_load_conf("/etc/datahangar/")
    data_cubes = {}
    for name, pipeline in conf["pipelines"].items():
        if "disabled" in pipeline and pipeline["disabled"]:
            print(f"WARNING: pipeline '{name}' is disabled")
            continue
        cols = datahangar_pipeline_db_get_cols(conf, pipeline, "druid")
        data_cubes[name] = {}
        data_cubes[name]["title"] = pipeline["title"]
        data_cubes[name]["description"] = pipeline["description"]
        data_cubes[name]["db_table_name"] = pipeline["db"]["table-name"]
        data_cubes[name]["cols"] = cols

    template = Environment(loader=FileSystemLoader('/tmp/')).get_template('turnilo_conf.yaml.j2')
    conf_file = template.render({"data_cubes" : data_cubes})
    with open("/etc/turnilo/config.yaml", 'w') as f:
        f.write(conf_file)
    print(f"Generated configuration file:\n")
    print(conf_file)
