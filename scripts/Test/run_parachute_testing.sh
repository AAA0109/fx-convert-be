#!/bin/bash

while true; do
    echo "*****************************"
    echo "Updating code..."
    echo "*****************************"
    cd /home/pangea/sites/hedgedesk_dashboard/
    git pull

    echo "*****************************"
    echo "Count the number of files that would be copied or updated"
    echo "*****************************"

    count=$(gsutil -m rsync -r -n gs://bucket-dashboard-dev-pangea-io/parachute-testing/input /home/pangea/parachute-testing/input 2>&1 | grep 'Would copy' | wc -l)
    echo "*****************************"
    echo "$count files would be created or updated."
    echo "*****************************"

    if [ "$count" -gt 0 ]; then
        echo "*****************************"
        echo "Starting sync from bucket to local directory"
        echo "*****************************"
        start_time=$(date +%s)
        gsutil -m rsync -r -d gs://bucket-dashboard-dev-pangea-io/parachute-testing/input /home/pangea/parachute-testing/input
        gsutil -m rsync -r -d gs://bucket-dashboard-dev-pangea-io/parachute-testing/output /home/pangea/parachute-testing/output
        end_time=$(date +%s)
        echo "*****************************"
        echo "Sync completed, copied files from bucket to local directory in $(( (end_time - start_time) / 60 )) minutes"
        echo "*****************************"

        echo "*****************************"
        echo "Starting to setup the ENV"
        echo "*****************************"
        CONDA_BASE=$(conda info --base)
        source "$CONDA_BASE/etc/profile.d/conda.sh"
        conda activate hd_dash
        echo "*****************************"
        echo "Setup completed"
        echo "*****************************"

        echo "*****************************"
        echo "Starting to run the script"
        echo "*****************************"
        cd /home/pangea/parachute-testing/input
        start_time=$(date +%s)
        for file in *.csv; do
            echo "*****************************"
            echo "Processing $file..."
            echo "*****************************"

            declare -a pids=() # Array to keep track of child PIDs
            while IFS= read -r line; do
                modified_line=${line//,/" "}
                IFS=' ' read -r -a array <<< "$modified_line"
                data_path="${array[2]}"
                company_to_run="${array[3]}"
                mkdir -p "$data_path/logs"

                echo -e "\n\n"
                echo "*****************************"
                echo -e "Running... scripts/Test/Script_Parachute_Statistics.py \n"
                echo -e "$modified_line -- $data_path/logs/${company_to_run}__python.log \n"
                echo "*****************************"
                echo -e "\n\n"

                (
                    cd /home/pangea/sites/hedgedesk_dashboard/
                    python scripts/Test/Script_Parachute_Statistics.py $modified_line > "$data_path/logs/${company_to_run}__python.log" 2>&1
                ) &
                pids+=($!) # Store PID of the last background process
            done < <(tail -n +2 "$file") # This skips the first line of each CSV file

            mv $file ${file}.txt

            # Wait for all background processes to finish
            for pid in "${pids[@]}"; do
                wait $pid
            done
            unset pids # Clear the PID array before processing the next file

            echo "*****************************"
            echo "Starting sync from output directory to bucket"
            echo "*****************************"
            start_time_rsync=$(date +%s)
            gsutil -m rsync -r -d /home/pangea/parachute-testing/output gs://bucket-dashboard-dev-pangea-io/parachute-testing/output
            end_time_rsync=$(date +%s)
            echo "*****************************"
            echo "Sync completed, copied files from local directory to bucket in $(( (end_time_rsync - start_time_rsync) / 60 )) minutes"
            echo "*****************************"
        done

        end_time=$(date +%s)
        echo "*****************************"
        echo "Script completed in $((end_time - start_time)) seconds"
        echo "*****************************"

        echo "*****************************"
        echo "Starting sync from output directory to bucket"
        echo "*****************************"
        start_time_rsync=$(date +%s)
        gsutil -m rsync -r -d /home/pangea/parachute-testing/input gs://bucket-dashboard-dev-pangea-io/parachute-testing/input
        end_time_rsync=$(date +%s)
        echo "*****************************"
        echo "Sync completed, copied files from local directory to bucket in $(( (end_time_rsync - start_time_rsync) / 60 )) minutes"
        echo "*****************************"

    else
        echo "*****************************"
        echo "Going to sleep for 5 minutes."
        echo "*****************************"

        # Sleep for 5 minutes
        sleep 300
    fi
done
