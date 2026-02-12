#!/bin/bash

# Configuration defaults
VENV_DIR=".venv.gdrive-get"
ENV_FILE=".env.gdrive-get"
MODELS_YAML_DRIVE_ID=""
DATASETS_YAML_DRIVE_ID=""

# Load Environment Variables from .env.gdrive-get
if [ -f "$ENV_FILE" ]; then
    # Read ignoring comments and empty lines
    # We use '|| [ -n "$key" ]' to handle the last line if it's missing a newline
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Ignore comments
        [[ "$key" =~ ^#.* ]] && continue
        # Ignore empty lines
        [[ -z "$key" ]] && continue

        # Remove quotes if present
        value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")

        # Set variable dynamically if it matches our expected keys or general config
        case "$key" in
            VENV_DIR) VENV_DIR="$value" ;;
            MODELS_YAML_DRIVE_ID) MODELS_YAML_DRIVE_ID="$value" ;;
            DATASETS_YAML_DRIVE_ID) DATASETS_YAML_DRIVE_ID="$value" ;;
        esac
    done < "$ENV_FILE"

else
    echo "Error: Environment file $ENV_FILE not found, generating one..."
    echo "Please edit the generated file to set your environment variables."
    echo "VENV_DIR=$VENV_DIR" > "$ENV_FILE"
    echo "MODELS_YAML_DRIVE_ID=" >> "$ENV_FILE"
    echo "DATASETS_YAML_DRIVE_ID=" >> "$ENV_FILE"
    exit 1
fi

# Activate Venv
PIP_EXE_WIN="$VENV_DIR/Scripts/pip.exe"
PYTHON_EXE_WIN="$VENV_DIR/Scripts/python.exe"
PIP_EXE_UNIX="$VENV_DIR/bin/pip"
PYTHON_EXE_UNIX="$VENV_DIR/bin/python"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment $VENV_DIR does not exist."
    echo "Please create it first via: python -m venv $VENV_DIR (or using third-party tools)"
    exit 1
fi

if [ -f "$PYTHON_EXE_WIN" ] && [ -f "$PIP_EXE_WIN" ]; then
    PYTHON_EXE="$PYTHON_EXE_WIN"
    PIP_EXE="$PIP_EXE_WIN"
elif [ -f "$PYTHON_EXE_UNIX" ] && [ -f "$PIP_EXE_UNIX" ]; then
    PYTHON_EXE="$PYTHON_EXE_UNIX"
    PIP_EXE="$PIP_EXE_UNIX"
else
    echo "Error: Python executable not found in $VENV_DIR."
    exit 1
fi

# Ensure dependencies (optional check, but good for robustness)
if ! "$PIP_EXE" show gdown > /dev/null 2>&1; then
    echo "gdown not found. Installing..."
    "$PIP_EXE" install gdown -q
fi
if ! "$PIP_EXE" show PyYAML > /dev/null 2>&1; then
    echo "PyYAML not found. Installing..."
    "$PIP_EXE" install PyYAML -q
fi

# Helper function to run python code
run_python() {
    "$PYTHON_EXE" -c "$1"
}

usage() {
    echo "Usage: $0 [OPTIONS] [name]"
    echo ""
    echo "Options:"
    echo "  -m, --model       Operate on Models"
    echo "  -d, --dataset     Operate on Datasets"
    echo "  -ls, --list       List available files"
    echo "  -o, --output DIR  Specify output file or directory"
    echo "  -x, --extract     Extract the downloaded file automatically"
    echo "  -h, --help        Show this help message and exit"
    echo ""
    echo "Examples:"
    echo "  $0 -m -ls"
    echo "  $0 --dataset my-dataset --output data/datasets/ --extract"
}

if [ $# -eq 0 ]; then
    usage
    exit 0
fi

# Parse Arguments
MODE=""
LIST=false
TARGET_NAME=""
OUTPUT_ARG=""
EXTRACT=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -m|--model)
            MODE="model"
            shift
            ;;
        -d|--dataset)
            MODE="dataset"
            shift
            ;;
        -ls|--list)
            LIST=true
            shift
            ;;
        -o|--output)
            OUTPUT_ARG="$2"
            shift 2
            ;;
        -x|--extract)
            EXTRACT=true
            shift
            ;;
        *)
            if [[ "$1" == -* ]]; then
                echo "Error: Unknown option: $1"
                usage
                exit 1
            fi
            TARGET_NAME="$1"
            shift
            ;;
    esac
done

if [ -z "$MODE" ]; then
    echo "Error: You must specify a mode (-m or -d)."
    usage
    exit 1
fi

if [ "$LIST" = false ] && [ -z "$TARGET_NAME" ]; then
    echo "Error: No target name specified."
    usage
    exit 1
fi

# Determine Drive ID
DRIVE_ID=""
if [ "$MODE" == "model" ]; then
    DRIVE_ID="$MODELS_YAML_DRIVE_ID"
elif [ "$MODE" == "dataset" ]; then
    DRIVE_ID="$DATASETS_YAML_DRIVE_ID"
