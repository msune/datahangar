#!/usr/bin/python3
import typer
import subprocess
import os

E_MSG="ERROR: "

#Typer stuff
ctl = typer.Typer()

DH_NAMESPACE="datahangar-stack"
DEFAULT_KCTL=(os.getenv("KCTL") or "kubectl")

#Reusable arg/opt objects
COMPONENT_OPT = typer.Option(None, "--component", "-c", help="Component")
PATH_OPT = typer.Option("./", "--path", "-p", help="DataHangar root folder")
KCTL_OPT = typer.Option(DEFAULT_KCTL, "--kubectl", "-k", help="kubectl command")

def _check_dh_root_folder(path: str):
    if not os.path.isdir(path+"/stack/base") or not os.path.isdir(path+"/stack/overlays"):
        raise typer.Exit(E_MSG + os.path.abspath(path)+" is not a valid datahangar root folder")
def _kctl_exec(_kctl: str, cmd):
    kctl=_kctl.strip().split(" ")

    try:
        proc = subprocess.run(kctl + cmd)
    except Exception as e:
        raise typer.Exit(E_MSG + "could not execute '" + str(kctl+cmd) +"'. Exception:"+str(e))
    return proc

def _invoke_kustomize_component(path: str, op: str, component: str, kctl: str):
    #Should never happen
    if component == None:
        raise typer.Exit(E_MSG + "Invalid None component")

    ov_kfile=path+"/stack/overlays/"+component+"/kustomization"
    if not os.path.isfile(ov_kfile+".yaml") and not os.path.isfile(ov_kfile+".yml"):
        #Use base only
        ov_kfile=path+"/stack/base/"+component+"/kustomization"
        if not os.path.isfile(ov_kfile+".yaml") and not os.path.isfile(ov_kfile+".yml"):
            raise typer.Exit(E_MSG + "Could not find Kustomize file at: " + ov_kfile +".y*ml. Invalid component?")
        kpath = path+"/stack/base/"+component
    else:
        kpath = path+"/stack/overlay/"+component

    cmd = [op, "-k", kpath]
    proc = _kctl_exec(kctl, cmd)
    if proc.returncode != 0:
        raise typer.Exit(E_MSG + "failed executing '" + kctl+str(cmd))

def _find_kustomizations(root_dir):
    folders_with_kustomization = []
    for root, dirs, files in os.walk(root_dir):
        if ("kustomization.yaml" or "kustomization.yml") in files:
            folders_with_kustomization.append(os.path.relpath(root, root_dir))
    return folders_with_kustomization

def _invoke_kustomize(path: str, _op: str, component : str, kctl: str):
    #Check if base and overlay folder exists
    _check_dh_root_folder(path)

    #Sanitize
    op = _op.strip().lstrip().lower()
    if not op == "apply" and not op == "delete":
        raise typer.Exit(E_MSG + "invalid op: " + _op)

    if component != None:
        _invoke_kustomize_component(path, op, component, kctl)
        return

    # Find all components
    components = _find_kustomizations(path+"/stack/base/")
    for c_it in components:
        _invoke_kustomize_component(path, op, c_it, kctl)

def _create_ns(kctl: str):
    cmd = ["create", "namespace", DH_NAMESPACE]
    proc = _kctl_exec(kctl, cmd)
    if proc.returncode != 0:
        raise typer.Exit(E_MSG + "failed executing '" + kctl+str(cmd))

@ctl.command("generate-secrets")
def gen_secrets(path : str = PATH_OPT, component : str = COMPONENT_OPT, kctl: str = KCTL_OPT):
    print("Hello: I am generating secrets...")

@ctl.command("deploy")
def deploy(path : str = PATH_OPT, component : str = COMPONENT_OPT, kctl: str = KCTL_OPT):
    _create_ns(kctl)
    _invoke_kustomize(path, "apply", component, kctl)

@ctl.command("undeploy")
def undeploy(path : str = PATH_OPT, component : str = COMPONENT_OPT, kctl: str = KCTL_OPT):
    _invoke_kustomize(path, "delete", component, kctl)

if __name__ == "__main__":
    ctl()
