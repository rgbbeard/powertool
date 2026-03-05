#!/usr/bin/python

from typing import Optional, Any, Dict, List, Union
import os
from os import system
from os.path import dirname, realpath
from re import sub
import json

BASE = dirname(__file__)
REQSFILE = f"{BASE}/requirements.json"


def get_path(from_filename: str, path_format: str = "unix"):
    curdir = ""

    if path_format == "unix":
        curdir = realpath(from_filename).replace("\\", "/")
        curdir = curdir.split("/")
        curdir.pop()
        curdir = "/".join(curdir)

    elif path_format in ("nt", "windows", "win"):
        curdir = curdir.split("\\")
        curdir.pop()
        curdir = "\\".join(curdir)

    return curdir


def is_empty(val: Any) -> bool:
    return val is None or val.strip() == "" or len(val) == 0


def sprintf(target: str, *replacements: Union[str, int, float]):
    for x, r in enumerate(replacements):
        target = sub(f"{{%{x}%}}", str(r), target)
    return target


def array_clear(
    target: Optional[Union[dict, list]], 
    check_values: bool = True,
    maintain_index: bool = False
) -> Union[Dict[Any, Any], List[Any]]:
    result = {} if maintain_index else []

    if target is not None:
        if isinstance(target, dict):
            iterator = target.items()
        elif isinstance(target, list):
            iterator = enumerate(target)
        else:
            raise TypeError("Input must be a dict or list")

        for index, value in iterator:
            if (check_values and not is_empty(value)) or (not check_values and index):
                item = value if check_values else index
                if maintain_index:
                    result[index] = item
                else:
                    result.append(item)

    return result


def printerr(message: str):
    print(f"\n❌  {message}")


def printinf(message: str):
    print(f"\nℹ️  {message}")


def printalr(message: str):
    print(f"\n⚠️  {message}")


def printsuc(message: str):
    print(f"\n✅  {message}")


def get_requirements():
    global REQSFILE

    reqs = {}

    with open(REQSFILE, "r") as data:
        reqs = json.load(data)

    return reqs


def try_install(module_name: str):
    reqs = get_requirements()

    command = reqs[module_name]["command"]

    print(f"Executing {command}...\n")
    try:
        system(command)
    except Exception as e:
        printerr(str(e))
        exit()

    print("Restart the console to see the changes")
    exit()


def import_module_error(module_name: str):
    reqs = get_requirements()

    url = reqs[module_name]["url"]

    printalr(f"Package {module_name} is required\n")

    response = input("Would you like to install it now? (yes/no) ")
    response = response.strip().lower()

    if response.startsWith("y"):
        try_install(module_name)
    elif response.startsWith("n"):
        print(f"See {url} for more details\n")
    exit()


def exec_exit():
    print("Okay, bye")
    exit()
