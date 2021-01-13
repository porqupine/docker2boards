#Copyright 2021 Stoytcho Stoytchev, licensed under the MIT License.
import argparse
import json
import os
import subprocess
import sys

from pip._vendor.urllib3.exceptions import NewConnectionError


def getContextNameAndHost(contexts):
    contextMap = {}
    for context in contexts:
        info = subprocess.run(['docker', 'context', 'inspect', context],
                              capture_output=True, text=True).stdout
        data = json.loads(info)
        contextMap[data[0]["Name"]] = data[0]["Endpoints"]["docker"]["Host"]
    return contextMap


def createContextEntry(name, host):
    # docker context create <name> --docker= "host=<host>"
    hostArg = "host=" + host
    cmd = 'docker context create ' + name + ' --docker="' + hostArg + '"'
    print(cmd)
    os.system(cmd)
    return host


def updateContextEntry(name, host):
    # docker context update <name> --docker="host=<host>"
    hostArg = "host=" + host
    cmd = 'docker context update ' + name + ' --docker="' + hostArg + '"'
    print(cmd)
    os.system(cmd)
    return host


def useContext(name):
    cmd = 'docker context use ' + name
    print(cmd)
    os.system(cmd+" 1>/dev/null")


def compose(name, host, yaml):
    useContext(name)
    cmd = "docker-compose -f " + yaml + " up -d"
    print(cmd)
    out = os.system(cmd + " 2>/dev/null")
    if (out != 0):
        print(
            f"Error on compose for host {host}. \n"
            f"This is most likely because {host} is not running a docker daemon\n")
    else:
        print(f"Successful compose for {name} - {host}\n")


def init_argparse() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage="%(prog)s [OPTION] [FILE]...",
        description="Push Docker images to a group of ports",
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"{parser.prog} version 1.0.0"
    )
    parser.add_argument("files", nargs="*")
    return parser


def main() -> None:
    parser = init_argparse()
    args = parser.parse_args()
    if not args.files:
        print("Error : At least one configuration file is required.")
        exit(1)

    # store context to return to when done
    currentContext = subprocess.run(['docker', 'context', 'show'], capture_output=True,
                                    text=True).stdout.strip()

    print(f"Storing current context {currentContext}\n")
    # docker context fetching - so we know what ports/names we've got going.
    contexts = subprocess.run(['docker', 'context', 'list', '-q'],
                              capture_output=True, text=True).stdout.strip().split('\n')
    contextMap = getContextNameAndHost(contexts)

    for file in args.files:
        try:
            handle = open(file, 'r')
            data = json.load(handle)
            for entry in data:
                name = entry.get('name')
                host = entry.get('host')
                yaml = entry.get('yaml')
                try:
                    print(f"Processing entry -- {name}, {host}, {yaml}")
                    existingHost = contextMap[name]
                    if not (existingHost == host):
                        contextMap[name] = updateContextEntry(name, host)
                except KeyError:
                    contextMap[name] = createContextEntry(name, host)

                compose(name, host, yaml)
        except (FileNotFoundError, IsADirectoryError, NewConnectionError) as err:
            print(f"{parser.prog}: {file}: {err.strerror}", file=sys.stderr)
        finally:
            print(f"Restoring original context {currentContext}")
            useContext(currentContext)


if __name__ == "__main__":
    main()
