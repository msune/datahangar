import json
import re
import sys, os
import requests
from urllib.parse import urlencode

DH_CONF_FOLDER="/etc/datahangar/"
DASHBOARD_FOLDER="/tmp/dashboards/"
DASHBOARD_CUSTOM_FOLDER="/tmp/custom_dashboards/"
BACKEND_SERVICE="backend-service"
BACKEND_PORT=80
DEFAULT_PATH = "rest/turnilo/dashboards/"

def create_dashboard(host, port, dashboard):
    url = f"http://{host}:{port}/{DEFAULT_PATH}"

    query = {
        "dataCube": dashboard["dataCube"],
        "shortName": dashboard["shortName"]
    }

    #First check if there is already a dashboard, and update
    query_url = urlencode(query)
    res = requests.get(url+"?"+query_url)
    if res.status_code != 200:
        raise Exception(f"UNKNOWN error: {res}")

    dashs = res.json()
    if len(dashs) > 1:
        raise Exception(f"CORRUPTED state: more than one dashboard for unique constraint shortName+dataCube {res}")
    elif len(dashs) == 1:
        #Update
        if "id" not in dashs[0]:
            raise Exception(f"CORRUPTED state: no ID for existing dashboard {res}")

        id_ = dashs[0]["id"]
        print(f"Updating dashboard {id_}: '{dashboard}'")
        url = f"{url}{id_}"
        res = requests.put(url, json=dashboard)
        op = "update"
    else:
        #Create
        print(f"Creating dashboard: '{dashboard}'")
        res = requests.post(url, json=dashboard)
        op = "create"

    if res.status_code != 200:
        raise Exception(f"UNKNOWN error during op='{op}': {res}")

def create_dashboards_in_file(file_path):
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        print(f"WARNING: unable to open '{file_path}'")
        return

    print(f"Attempting to create/update dashboards in '{file_path}'...")
    with open(file_path) as f:
        dashboards = json.load(f)
        for dash in dashboards:
            create_dashboard(BACKEND_SERVICE, BACKEND_PORT, dash)

if __name__ == "__main__":
    sys.path.append(DH_CONF_FOLDER)
    sys.path.append(DH_CONF_FOLDER+"/lib/")
    from dh_conf import datahangar_load_conf, datahangar_pipeline_db_get_cols

    conf = datahangar_load_conf("/etc/datahangar/")

    # First load (default) profiles dashboards
    for name, pipeline in conf["pipelines"].items():
        if "disabled" in pipeline and pipeline["disabled"]:
            print(f"WARNING: pipeline '{name}' is disabled")
            continue
        for profile in pipeline["data-profiles"]:
            if profile.startswith("net.raw"):
                continue
            create_dashboards_in_file(DASHBOARD_FOLDER+profile+".json")

    # Then custom
    if os.path.exists(DASHBOARD_CUSTOM_FOLDER) and os.path.isdir(DASHBOARD_CUSTOM_FOLDER):
        for filename in os.listdir(DASHBOARD_CUSTOM_FOLDER):
            with open(DASHBOARD_CUSTOM_FOLDER+filename) as f:
                create_dashboards_in_file(DASHBOARD_CUSTOM_FOLDER + filename)
    else:
        print(f"NOTE: no custom folder")
