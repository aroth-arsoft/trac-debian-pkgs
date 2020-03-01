#!/bin/bash
script_file=`readlink -f "$0"`
script_dir=`dirname "$script_file"`

default_image_name='arsoft-trac'
docker_image_name=''
docker_build_lsb_release=''
TRAC_ENV_DIR=''
clear_env=0

function usage() {
	echo "Usage: $script_file [OPTIONS]"
	echo "OPTIONS:"
	echo "    -h, --help            shows this help"
	echo "    -v, --verbose         enable verbose output"
	echo "    --env <dir>           use different trac environment (default: $TRAC_ENV_DIR)"
	echo "    --clear               clear trac environment"
	exit 0
}

function docker_run() {
    docker_image_name="$1"
    shift

    local build_args=''
    if [ -z "$docker_build_lsb_release" ]; then
        local tag="$docker_image_name:latest"
    else
        local tag="$docker_image_name:$docker_build_lsb_release"
    fi

    docker run --rm --name $docker_image_name --network host $@ $tag
}

got_lsb_rel=0

# parse command line arguments
while [ $# -ne 0 ]; do
    case "$1" in
    '-?'|'-h'|'--help') usage;;
    '-v'|'--verbose') verbose=1; ;;
    '--clear') clear_env=1; ;;
    '--env') TRAC_ENV_DIR="$1"; shift; ;;
    -*)
        echo "Unrecognized option $1" >&2
        exit 1
        ;;
    *)
        ;;
    esac
    shift
done

[ -z "$TRAC_ENV_DIR" ] && TRAC_ENV_DIR="$script_dir/../data"
if [ ! -d "$TRAC_ENV_DIR" ]; then
    mkdir "$TRAC_ENV_DIR"
fi

image_env=''
if [ $clear_env -ne 0 ] ;then
    image_env="$image_env -e TRAC_CLEAR_ENV=1"
fi

docker_run "$default_image_name" -v "$TRAC_ENV_DIR:/home/trac/env" $image_env $@
