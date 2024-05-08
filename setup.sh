#!/bin/bash

# Colors
NOTIFY_GREEN='\033[0;32m'
NOTIFY_RED='\033[0;31m'
NOTIFY_YELLOW='\033[1;33m'
NOTIFY_WHITE='\033[0;37m'
NOTIFY_RESET='\033[0m'

j_notify() {
    type=$1
    message=$2

    case $type in
        0)
            echo -e "[  ${NOTIFY_GREEN}OK${NOTIFY_RESET}  ] ${message}"
            ;;
        1)

            echo -e "[${NOTIFY_RED}FAILED${NOTIFY_RESET}] ${message}"
            ;;

        2)
            echo -e "[ ${NOTIFY_WHITE}INFO${NOTIFY_RESET} ] ${message}"
            ;;

        3)
            echo -e "${NOTIFY_GREEN}${message}${NOTIFY_RESET}\n─────────────────────────────────────────────────────\nNote: ${WHITE}$3${RESET}"
            ;;

        4)
            echo -e "[ ${NOTIFY_YELLOW}NOTE${NOTIFY_RESET} ] ${message}"
            ;;


        *)
        echo -e "[${NOTIFY_RED}FAILED${NOTIFY_RESET}] Invalid Option Type"
        exit 1;;
    esac

}

PrintBanner() {
    # Prints a nice user banner for displaying events.
    # echo ${#1} # Determine Length of a String
    DASH=$(perl -se 'print "-" x $N' -- -N=${#1})
    echo -e "\n${DASH}\n${1}\n${DASH}"
}

WARNBanner() {
    # Prints a nice user banner for displaying events.
    # echo ${#1} # Determine Length of a String
    DASH=$(perl -se 'print "-" x $N' -- -N=${#1})
    echo -e "\n${DASH}\n${NOTIFY_RED}${1}${NOTIFY_RESET}\n${DASH}"
}

move_check() {
    file=$1
    dest=$2
    title=$3
    j_notify 2 "Preparing $title"
    if [ -f "$dest" ]; then
        j_notify 2 "$dest exists. Skipping..."
    else
        j_notify 2 "Moving $file"
        cp $file $dest
    fi
    if [ -f "$dest" ]; then
        j_notify 0 "$title complete"

    else
        j_notify 1 "$title failed"
    fi

}

move_dir() {
    file=$1
    dest=$2
    title=$3
    j_notify 2 "Preparing $title"
    cp -r $file $dest
    if [ -d "$dest" ]; then
        j_notify 0 "$title complete"

    else
        j_notify 1 "$title failed"
    fi

}

create_dir() {
    if [ -d "$1" ]; then
        j_notify 2 "$1 detected."
    else
        mkdir -p "$1"
        j_notify 0 "Created: $1"
    fi
}

create_structure() {
    j_notify 2 "Creating Structure"
    create_dir conversion
    create_dir wheels
    create_dir src
    create_dir dev_test_data
    create_dir dev_test_reports
    j_notify 0 "Structure Complete"
}

install_sdk() {
    j_notify 2 "Installing Hyperscience SDK"
    sleep 1
    pip install setup_files/flows_sdk-1.4.0-py3-none-any.whl

    j_notify 2 "Checking Hyperscience SDK"
    result=$(pip freeze | grep "flows")
    if [[ "$result" == *"flow"* ]]; then
        j_notify 0 "Hyperscience SDK installed"
    else
        j_notify 1 "SDK failed"
        exit 1
    fi
}

set_builder_params() {
    local FILE="conversion/builder.py"
    rm $FILE

    move_check "setup_files/builder.py" $FILE "builder file"

    uuid=$(uuidgen)
    j_notify 3 "Created uuid" "$uuid"

    j_notify 2 "Setting uuid" "$uuid"
    sed -i "s/474c5392-0ea5-4a92-a972-0dadc37b4030/$uuid/g" $FILE
    j_notify 0 "Set uuid"

    echo -n "Project name (no spaces): "
    read proj
    sed -i "s/DVA_R5/$proj/g" $FILE
    j_notify 0 "Builder.py Setup complete"


}

ask_builder_params() {
    PrintBanner "NOTICE"
    echo "The builder.py for HS will now be reconfigured"
    echo "This will require a new GUID and name for the project"
    WARNBanner "WARNING"
    echo "This will overwrite the builder file"
    read -p "Do you want to proceed? (yes/no) " yn

    case $yn in 
        yes|y )
        echo ""
        j_notify 0 "Reconfiguring HS builder"
        set_builder_params
        ;;
        no|n ) 
        j_notify 0 "skipping HS builder"
        ;;
        * )
        j_notify 1 "Invalid Response"
        ;;
    esac
}

set_bashrc() {
    if [ -f "~/.bashrc" ]; then
        file="~/.bashrc"
    else
        file="~/.bash_profile"
    fi


    local BUILD="pushd $PWD/conversion > /dev/null && python builder.py; popd > /dev/null"
    local TEST="pushd $PWD > /dev/null && python test_rig.py; popd > /dev/null"

    echo "alias build='$BUILD'" > $file


}

ask_setup_sh() {
    PrintBanner "NOTICE"
    echo "Preparing to Setup the bashrc file"
    read -p "Do you want to proceed? (yes/no) " yn

    case $yn in 
        yes|y )
        echo ""
        j_notify 0 "Reconfiguring bashrc"
        set_bashrc
        ;;
        no|n ) 
        j_notify 0 "skipping bashrc"
        ;;
        * )
        j_notify 1 "Invalid Response"
        ;;
    esac
}


PrintBanner "Setting up HyperScience Dev Environment V35"

create_structure

move_check "setup_files/builder.py" "conversion/builder.py" "builder file"
move_check "setup_files/main.py" "conversion/main.py" "main file"
move_check "setup_files/download.sh" "wheels/download.sh" "wheel downloader"
move_check "setup_files/requirements.txt" "./requirements.txt" "requirements"
move_check "setup_files/test_rig.py" "./test_rig.py" "test rig"
move_check "setup_files/document_lookup.py" "src/document_lookup.py" "document lookup"
move_dir "setup_files/HS_templates" "conversion/HS_templates" "HS Templates"
move_dir "setup_files/reporting" "./reporting" "Reporting"


# install_sdk
ask_builder_params
ask_setup_sh