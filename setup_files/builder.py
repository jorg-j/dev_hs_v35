import os
import sys
import subprocess
import shutil
from glob import glob
from datetime import datetime

file_paths = ["src", "reporting"]
document_exclusions = []

DOCSPLITTING = True

if DOCSPLITTING:
    FLOWUUID = "474c5392-0ea5-4a92-a972-0dadc37b4030"
    IDENTIFIER = "DVA_R5"
    FLOWTITLE = "DVA_R5"
else:
    # FLOWUUID = "02512b0d-16ba-4429-9072-2f300c863106"
    FLOWUUID = "474c5392-0ea5-4a92-a972-0dadc37b4030"
    IDENTIFIER = "DVA_R5"
    FLOWTITLE = "DVA_R5"


# maintain all imports across the project
imports = set()

# maintain all file content across the project
all_content = []


def setup():
    def check_dir(dirname):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, dirname)
        try:
            os.makedirs(file_path)
        except OSError as e:
            pass
    check_dir("artifacts")
    check_dir("build")



def manage_version_number():
    current_date = datetime.now().date()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "current_version.txt")

    try:
        with open(file_path, "r") as f:
            current_version = f.read()

        components = current_version.replace("\n", "").partition("_")

        c_version_date = datetime.strptime(components[0], "%Y%m%d").date()
        current_date = datetime.now().date()

        if c_version_date == current_date:
            c_build = int(components[2])
            c_version_date = current_date.strftime("%Y%m%d")
            build_num = c_build + 1
        else:
            build_num = 1
            c_version_date = current_date.strftime("%Y%m%d")
    except:
        c_version_date = current_date.strftime("%Y%m%d")
        build_num = 1

    version = f"{c_version_date}_{build_num}"

    with open(file_path, "w") as f:
        f.write(version)

    return version

def copy_artifacts(src):
    """
    Copies the required HS template to the build directory
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    dest_file = os.path.join(script_dir, "artifacts", src)
    src_template = os.path.join(script_dir, "build", src)
    shutil.copy(src_template, dest_file)

def get_imports(filename):
    """
    get all imports from a given file
    """
    temp_imports = set()
    with open(filename, "r", encoding="utf-8") as file:
        file_data = (row for row in file)
        only_imports = (
            row
            for row in file_data
            if row.startswith("import ") or row.startswith("from ")
        )
        cleaned_imports = (row for row in only_imports if "# block" not in row.lower())

        for i in cleaned_imports:
            temp_imports.add(i)
    return temp_imports


def generate_file_listing(file_paths):
    """
    Generator for all files within all paths
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)

    for file_path in file_paths:
        search = os.path.join(parent, file_path, "*.py")
        files = glob(search)
        files = (f for f in files if "test" not in f)
        files = (f for f in files if "dev_" not in f)
        files = (f for f in files if "boilerplate" not in f)
        files = (f for f in files if f not in document_exclusions)

        for f in files:
            yield f
        # yield [f for f in files]


def write_imports(imports):
    """
    Write all imports to disk
    Then sorts using isort
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    import_path = os.path.join(script_dir, "build", "imports.py")
    with open(import_path, "w+") as f:
        for im in imports:
            f.write(im)
    try:
        subprocess.check_output(["isort", "--version"])
    except:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "isort"])

    subprocess.check_call(["isort", import_path])


def write_content(all_content):
    """
    Write all file content to disk
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "build", "content.py")
    with open(file_path, "w+", encoding="utf-8") as f:
        for im in all_content:
            f.write(im)
            f.write("\n")


def copy_template(src, dest):
    """
    Copies the required HS template to the build directory
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    dest_file = os.path.join(script_dir, "build", dest)
    src_template = os.path.join(script_dir, "HS_templates", src)
    shutil.copy(src_template, dest_file)


def setup_templates(dist, test):
    """
    Copies the distribution and test templates
    to their required dir
    """
    copy_template(dist, "master.py")
    copy_template(test, "test_master.py")


def get_file_content(filename):
    """
    Gets the file content between SOF and EOF boundaries
    """
    start, end = 0, 0
    function_lines = []
    upper_boundary = "#### SOF"
    lower_boundary = "#### EOF"
    with open(filename, "r", encoding="utf-8") as f:
        data = f.read()
    lines = data.split("\n")

    for pos, line in enumerate(lines):
        if line.startswith(upper_boundary):
            start = pos + 1
        if line.startswith(lower_boundary):
            end = pos - 1
        if start != 0 and end != 0:
            lines_captured = [lines[j] for j in range(start, end + 1)]
            return lines_captured
    return []


def indent(data, amount):
    """
    Update the correct amount of indents
    """
    spaces = " " * amount
    x = "\n".join([f"{spaces}{x}" for x in data])
    return x.strip()


def file_replacement(filename, seek, replacement):
    """
    Open a given file in build and replace seek with replacement
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "build", filename)
    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(seek, replacement)
    data = data.replace("\n\n", "\n")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(data)


def insert_imports():
    """
    Update the master and test_master imports
    """
    seek = "#IMPORTS"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "build", "imports.py")

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.readlines()

    master_v = indent(data, 8)
    test_v = indent(data, 0)

    file_replacement("master.py", seek, master_v)
    file_replacement("test_master.py", seek, test_v)


def insert_content():
    """
    Update the master and test_master mainline code
    """
    seek = "#MAINLINE"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "build", "content.py")

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.readlines()

    master_v = indent(data, 8)
    test_v = indent(data, 4)

    file_replacement("master.py", seek, master_v)
    file_replacement("test_master.py", seek, test_v)

def insert_main_block():
    """
    Update the master and test_master mainblock code
    """
    seek = "#MAINBLOCK"

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "main.py")

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.readlines()

    master_v = indent(data, 8)
    test_v = indent(data, 4)

    file_replacement("master.py", seek, master_v)
    file_replacement("test_master.py", seek, test_v)


def apply_formatting(filename):
    """
    Write all imports to disk
    Then sorts using isort
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "build", filename)

    try:
        subprocess.check_output(["black", "--version"])
    except:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "black"])

    try:
        subprocess.run(["black", file_path], stdout=subprocess.PIPE, check=True)
    except:
        print(f"Black unable to run on: {file_path}")


def convert():
    """
    Convert the master.py into a master.json file
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "build", "master.py")
    out_path = os.path.join(script_dir, "build", "master.json")

    result = subprocess.run(["python", file_path], stdout=subprocess.PIPE, check=True)
    decoded = result.stdout.decode("utf-8")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(decoded.replace("\r", ""))


version = manage_version_number()

files = generate_file_listing(file_paths)

for filename in files:
    # for filename in file_set:
    # Build the imports for each file into the imports set
    current_imports = get_imports(filename)
    imports = imports | current_imports

    file_content = get_file_content(filename)
    all_content.extend(file_content)

setup()
write_imports(imports)
write_content(all_content)

setup_templates("docsplit.py", "docsplit_testing.py")

file_replacement("master.py", "#VERSION", version)
file_replacement("test_master.py", "#VERSION", version)

insert_imports()
insert_content()
insert_main_block()

file_replacement("master.py", "#FLOWUUID", FLOWUUID)
file_replacement("master.py", "#IDENTIFIER", IDENTIFIER)
file_replacement("master.py", "#FLOWTITLE", FLOWTITLE)

apply_formatting("test_master.py")

convert()


# Move the artifacts to the artifact generate
copy_artifacts("master.py")
copy_artifacts("master.json")
copy_artifacts("test_master.py")