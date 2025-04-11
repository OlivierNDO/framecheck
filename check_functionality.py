# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 13:24:46 2025

@author: user
"""
import os
import sys
sys.dont_write_bytecode = True


from src.frame_check import FrameCheck

import pandas as pd


### Example 1

data = {
    'id': [1, 2, 3, 4],
    'score': [0.9, 0.5, 1.2, -0.1],
    'age': [25, 17, 34, 101],
    'gender': ['M', 'F', 'M', 'X']  # Invalid gender for the last row
}

df = pd.DataFrame(data)


# Initialize FrameCheck
validator = (
    FrameCheck()
    .column('id')  # ColumnExistsCheck for 'id'
    .column('score', type='float', min=0.0, max=1.0, warn_only = True)  # Score between 0 and 1
    .column('this is not there')
    .unique()
    .only_defined_columns()
    .raise_on_error()
)

# Validate the DataFrame
validation_result = validator.validate(df)



### Example 2
df = pd.DataFrame({
    'id': ['a123', 'b456', 'c789'],
    'good_credit': [0, 1, 0],
    'home_owner': [1, 1, 0],
    'promo_eligible': [0, 0, 1],
    'score': [0.9, 0.5, 1.2],
    'email': ['x@example.com', 'bad', 'z@example.com'],
})

validator = (
    FrameCheck()
    .columns(['good_credit', 'home_owner', 'promo_eligible'], type = 'int', in_set = [0, 1])
    .column('score', type='float', min=0.0, max=1.0)
    .column('email', type='string', regex=r'.+@.+\..+', warn_only = True)
    .unique(columns = ['id'])
    .row_count(2)
    .not_empty()
    .raise_on_error()
)

result = validator.validate(df)










errors = []

if df.empty: errors.append("DataFrame is empty.")
expected_cols = {'id', 'age', 'good_credit', 'home_owner', 'promo_eligible', 'score', 'email'}
extra = set(df.columns) - expected_cols
if extra: errors.append(f"Unexpected columns: {sorted(extra)}")

for col in ['good_credit', 'home_owner', 'promo_eligible']:
    if not df[col].isin([0, 1]).all():
        errors.append(f"Column '{col}' contains values outside [0, 1].")

if not df['id'].str.match(r'^[a-z0-9]+$').all():
    errors.append("Column 'id' contains invalid strings.")

if (df['age'] < 18).any(): errors.append("Column 'age' has values < 18.")
if (df['age'] > 99).any(): errors.append("Column 'age' has values > 99.")

if (df['score'] < 0).any(): errors.append("Column 'score' has values < 0.")
if (df['score'] > 1).any(): errors.append("Column 'score' has values > 1.")

# Warning only: email regex
bad_email = ~df['email'].str.contains(r'.+@.+\..+', regex=True)
if bad_email.any(): print("Warning: Some emails are invalid:", df['email'][bad_email].tolist())

if errors:
    raise ValueError("Validation failed:\n" + "\n".join(errors))