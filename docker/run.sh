#!/bin/bash
script_file=`readlink -f "$0"`
script_dir=`dirname "$script_file"`

default_image_name='arsoft-trac'
docker_image_name=''
docker_build_lsb_release=''
data_dir=''

function usage() {
	echo "Usage: $script_file [OPTIONS]"
	echo "OPTIONS:"
	echo "    -h, --help            shows this help"
	echo "    -v, --verbose         enable verbose output"
	echo ""
	echo "  LSB_RELEASE    name of the LSB release (e.g. bionic, centos7; default $docker_build_lsb_release)"
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
    '--data') data_dir="$1"; shift; ;;
    -*)
        echo "Unrecognized option $1" >&2
        exit 1
        ;;
    *)
        ;;
    esac
    shift
done

[ -z "$data_dir" ] && data_dir="$script_dir/../data"
[ ! -d "$data_dir" ] && mkdir "$data_dir"

docker_run "$default_image_name" -v "$data_dir:/home/trac/env" $@
