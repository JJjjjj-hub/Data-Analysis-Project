import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from web.services.ml import TrainOptions, train_classifier

np.random.seed(42)
n = 200
df = pd.DataFrame({
    'age': np.random.randint(15, 25, n),
    'sleep_hours': np.random.normal(7, 1.5, n),
    'gender': np.random.choice(['M', 'F'], n),
    'depression_label': np.random.choice([0, 1], n),
})

print("=== linear_regression enable_cv=False ===")
pipe, m = train_classifier(df, TrainOptions(enable_cv=False), model='linear_regression')
print(f"f1: {m['f1']:.4f}")
print(f"feature_importance: {len(m['feature_importance'])} features")
assert 'feature_importance' in m
assert len(m['feature_importance']) > 0
print("PASS\n")

print("=== linear_regression enable_cv=True cv_folds=2 ===")
pipe2, m2 = train_classifier(df, TrainOptions(enable_cv=True, cv_folds=2), model='linear_regression')
print(f"best_params: {m2['best_params']}")
print(f"cv_scores: {m2['cv_scores']}")
assert 'best_params' in m2
assert 'cv_scores' in m2
assert len(m2['cv_scores']['scores']) == 2
print("PASS\n")

print("All tests passed!")