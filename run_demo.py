"""Run the synthetic experiment and refresh the local dashboard data."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parent
env = dict(os.environ)
if sys.platform == 'darwin':
    # Reuse the OpenMP runtime shipped by the installed scikit-learn wheel.
    spec = importlib.util.find_spec('sklearn')
    library_dir = Path(spec.origin).parent / '.dylibs'
    env['DYLD_LIBRARY_PATH'] = str(library_dir) + os.pathsep + env.get('DYLD_LIBRARY_PATH', '')
subprocess.run([sys.executable, str(root/'train.py')], env=env, check=True)
subprocess.run([sys.executable, str(root/'model_runtime.py'), 'train', '--csv',
                str(root/'data/demo.csv'), '--source', 'demo'], env=env, check=True)
shutil.copy2(root/'artifacts/results.json', root/'frontend/src/results.json')
