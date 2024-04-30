import json
import re

DH_CONF_FOLDER="/etc/datahangar/"

def __load_mappings():
    #Load mappings
    with open(DH_CONF_FOLDER+"datafields-db-type.json", "r") as f:
        return json.loads(f.read())

#Parse pipeline info (yeah, a pitty it is not in JSON already due to nfacctd not
#supporting python in the base container)
def __load_pipelines():
    pipeline_names=[]
    raw={}
    with open(DH_CONF_FOLDER+"datahangar.conf", "r") as f:
        for line in f.readlines():
            if re.match(r'^\s*#.*', line):
                #Ignore comments
                continue
            if not re.match(r'^\s*pipeline\..*', line):
                #Ignore garbage
                continue
            if ":" not in line:
                #Ignore garbage
                continue

            parts = line.split(":")
            val = parts[1].strip().rstrip("\n").strip('"')
            raw[parts[0]] = val
            if re.match(r'pipeline\..*\.enabled.*', parts[0]):
                pipeline_names.append(re.search(r'pipeline\.(.*?)\.enabled', parts[0])[1])

    #Post process
    pipelines = {}
    for name in pipeline_names:
        p = {}
        keys = ["enabled", "description", "dataProfiles", "dbTableName", "kafka.nfacctdOutputTopic", "kafka.dbIngestionTopic"]

        for key_ in keys:
            key = "pipeline."+name+"."+key_
            if key not in raw:
                raise Exception(f"ERROR: Could not find: {key} in configuration. Aborting!")
            p[key_] = raw[key].strip()
        pipelines[name] = p
    return pipelines

def __load_data_profile(data_profile):
    with open(DH_CONF_FOLDER+"data-profiles/"+data_profile, "r") as f:
        return f.read()

def get_pipelines():
    return __load_pipelines()

def get_db_cols(db_name, pipeline):
    cols={}
    mappings = __load_mappings()

    #Load all fields from profiles / raw
    fields = ""
    for profile in pipeline["dataProfiles"].split(","):
        profile = profile.strip() #Remove trailing or leading spaces
        if profile.startswith("net.raw."):
            field = profile.replace("net.raw.", "").strip()
            if field not in mappings:
                raise Exception(f"ERROR: Could not find mapping for field: {field} in fields 2 DB types JSON. Aborting!")
            cols[mappings[field]["kafka_id"]] = {
                    "type": mappings[field][db_name]["type"],
                    "title": mappings[field]["title"]
            }
            continue

        #Load profile from file
        fields = __load_data_profile(profile)
        for field in fields.split(","):
            field = field.strip()
            if field == "":
                continue
            if field not in mappings:
                raise Exception(f"ERROR: Could not find mapping for field: {field} in fields 2 DB types JSON. Aborting!")
            cols[mappings[field]["kafka_id"]] = {
                    "type": mappings[field][db_name]["type"],
                    "title": mappings[field]["title"]
            }
    return cols

if __name__ == "__main__":
    DH_CONF_FOLDER="./"
    pipelines = get_pipelines()
    for name, p in pipelines.items():
        print(f"Pipeline: {name}")
        druid_cols = get_db_cols("druid", p)
        print(druid_cols)
