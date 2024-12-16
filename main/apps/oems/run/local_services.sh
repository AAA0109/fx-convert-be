#!/bin/bash

if [ $# -lt 1 ]; then
	echo "USAGE: <app-dir>"
	exit 1
fi

APP_DIR=$1
cd $APP_DIR

BIN="python -u -q"

$BIN manage.py runoms --oms-id TEST_PAYMENT_OMS1 --timeout 1.0 &
$BIN manage.py runems --ems-id TEST_RFQ1 --ems-type RFQ --timeout 1.0 &
$BIN manage.py runems --ems-id TEST_CORPAY1 --ems-type CORPAY --timeout 1.0 &
$BIN manage.py runems --ems-id TEST_MP_RFQ1 --ems-type RFQ_MP --timeout 1.0 &
$BIN manage.py runems --ems-id TEST_CORPAY_MP1 --ems-type CORPAY_MP --timeout 1.0 &

wait

