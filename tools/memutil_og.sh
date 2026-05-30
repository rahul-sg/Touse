#!/bin/bash

usage() {
    echo "usage: ${progname} <process>"
    exit 1
}
progname=`basename $0`
process=$1
if [ -z "${process}" ]; then
    usage
fi
pid=`ps axww | grep -w ${process} | head -1 | awk '{print $1}'`
echo "PID: ${pid}"
if [ -z "${pid}" ]; then
    echo "${progname}: no PID found for ${process}"
    exit 1
fi
while [ 1 ]; do
    memusage_curr=`top -l 1 -o mem -O +rsize | grep ${pid} | awk '{ print $8 }'`
    echo `date`: ${memusage_curr}
    sleep 5
done
