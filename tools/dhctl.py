#!/usr/bin/python3
import typer
import subprocess
import os
import logging
import json
from typing_extensions import Annotated

E_MSG="ERROR:"
W_MSG="WARNING:"

COMPONENTS=[
    "conf/",
    "infra/zookeeper",
    "infra/postgresql",
    "infra/backend",
    "bus/kafka",
    "collection/nfacctd",
    "storage/db",
    "ui/frontend",
    "ui/turnilo"
]

#Typer stuff
ctl = typer.Typer(no_args_is_help=True)

DH_NAMESPACE="datahangar-stack"
DEFAULT_KCTL=(os.getenv("KCTL") or "kubectl")

#Reusable arg/opt objects
OVERLAY_ARG = typer.Argument(..., help="Overlay name")
COMPONENTS_OPT = typer.Option(None, "--components", "-c", help="Components [default: all]")
PATH_OPT = typer.Option("./", "--path", "-p", help="DataHangar root folder")
KCTL_OPT = typer.Option(DEFAULT_KCTL, "--kubectl", "-k", help="kubectl command")

"""
Core
"""
def _check_dh_root_folder(path: str):
    """
    Check that the path is a Datahangar root folder
    """
    if not os.path.isdir(path+"/stack/base") or not os.path.isdir(path+"/stack/overlays"):
        raise typer.Exit(E_MSG + os.path.abspath(path)+" is not a valid datahangar root folder")

