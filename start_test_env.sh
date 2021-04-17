#!/bin/sh
script_file=`readlink -f "$0"`
script_dir=`dirname "$script_file"`

docker-compose -f "$script_dir/docker-compose.yaml" up -d
