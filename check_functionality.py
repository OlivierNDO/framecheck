# -*- coding: utf-8 -*-
"""
Created on Thu Apr 10 13:24:46 2025

@author: user
"""
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
    .column('score', type='float', min=0.0, max=1.0)  # Score between 0 and 1
    .unique()
    .only_defined_columns()
    .build()  # Finalize the checks into a schema
)

# Validate the DataFrame
validation_result = validator.validate(df)

# Print the validation result
print("\nValidation Result:")
print(validation_result.summary())  # Shows the summary of validation errors and warnings

# Optionally, print the invalid rows
invalid_rows = validation_result.get_invalid_rows(df)
print("\nInvalid Rows:")
print(invalid_rows)






### Example 2

data = {}

df = pd.DataFrame(data)


# Initialize FrameCheck
validator = (
    FrameCheck()
    .not_empty()
    .build()  # Finalize the checks into a schema
)

# Validate the DataFrame
validation_result = validator.validate(df)

# Print the validation result
print("\nValidation Result:")
print(validation_result.summary())  # Shows the summary of validation errors and warnings

# Optionally, print the invalid rows
invalid_rows = validation_result.get_invalid_rows(df)
print("\nInvalid Rows:")
print(invalid_rows)






