# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 13:24:46 2025

@author: user
"""
import os
import sys
#sys.dont_write_bytecode = True


from framecheck import FrameCheck

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
    'a': [0, 1, 0, 1, 2],
    'b': [1, 1, 0, 0, 3],
    'timestamp': ['2022-01-01', '2022-01-02', '2019-12-31', '2021-01-01', '2023-05-01'],
    'email': ['a@example.com', 'bad', 'b@example.com', 'not-an-email', 'c@example.com'],
    'extra': ['x'] * 5
})


validator = (
    FrameCheck()
    .columns(['a', 'b'], type='int', in_set=[0, 1])
    .column('timestamp', type='datetime', after='2020-01-01')
    .column('email', type='string', regex=r'.+@.+\..+', warn_only=True)
    .only_defined_columns()
    .row_count(min=5, max=100)
    .not_empty()
    .raise_on_error()
)

result = validator.validate(df)









import great_expectations as ge

ge_df = ge.from_pandas(df)
ge_df.expect_column_values_to_be_in_set('a', [0, 1])
ge_df.expect_column_values_to_be_of_type('a', 'int64')
ge_df.expect_column_values_to_be_in_set('b', [0, 1])
ge_df.expect_column_values_to_be_of_type('b', 'int64')
ge_df['timestamp'] = pd.to_datetime(ge_df['timestamp'])
ge_df.expect_column_values_to_be_of_type('timestamp', 'datetime64[ns]')
ge_df.expect_column_values_to_be_between('timestamp', min_value='2020-01-01')
ge_df.expect_column_values_to_match_regex('email', r'.+@.+\..+', mostly=1.0)
ge_df.expect_table_row_count_to_be_between(min_value=5, max_value=100)
ge_df.expect_table_row_count_to_be_greater_than(0)
expected_columns = {'a', 'b', 'timestamp', 'email'}
unexpected = set(df.columns) - expected_columns
if unexpected:
    raise ValueError(f"Unexpected columns in DataFrame: {unexpected}")

results = ge_df.validate()
if not results['success']:
    raise ValueError(f"Validation failed: {results}")