"""Launch the local server with the OpenMP runtime installed by scikit-learn."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
env = dict(os.environ)
if sys.platform == 'darwin':
    spec = importlib.util.find_spec('sklearn')
    if spec is not None:
        library = Path(spec.origin).parent / '.dylibs'
        env['DYLD_LIBRARY_PATH'] = str(library) + os.pathsep + env.get('DYLD_LIBRARY_PATH', '')
raise SystemExit(subprocess.call([sys.executable, str(root/'server.py'), *sys.argv[1:]], env=env))