def _kctl_exec(_kctl: str, cmd, debug_only: bool=True):
    """
    Execute a kubectl, and store the output.
    """
    kctl=_kctl.strip().split(" ")

    try:
        proc = subprocess.run(kctl + cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as e:
        raise typer.Exit("could not execute '" + str(kctl+cmd) +"'.\nException:\n"+str(e))
    logging.debug("[>] "+str(kctl+cmd))

    if not debug_only:
        logging.info(proc.stdout.decode())
    else:
        logging.debug(proc.stdout.decode())
    return proc

def _ns(kctl: str, op: str ):
    """
    create (idempotent) or delete a namespace
    """
    op_str = "Create" if op == "create" else "Delete"
    logging.debug(f"[{op_str}] Namespace '{DH_NAMESPACE}'")

    if op == "create":
        logging.debug(f"Checking if Namespace '{DH_NAMESPACE}' exists")
        if _kctl_exec(kctl, ["get", "namespace", DH_NAMESPACE]).returncode == 0:
            #NS exists
            logging.debug(f"Namespace '{DH_NAMESPACE}' exists... skipping creation.")
            return

    cmd = [op, "namespace", DH_NAMESPACE]
    proc = _kctl_exec(kctl, cmd)
    if proc.returncode != 0:
        raise typer.Exit(E_MSG + "failed executing '" + kctl+str(cmd))

def _invoke_kustomize(path: str, overlay: str, op: str, component: str, kctl: str):
    """
    Apply / delete Component Kustomize overlay
    """
    #Should never happen
    if component == None:
        raise typer.Exit(E_MSG + "Invalid None component")

    kpath = path+"/stack/overlays/"+overlay+"/"+component
    if not os.path.isdir(kpath):
        raise typer.Exit(E_MSG + "couldn't find component in '"+kpath+"'")

    cmd = [op, "-k", kpath]
    proc = _kctl_exec(kctl, cmd)
    if proc.returncode != 0:
        raise typer.Exit(E_MSG + "failed executing '" + kctl+str(cmd))

def _invoke_kustomize_components(path: str, overlay: str, op: str, components : str, kctl: str):
    """
    Apply / delete to a list of components or to ALL
    """
    if components == None:
        # Find all components
        components = COMPONENTS

    op_str = "Deploy" if op == "apply" else "Undeploy"
    for c_it in components:
        try:
            logging.debug(f"[{op_str}] "+str(c_it.lstrip("/")))
            _invoke_kustomize(path, overlay, op, c_it, kctl)
        except Exception as e:
            if op == "apply":
                raise e
            else:
                logging.warning(W_MSG + str(e))


"""
Status backend
"""
def _check_pods(kctl: str):
    proc = _kctl_exec(kctl, ["get", "pods", "-n", DH_NAMESPACE, "-o=json"], True)
    pods = json.loads(proc.stdout.decode('utf-8'))

    logging.debug(f"Checking Pods...")

    all_healthy = True
    for pod in pods['items']:
        namespace = pod['metadata']['namespace']
        name = pod['metadata']['name']
        phase = pod['status']['phase']
        conditions = pod['status'].get('conditions', [])
        owner_kind = pod['metadata']['ownerReferences'][0]['kind']
        owner_name = pod['metadata']['ownerReferences'][0]['name']

        if owner_kind == "Job":
            continue

        if phase != 'Running':
            logging.warning(f"{W_MSG} {owner_kind} '{owner_name}' Pod '{name}' in namespace '{namespace}' is not healthy (phase)")
            all_healthy = False
            continue

        ready = False
        for condition in conditions:
            if condition['type'] == 'Ready' and condition['status'] == 'True':
                ready = True
                break
        if not ready:
            logging.warning(f"{W_MSG} {owner_kind} '{owner_name}' Pod '{name}' in namespace '{namespace}' is not healthy (ready=False)")
            all_healthy = False
    return all_healthy

def _check_services(kctl: str):
    ns = DH_NAMESPACE
    proc = _kctl_exec(kctl, ["get", "services", "-n", ns, "-o=json"], True)
    services_info = json.loads(proc.stdout.decode('utf-8'))

    logging.debug(f"Checking Services...")

    all_healthy = True
    for service in services_info["items"]:
        service_name = service["metadata"]["name"]
        service_namespace = service["metadata"]["namespace"]

        # Run kubectl get endpoints command to get endpoints for the service
        proc = _kctl_exec(kctl, ["get", "endpoints", "-n", ns, service_name, "-o=json"], True)
        endpoints_info = json.loads(proc.stdout.decode('utf-8'))

        # Check if the service has at least one endpoint
        if not endpoints_info.get("subsets"):
            all_healthy = False
            logging.warning(f"{W_MSG} Service '{service_name}' in namespace '{ns}' is NOT healthy.")
    return all_healthy

def _get_job_last_log(kctl, job_name):
    ns = DH_NAMESPACE
    try:
        pod_name = _kctl_exec(kctl, ["get", "pods", "-n", ns, "--selector=job-name="+job_name, "--output=jsonpath='{.items[-1].metadata.name}'"]).stdout.decode('utf-8').strip('"').strip("'")
        return _kctl_exec(kctl, [ "-n", ns, "logs", pod_name]).stdout.decode('utf-8')
    except Exception as e:
        return "EXCEPTION recovering logs "+str(e)

def _check_jobs_completion(kctl: str):
    ns = DH_NAMESPACE
    proc = _kctl_exec(kctl, ["get", "jobs", "-n", ns, "-o=json"], True)
    jobs_info = json.loads(proc.stdout.decode('utf-8'))

    logging.debug(f"Checking Jobs...")

    all_healthy = True
    for job in jobs_info["items"]:
        job_status = job['status']
        job_name = job['metadata']['name']
        if "succeeded" not in job_status.keys() or job_status['succeeded'] == 0:
            logging.warning(f"{W_MSG} Job '{job_name}' in namespace '{ns}' has not completed ({job_status}).")
            jobs_last_log = _get_job_last_log(kctl, job_name)
            logging.warning(f"Last log:\n---\n {jobs_last_log}\n---\n")
            all_healthy = False

    return all_healthy

"""
Frontend commands
"""
@ctl.command("status")
def status(overlay: str = OVERLAY_ARG, path: str=PATH_OPT, components: str=COMPONENTS_OPT, kctl: str=KCTL_OPT):
    """
    Get status of a component or the whole stack
    """
    _check_dh_root_folder(path)
    logging.debug(f"Checking status of '{DH_NAMESPACE}'")

    pods = _check_pods(kctl)
    svcs = _check_services(kctl)
    jobs = _check_jobs_completion(kctl)

    if not pods or not svcs or not jobs:
        raise typer.Exit(f"{E_MSG} stack NOT healthy!")

@ctl.command("generate-secrets")
def gen_secrets(overlay: str = OVERLAY_ARG, path: str=PATH_OPT, components: str=COMPONENTS_OPT, kctl: str=KCTL_OPT):
    """
    Generate secrets
    """
    _check_dh_root_folder(path)
    logging.info("Hello: I am generating secrets...")

@ctl.command("deploy")
def deploy(overlay: str = OVERLAY_ARG, path: str = PATH_OPT, components: str = COMPONENTS_OPT, kctl: str = KCTL_OPT):
    """
    Deploy component(s) or the whole stack
    """
    _check_dh_root_folder(path)
    _ns(kctl, "create")
    _invoke_kustomize_components(path, overlay, "apply", components, kctl)

@ctl.command("undeploy")
def undeploy(overlay: str = OVERLAY_ARG, path: str = PATH_OPT, components: str = COMPONENTS_OPT, kctl: str = KCTL_OPT):
    """
    Undeploy component(s) or the whole stack
    """
    _check_dh_root_folder(path)
    _invoke_kustomize_components(path, overlay, "delete", components, kctl)
    try:
        _ns(kctl, "delete")
    except Exception as e:
        logging.warning(W_MSG+str(e))

@ctl.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v")):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(message)s", level=level)
    logging.debug("dhctl vX.Y")

if __name__ == '__main__':
    ctl()
