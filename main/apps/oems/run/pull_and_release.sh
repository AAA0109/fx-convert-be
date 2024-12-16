#!/bin/bash
set -e
set -i

PWD=`pwd`

sudo systemctl stop oms_backend1
sudo systemctl stop ems_corpay1
sudo systemctl stop ems_rfq1

cd ~/app/hedgedesk_dashboard
git pull

# conda activate deploy
# pip install -r requirements/base.txt

echo "ready to restart"

sudo systemctl start oms_backend1
sudo systemctl start ems_corpay1
sudo systemctl start ems_rfq1

cd $PWD
