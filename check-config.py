#!/usr/bin/python3
#
# USAGE
#
#    check-config.py
#
# DESCRIPTION
#
#   This script checks the consistency of the buildbot configuration.  It
#   verifies that all worker directories defined in `files/workers` are
#   referenced in the builder YAML configuration files located in
#   `files/builders`. It also checks if any workers referenced in the builder
#   configurations are missing from the `files/workers` directory.
#

import os
import sys
import yaml

def get_workers_from_yaml(builders_dir):
    """
    Reads all yaml files in the given directory and returns a set of worker names.
    """
    workers_from_yaml = set()
    for filename in os.listdir(builders_dir):
        if not (filename.endswith(".yml") or filename.endswith(".yaml")):
            continue

        filepath = os.path.join(builders_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                if not isinstance(data, list):
                    continue
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    if 'worker' in item:
                        workers_from_yaml.add(item['worker'])
                    if 'workers' in item and isinstance(item['workers'], list):
                        workers_from_yaml.update(item['workers'])
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {filename}: {e}", file=sys.stderr)
            continue

    if "dummy" in workers_from_yaml:
        workers_from_yaml.remove("dummy")
    return workers_from_yaml

def get_workers_from_fs(workers_dir):
    """
    Returns a set of worker names from the filesystem directory.
    """
    try:
        return set(os.listdir(workers_dir))
    except FileNotFoundError:
        print(f"Error: Workers directory not found at {workers_dir}", file=sys.stderr)
        sys.exit(1)

def report_results(workers_from_yaml, workers_from_fs):
    """
    Compares the two sets of workers and prints warnings or errors.
    Returns the exit code.
    """
    unreferenced_workers = workers_from_fs - workers_from_yaml
    missing_workers = workers_from_yaml - workers_from_fs
    exit_code = 0

    if unreferenced_workers:
        print("ERROR: The following workers are not referenced in any builder configuration:")
        for worker in sorted(list(unreferenced_workers)):
            print(worker)
        exit_code = 1

    if missing_workers:
        print("ERROR: The following workers are configured in builders but are missing from the workers directory:")
        for worker in sorted(list(missing_workers)):
            print(worker, file=sys.stderr)
        exit_code = 1

    return exit_code

def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    builders_dir = os.path.join(script_dir, "files", "builders")
    workers_dir = os.path.join(script_dir, "files", "workers")

    workers_from_yaml = get_workers_from_yaml(builders_dir)
    workers_from_fs = get_workers_from_fs(workers_dir)
    exit_code = report_results(workers_from_yaml, workers_from_fs)

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
