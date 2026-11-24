"""New AI-assisted implementation of selected methods from Dewen Wang's thesis.

No historical training code or original dataset was available. See PROVENANCE.md.
"""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge, LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier, StackingClassifier
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import (accuracy_score, roc_auc_score, recall_score,
                           precision_score, f1_score, cohen_kappa_score,
                           matthews_corrcoef)

ROOT = Path(__file__).resolve().parent
FEATURES = [f'sensor_{i:02}' for i in range(1, 16)]


def label_days(days):
    """Explicit boundary: exactly seven days is negative in this new project."""
    return (np.asarray(days) < 7).astype(int)


def demo_data(path):
    """Independent synthetic snapshots; neither equipment records nor thesis data."""
    rng = np.random.default_rng(23)
    latent = rng.normal(size=(240, 4))
    x = np.einsum('ij,jk->ik', latent, rng.normal(size=(4, 15))) + rng.normal(0, .3, size=(240, 15))
    days = np.clip(9 - 3 * latent[:, 0] - 2 * latent[:, 1] + rng.normal(size=240), 0, 30)
    x[rng.random(x.shape) < .06] = np.nan
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['record_id', *FEATURES, 'remaining_days'])
        for i, (row, day) in enumerate(zip(x, days)):
            writer.writerow([f'DEMO-{i:04}', *['' if np.isnan(v) else v for v in row], day])


def load_data(path):
    with path.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    ids = [r['record_id'] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('record_id must be unique; repeated rows would contaminate evaluation')
    x = np.array([[float(r[f]) if r[f] else np.nan for f in FEATURES] for r in rows])
    days = np.array([float(r['remaining_days']) for r in rows])
    y = label_days(days)
    if not np.isfinite(days).all() or (days < 0).any():
        raise ValueError('remaining_days must be finite and nonnegative')
    if np.isinf(x).any() or np.isnan(x).all(axis=0).any():
        raise ValueError('features cannot contain infinity or an entirely missing column')
    if len(np.unique(y)) != 2 or np.bincount(y).min() < 15:
        raise ValueError('need at least 15 samples in each class for nested cross-validation')
    return rows, x, y


def make_model(seed=23):
    # Preprocessing belongs inside EVERY base pipeline. Stacking's inner folds
    # must not share an imputer fitted on their validation rows.
    def pipeline(classifier):
        return make_pipeline(IterativeImputer(estimator=BayesianRidge(),
                             random_state=seed, max_iter=10), classifier)
    estimators = [
        ('lgbm', pipeline(LGBMClassifier(n_estimators=30, num_leaves=7,
                                      verbosity=-1, random_state=seed, n_jobs=1))),
        ('extra_trees', pipeline(ExtraTreesClassifier(n_estimators=32,
                                  min_samples_leaf=2, random_state=seed, n_jobs=1))),
        ('random_forest', pipeline(RandomForestClassifier(n_estimators=32,
                                   min_samples_leaf=2, random_state=seed, n_jobs=1)))
    ]
    return StackingClassifier(estimators=estimators,
        final_estimator=LogisticRegression(max_iter=1000), stack_method='predict_proba',
        cv=StratifiedKFold(3, shuffle=True, random_state=seed), n_jobs=1)


def run(path, output, is_demo):
    rows, x, y = load_data(path)
    model = make_model()
    # Outer predictions are out of fold; remaining_days is used only as a label.
    cv = StratifiedKFold(10, shuffle=True, random_state=23)
    probabilities = cross_val_predict(model, x, y, cv=cv, method='predict_proba')[:, 1]
    predicted = (probabilities >= .5).astype(int)
    metrics = {
        'accuracy': accuracy_score(y, predicted), 'auc': roc_auc_score(y, probabilities),
        'recall': recall_score(y, predicted), 'precision': precision_score(y, predicted, zero_division=0),
        'f1': f1_score(y, predicted), 'kappa': cohen_kappa_score(y, predicted),
        'mcc': matthews_corrcoef(y, predicted)
    }
    result = dict(data_source='synthetic demonstration' if is_demo else 'user supplied CSV',
        sample_count=len(y), label='remaining_days < 7', threshold=.5,
        evaluation='pooled out-of-fold metrics from outer 10-fold stratified CV; inner 3-fold stacking',
        limitations='Random CV assumes independent rows. Not valid evidence for repeated equipment or temporal generalization.',
        metrics={k:float(v) for k,v in metrics.items()},
        devices=[dict(record_id=r['record_id'], risk_probability=float(p),
                      predicted_at_risk=bool(p >= .5), actual_at_risk=bool(t))
                 for r,p,t in zip(rows, probabilities, y)])
    output.mkdir(parents=True, exist_ok=True)
    (output/'results.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k != 'devices'}, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts')
    args = parser.parse_args()
    is_demo = args.csv is None
    path = args.csv or ROOT/'data/demo.csv'
    if is_demo:
        path.parent.mkdir(exist_ok=True)
        demo_data(path)
    run(path, args.output, is_demo)
