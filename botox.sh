#!/bin/sh
# A shell script replacement for the botox executable. Requires the following tools:
#
#      o ps
#      o grep
#      o awk
#      o kill

PROCESS="$1"

if [ "$PROCESS" ]
then
	echo "Usage: $0 <process name>"
	exit 1
fi

while [ 1 ]
do
	PID=`ps | grep "$PROCESS" | grep -v grep | awk '{print $1}'`
	if [ "$PID" != "" ]
	then
		kill -STOP $PID
		cat /proc/$PID/maps
		echo "PID: $PID"
		break
	fi
done