fi

if [ -z "$DRIVE_ID" ]; then
    echo "Error: Values for $MODE Drive ID not found in $ENV_FILE"
    exit 1
fi

# Temp file for Python to write the final output path to
OUTPUT_PATH_FILE=".last_dl_path"

# Python script to Fetch Config, Parse, and Print/Download
# We verify logic inside python to handle complex YAML parsing safely
PYTHON_SCRIPT="
import sys
import tempfile
import os
import gdown
import yaml

drive_id = '$DRIVE_ID'
mode = '$MODE'
do_list = '$LIST'
target_name = '$TARGET_NAME'
output_arg = '$OUTPUT_ARG'
output_path_file = '$OUTPUT_PATH_FILE'

def get_metadata_entries(metadata):
    for key in ['models', 'datasets', 'files']:
        if key in metadata:
            return metadata[key]
    return None

try:
    # 1. Download metadata to temp
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.yaml', delete=False) as tmp:
        temp_path = tmp.name

    print(f'Fetching {mode} metadata...')
    url = f'https://drive.google.com/uc?id={drive_id}'
    # Fetch metadata
    gdown.download(url, temp_path, quiet=True, fuzzy=True)

    with open(temp_path, 'r') as f:
        metadata = yaml.safe_load(f)

    if os.path.exists(temp_path):
        os.remove(temp_path)

    entries = get_metadata_entries(metadata)
    if not entries:
        print('Error: no entries found in metadata')
        sys.exit(1)

    # Convert dict to list if needed
    if isinstance(entries, dict):
        # normalize to list of dicts with 'name'
        new_entries = []
        for k, v in entries.items():
            v['name'] = k
            new_entries.append(v)
        entries = new_entries

    # 2. Execute Action
    if do_list == 'true':
        print(f'\\nAvailable {mode}s:')
        for e in entries:
            name = e.get('name', 'Unknown')
            desc = e.get('description', e.get('desc', ''))
            print(f' - {name}: {desc}')

    elif target_name:
        # Find target
        found = None
        for e in entries:
            if e.get('name') == target_name:
                found = e
                break

        if not found:
            print(f'Error: {target_name} not found in metadata.')
            sys.exit(1)

        file_id = found.get('id')
        default_output = found.get('output', found.get('name', target_name))

        # Determine final output path
        final_output = default_output
        if output_arg:
            if os.path.isdir(output_arg) or output_arg.endswith('/') or output_arg.endswith('\\\\\\\\'):
                os.makedirs(output_arg, exist_ok=True)
                final_output = os.path.join(output_arg, default_output)
            else:
                # Treat as file path override
                # Ensure parent dir exists
                parent_dir = os.path.dirname(os.path.abspath(output_arg))
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                final_output = output_arg

        if not file_id:
             print('Error: ID missing for item.')
             sys.exit(1)

        print(f'Downloading {target_name} -> {final_output}...')
        dl_url = f'https://drive.google.com/uc?id={file_id}'
        gdown.download(dl_url, final_output, quiet=False, fuzzy=True)

        # Write final path to temp file for Bash
        with open(output_path_file, 'w') as f:
            f.write(os.path.abspath(final_output))

except Exception as e:
    print(f'An error occurred: {e}')
    sys.exit(1)
"

# Execute the python logic
"$PYTHON_EXE" -c "$PYTHON_SCRIPT"
PY_EXIT_CODE=$?

# If Python succeeded and Unpack is requested
if [ $PY_EXIT_CODE -eq 0 ] && [ "$EXTRACT" = true ] && [ "$LIST" = false ]; then
    if [ -f "$OUTPUT_PATH_FILE" ]; then
        DOWNLOADED_FILE=$(cat "$OUTPUT_PATH_FILE")

        if [ -f "$DOWNLOADED_FILE" ]; then
            # echo "Inspecting file type for extraction..."
            MIME_TYPE=$(file -b --mime-type "$DOWNLOADED_FILE")
            DIR_NAME=$(dirname "$DOWNLOADED_FILE")

            # echo "Detected MIME type: $MIME_TYPE"

            case "$MIME_TYPE" in
                application/zip)
                    echo "Unzipping $DOWNLOADED_FILE..."
                    # Check if unzip exists
                    if command -v unzip >/dev/null 2>&1; then
                         unzip -o "$DOWNLOADED_FILE" -d "$DIR_NAME"
                    else
                         echo "Error: 'unzip' command not found."
                    fi
                    ;;
                application/x-tar|application/gzip|application/x-gzip|application/x-compressed-tar)
                    echo "Extracting tarball $DOWNLOADED_FILE..."
                    tar -xf "$DOWNLOADED_FILE" -C "$DIR_NAME"
                    ;;
                *)
                    echo "Warning: storage type '$MIME_TYPE' not supported for auto-extraction."
                    ;;
            esac
        fi
    fi
fi

# Cleanup temp file
if [ -f "$OUTPUT_PATH_FILE" ]; then
    rm "$OUTPUT_PATH_FILE"
fi

exit $PY_EXIT_CODE
