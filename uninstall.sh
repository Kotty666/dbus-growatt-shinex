#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
SERVICE_NAME=$(basename $SCRIPT_DIR)


chmod a-x $SCRIPT_DIR/service/run

if [ -f /service/$SERVICE_NAME ]
then
        rm /service/$SERVICE_NAME
fi


pids=$(pgrep -f $SERVICE_NAME)
if [ ! -z "$pids" ]
then
  for pid in $pids
  do
    kill $pid
  done
fi

if [ -f '/data/rc.local' ]
then
  sed -i '/.*'$SERVICE_NAME'.*/d' /data/rc.local
fi
