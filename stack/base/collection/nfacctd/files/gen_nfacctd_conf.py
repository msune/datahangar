#!/usr/bin/python3
import json
import re
from typing import Optional
from jinja2 import Environment, FileSystemLoader
import sys, os
import requests

TEMPLATE_FOLDER=os.path.dirname(__file__)

def gen_nfacctd_conf(out_folder: str, conf: dict) -> None:
    """Generate nfacctd configuration file"""
    env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))
    template = env.get_template('./nfacctd.conf.j2')

    config_data = {
        'conf' : conf,
    }

    with open(os.path.join(out_folder, 'nfacctd.conf'), 'w') as f:
        f.write(template.render(config_data))

def gen_librdkafka_conf(out_folder: str) -> None:
    """Generate nfacctd configuration file"""
    env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))
    template = env.get_template('./librdkafka.conf.j2')

    config_data = {
        'kafka_user' : os.environ.get("KAFKA_USERNAME"),
        'kafka_pwd' : os.environ.get("KAFKA_PASSWORD"),
    }

    with open(os.path.join(out_folder, 'librdkafka.conf'), 'w') as f:
        f.write(template.render(config_data))

def main(conf_folder: str, pmacct_conf_folder: str) -> None:
    sys.path.append(conf_folder)
    sys.path.append(conf_folder+"/lib/")
    from dh_conf import datahangar_load_conf

    conf = datahangar_load_conf(conf_folder)
    gen_nfacctd_conf(pmacct_conf_folder, conf)
    gen_librdkafka_conf(pmacct_conf_folder)

if __name__ == '__main__':
    if len(sys.argv) != 3 and len(sys.argv) != 1:
        raise Exception("Wrong number of params")

    conf_folder = sys.argv[1] if len(sys.argv) == 3 else '/etc/datahangar/'
    pmacct_conf_folder = sys.argv[2] if len(sys.argv) == 3 else '/etc/pmacct/'

    main(conf_folder, pmacct_conf_folder)
