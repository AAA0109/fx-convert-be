#!/bin/bash

echo "Starting git pull..."
if git pull; then
    echo "Git pull successful..."

    echo "Installing pip packages..."
    if pip install -r requirements/production.txt; then
        echo "Pip packages installed successfully..."
    else
        echo "Failed to install pip packages..."
    fi

    echo "systemctl daemon-reload..."
    if sudo systemctl daemon-reload; then
        echo "systemctl daemon-reload restart successful..."
    else
        echo "systemctl daemon-reload failed..."
    fi

    echo "Restarting celery..."
    sudo mkdir -p /var/run/celery
    sudo chown pangea /var/run/celery
    sudo chmod 755 /var/run/celery

    sudo mkdir -p /var/log/celery
    sudo chown pangea /var/log/celery
    sudo chmod 755 /var/log/celery
    if sudo systemctl restart celery; then
        echo "Celery restart successful..."
    else
        echo "Celery restart failed..."
    fi

    echo "Restarting celerybeat..."
    if sudo systemctl restart celerybeat; then
        echo "Celerybeat restart successful..."
    else
        echo "Celerybeat restart failed..."
    fi

    echo "Restarting celeryflower..."
    if sudo systemctl restart celeryflower; then
        echo "Celeryflower restart successful..."
    else
        echo "Celeryflower restart failed..."
    fi

    echo "Status of celery..."
    sudo systemctl status celery --no-pager

    echo "Status of celerybeat..."
    sudo systemctl status celerybeat --no-pager

    echo "Status of celeryflower..."
    sudo systemctl status celeryflower --no-pager
else
    echo "Git pull failed..."
fi
echo "Exiting..."
