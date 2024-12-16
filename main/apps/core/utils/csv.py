import os
import glob

def get_csv_files_from_dir(file_path):
    extension = 'csv'
    os.chdir(file_path)
    return glob.glob('*.{}'.format(extension))
