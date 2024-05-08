import json
import os
import os.path as path
import shutil
import sys
from datetime import datetime
from glob import glob
from inspect import getsourcefile
import datetime

import conversion.artifacts.test_master as runcode

import memory_profiler as mem_profile

import cProfile
import pstats

current_dir = path.dirname(path.abspath(getsourcefile(lambda: 0)))
sys.path.insert(0, current_dir[: current_dir.rfind(path.sep)])

sys.path.pop(0)


def serialiser(data):
    if isinstance(data, dict):
        for key, value in data.items():
            data[key] = serialiser(value)
        return data
    elif isinstance(data, list):
        return [serialiser(item) for item in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data


def load_in_json(filename):
    try:
        with open(filename, "r") as f:
            data = f.read()
        data = data.replace("\n", "")
        data = json.loads(data)
    except (FileNotFoundError, json.JSONDecodeError, IndexError) as e:
        try:
            with open(filename, "r") as f:
                data = f.read()
            data = data.split('"code":')[0]
            data = data.replace("\n", "")
            data = data[:-5] + "}"

            data = json.loads(data)
        except (FileNotFoundError, json.JSONDecodeError, IndexError) as e:
            print(f"Error processing {filename}: {e}")
            quit()
    return data


def run_test():
    data_dir = os.path.join(os.getcwd(), "dev_test_data")
    manual_file = ""
    # manual_file = f"{data_dir}/1054.json"
    if manual_file:
        files = [manual_file]
    else:
        try:
            files = glob(f"{data_dir}/{sys.argv[1]}*.json")
        except:
            files = glob(f"{data_dir}/*.json")

    for file in files:
        print(file)
        data = load_in_json(file)

        document_data = data["document_data"]
        full_page_raw = data["full_page_raw"]
        doc_title_output = data["doc_title_output"]

        with cProfile.Profile() as pr:
            start_time = datetime.datetime.now()
            start_mem = (
                str(mem_profile.memory_usage()).replace("[", "").replace("]", "")
            )
            result, report_file = runcode._main_validation(
                document_data, full_page_raw, doc_title_output
            )

        stats = pstats.Stats(pr)
        stats.sort_stats(pstats.SortKey.TIME)
        stats.dump_stats(filename="output.prof")

        end_mem = str(mem_profile.memory_usage()).replace("[", "").replace("]", "")
        print(f"Memory (Start) {start_mem}")
        print(f"Memory (End) {end_mem}")
        print(f"Memory Delta {float(end_mem) - float(start_mem)}")
        print(datetime.datetime.now() - start_time)
        new_fullpath = os.path.join(
            os.getcwd(),
            "dev_test_reports",
            f'Submission_{document_data["submission"]["id"]}.xlsx',
        )
        try:
            shutil.move(report_file, new_fullpath)
        except:
            print("El Cooked")


if __name__ == "__main__":
    run_test()
