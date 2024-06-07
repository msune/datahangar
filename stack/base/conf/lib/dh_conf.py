import yaml
import os, sys
import argparse
import re
import pprint

def load_yaml(file_path: str):
    """Load a YAML file and return its contents."""
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

def merge_dicts(dict1: dict, dict2: dict):
    """Recursively merge two dictionaries."""
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1:
            dict1[key] = merge_dicts(dict1[key], value)
        else:
            dict1[key] = value
    return dict1

def __check_field(dict_, name, field):
    if field not in dict_:
        raise Exception(f"ERROR: missing '{field}' in '{name}'")

def __validate_and_transform(conf):
    __check_field(conf, "", "data")
    __check_field(conf["data"], "data", "fields")
    data = conf["data"]
    fields = data["fields"]
    if len(fields) == 0:
        raise Exception("ERROR: 'data.fields' has length == 0")

    #Validate that ALL fields have all mappings
    i = 0
    field_dict = {}
    for field in fields:
        __check_field(field, f"data.fields[{i}]", "title")
        __check_field(field, f"data.fields[{i}]", "nfacctd")
        __check_field(field["nfacctd"], f"data.fields[{i}].nfacctd", "name")
        __check_field(field, f"data.fields[{i}]", "kafka")
        __check_field(field["kafka"], f"data.fields[{i}].kafka", "name")
        __check_field(field, f"data.fields[{i}]", "druid")
        __check_field(field["druid"], f"data.fields[{i}].druid", "type")
        __check_field(field, f"data.fields[{i}]", "clickhouse")
        __check_field(field["clickhouse"], f"data.fields[{i}].clickhouse", "type")
        field_dict[field["nfacctd"]["name"]] = field
        i = i+1
    data["fields"] = field_dict

    #Check data profile sanity
    __check_field(conf["data"], "data", "profiles")
    profiles = data["profiles"]
    if len(fields) == 0:
        raise Exception("ERROR: 'data.profiles' has length == 0")
    i = 0
    data_profiles_dict = {}
    for profile in profiles:
        __check_field(profile, f"data.profiles[{i}]", "name")
        __check_field(profile, f"data.profiles[{i}]", "title")
        __check_field(profile, f"data.profiles[{i}]", "description")
        __check_field(profile, f"data.profiles[{i}]", "fields")
        fields = profile["fields"]
        if not isinstance(fields, list):
            raise Exception(f"ERROR: 'data.profiles[{i}].fields' is not a YAML array")
        if len(fields) == 0:
            raise Exception(f"ERROR: 'data.profiles[{i}].fields' has length == 0")

        profile_fields_dict = {}
        for field_name in profile["fields"]:
            if field_name not in data["fields"]:
                raise Exception(f"ERROR: unknown '' in 'data.profiles[{i}].fields'")
            profile_fields_dict[field_name] = True
        profile["fields"] = profile_fields_dict
        data_profiles_dict[profile["name"]] = profile
        i = i+1
    data["profiles"] = data_profiles_dict

    #Check pipelines sanity
    __check_field(conf, "", "pipelines")
    pipelines = conf["pipelines"]
    if len(pipelines) == 0:
        raise Exception("ERROR: 'data.pipelines' has length == 0")

    i = 0
    pipelines_dict={}
    for pipeline in pipelines:
        __check_field(pipeline, f"pipelines[{i}]", "name")
        __check_field(pipeline, f"pipelines[{i}]", "title")
        __check_field(pipeline, f"pipelines[{i}]", "description")
        __check_field(pipeline, f"pipelines[{i}]", "data-profiles")
        __check_field(pipeline, f"pipelines[{i}]", "kafka")
        __check_field(pipeline["kafka"], f"pipelines[{i}].kafka", "topic-nfacctd-out")
        __check_field(pipeline["kafka"], f"pipelines[{i}].kafka", "topic-db-ingestion")
        __check_field(pipeline, f"pipelines[{i}]", "db")
        __check_field(pipeline["db"], f"pipelines[{i}].db", "table-name")

        #Validate table name (SQL)
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', pipeline["db"]["table-name"]):
            raise Exception(f"ERROR: invalid characters on field 'table-name' in pipelines[{i}].db")

        profiles_dict = {}
        profiles_aggr_fields = []
        for profile in pipeline["data-profiles"]:
            if profile.startswith("net.raw."):
                raw_field = profile.replace("net.raw.", "").strip()
                if raw_field not in data["fields"]:
                    raise Exception(f"ERROR: unknown RAW field '{profile}' in pipelines[{i}].data-profiles. Missing field definition?")
                profiles_aggr_fields.append(raw_field)
            else:
                if profile not in data["profiles"]:
                    raise Exception(f"ERROR: unknown data-profile '{profile}' in pipelines[{i}].data-profiles")
                profiles_aggr_fields.extend(data["profiles"][profile]["fields"].keys())
            profiles_dict[profile] = True
            i = i+1
        pipeline["data-profiles"] = profiles_dict
        pipeline["data-profiles-aggr-fields"] = profiles_aggr_fields
        pipelines_dict[pipeline["name"]] = pipeline

    conf["pipelines"] = pipelines_dict
    return conf

def datahangar_pipeline_db_get_cols(conf: dict, pipeline: dict, db: str) -> dict:
    cols = {}
    fields = conf["data"]["fields"]
    for field_name in pipeline["data-profiles-aggr-fields"]:
        field = fields[field_name]
        cols[field["kafka"]["name"]] = {
            "type" : field[db]["type"],
            "title" : field["title"]
        }

    pprint.pprint(cols)
    return cols

def datahangar_load_conf(path: str):
    conf_files = ["data-fields.yaml", "data-profiles.yaml", "conf.yaml"]

    conf = {}
    for conf_file in conf_files:
        tmp = load_yaml(os.path.join(path, conf_file))
        merge_dicts(conf, tmp)
    return __validate_and_transform(conf)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise Exception("ERROR: invalid number of parameters (should be 1)")
    conf = datahangar_load_conf(sys.argv[1])
    import pprint
    pprint.pprint(conf, indent=4)
