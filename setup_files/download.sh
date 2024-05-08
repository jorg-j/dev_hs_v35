function download_whl() {
    pip download --python-version 3.7 --platform=manylinux2014_x86_64 --only-binary=:all: $1
}


download_whl opencv-python-headless
download_whl openpyxl==3.1.2
download_whl Pillow==9.4.0
download_whl phonenumbers==8.13.26
download_whl pylint==2.16.2
download_whl PyPDF2==3.0.1
download_whl python-Levenshtein==0.20.9
download_whl python-dateutil==2.8.2
download_whl requests==2.31.0
download_whl tzdata==2023.3
download_whl pytz==2023.3.post1