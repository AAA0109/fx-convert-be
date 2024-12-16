#!/bin/sh

# ========================

function instance_status {
	local instance=$1
	local zone=$2
	gcloud compute instances describe $instance --zone=$zone --format="get(status)"
}

function start_instance {
	local instance=$1
	local zone=$2
	gcloud compute instances start $instance --zone=$zone
}

function stop_instance {
	local instance=$1
	local zone=$2
	gcloud compute instances stop $instance --zone=$zone
}

function resize_instance {
	local instance=$1
	local zone=$2
	local mt=$3
	stop_instance $instance $zone
	gcloud compute instances set-machine-type $instance --zone=$zone --machine-type=$mt
	start_instance $instance $zone
}

# ========================

