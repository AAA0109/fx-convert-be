#!/bin/bash -i

set -e

# source ~/.bashrc

readonly SYSTEM_BIN_DIR="/usr/local/bin"

function log {
	local readonly level="$1"
	local readonly message="$2"
	local readonly timestamp=$(date +"%Y-%m-%d %H:%M:%S")
	>&2 echo -e "$timestamp [$level] $message"
}

function has_command {
	[[ -n "$(caommand -v $1)" ]]
}

function start_systemd {
	log "INFO" $2
	sudo systemctl enable $1
	sudo systemctl start $1
}

function add_system_symlink {
	local readonly symlink_path="$SYSTEM_BIN_DIR/$1"
	if [[ -f "$symlink_path" ]]; then
		log "INFO" "Symlink $symlink_path already exists. Will not add again."
	else
		log "INFO" "Adding symlink to $2 in $symlink_path"
		sudo ln -s "$2" "$symlink_path"
	fi
}

function ensure_system_packages {
	sudo apt-get install -y libpq-dev gcc >/dev/null
}

function write_runfile {

	local runfile="$1"
	local symlink="$2"

	tee $runfile > /dev/null <<EOF
#!/bin/bash -i

set -e

source ~/.bashrc

if [ \$# -lt 2 ]; then
	echo "USAGE: <conda-env> <command> <args>"
	exit -1
else
	CENV="\$1"
	shift;
	COMMAND="\$@"
fi

echo "RUNNING [\${CENV}]: python manage.py \${COMMAND}"

# this will move you to the repo directory
conda activate \${CENV}

stdbuf -oL -eL python -u manage.py \${COMMAND}
EOF
	chmod ug+x $runfile
	add_system_symlink $symlink $runfile
}

function install_conda {
	local install_prefix="$1"
	if [ ! -d $install_prefix ]; then
		echo "installing conda at $install_prefix"
		mkdir -p $install_prefix
		wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O $install_prefix/miniconda.sh
		bash $install_prefix/miniconda.sh -b -u -p $install_prefix
		rm -rf $install_prefix/miniconda.sh
		$install_prefix/bin/conda init bash
		source ~/.bashrc
		conda config --set auto_activate_base false
		conda deactivate
	fi
}

function setup_application {
	local app_repo="$1"
	local pip_requirements="$2"
	local runfile="$3"

	echo "setting up conda application"
	if [ ! -d "$CONDA_PREFIX/etc/conda/activate.d" ]; then
		mkdir -p $CONDA_PREFIX/etc/conda/{activate.d,deactivate.d}
		echo "cd $app_repo" > $CONDA_PREFIX/etc/conda/activate.d/entrypoint.sh
		echo "cd ~" > $CONDA_PREFIX/etc/conda/deactivate.d/exitpoint.sh
	fi
	write_runfile ~/app/$runfile $runfile
	cd $app_repo
	ensure_system_packages
	echo "pip installing required packages: $pip_requirements"
	pip install -r $pip_requirements >/dev/null
}

function install_application {
	local conda_env="$1"
	local python_version="$2"
	local app_repo="$3"
	local pip_requirements="$4"
	local runfile="$5"

	# setup conda environment and add application
	if { conda env list | grep $conda_env; } >/dev/null 2>&1; then
		echo "found conda environment $conda_env"
		conda activate $conda_env
		setup_application $app_repo $pip_requirements $runfile
	else
		echo "creating conda environment $conda_env $python_version"
		conda create -n $conda_env -y -q python=$python_version
		conda activate $conda_env
		setup_application $app_repo $pip_requirements $runfile
	fi
}

# =====================================================================================
# =====================================================================================
# =====================================================================================
# =====================================================================================
# =====================================================================================


APP_REPO=
PIP_REQUIREMENTS=requirements/local.txt
INSTALL_PREFIX=~/miniconda3
PYTHON_VERSION="3.10"
CONDA_ENV="deploy"
RUNFILE="run-django"

while [[ $# -gt 0 ]]
do
key="$1"

case $key in 
		-h|--help)
	echo "< Usage: boolean arguments or args separated by spaced >"
		exit 0
	;;
	-p|--prefix)
	INSTALL_PREFIX="$2"
	shift # past argument
	shift # past value
	;;
	--py-version)
	PYTHON_VERSION="$2"
	shift # past argument
	shift # past value
	;;
	-e|--conda-env)
	CONDA_ENV="$2"
	shift # past argument
	shift # past value
	;;
	-s|--script)
	RUNFILE="$2"
	shift # past argument
	shift # past value
	;;
	-r|--requirements)
	PIP_REQUIREMENTS="$2"
	shift # past argument
	shift # past value
	;;
	-a|--app-repo)
	APP_REPO="$2"
	shift # past argument
	shift # past value
	;;
esac
done

if [ -z $APP_REPO ]; then
	echo "ERROR: must provide app repo for installation"
	exit -1
fi

#echo `which conda`

install_conda $INSTALL_PREFIX

echo "setting up application"
install_application $CONDA_ENV $PYTHON_VERSION $APP_REPO $PIP_REQUIREMENTS $RUNFILE
# TODO: install .env from somewhere

