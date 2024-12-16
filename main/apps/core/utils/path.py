
from pathlib import Path

def updir(path: Path, n : int):
    return path.parents[n-1]