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



df = pd.DataFrame({
    'id': ['a98325jh', '235lkjl25', '23543k5'],
    'age': [25, 18, 85.0],
    'score': [0.5, 0.9, 0.56],
    'subscribed': [True, False, True],
    'signup_date': pd.to_datetime(['2022-01-01', '2023-01-01', '2024-01-01']),
    'email': ['a@example.com', 'abc@gmail.com', 'b@example.com'],
    'phone': ['1231235757', '2828437222', '2139499999'],
    'extra_column': ['unexpected', 'should', 'flag']
})

validator = (
    FrameCheck()
    .column('id', type='string', regex=r'^[a-z0-9]+$')
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0, max=1.0)
    .column('subscribed', type='bool')
    .column('signup_date', type='datetime', after='2010-01-01', before='tomorrow')
    .column('email', type='string', regex=r'.+@.+\..+', in_set=['a@example.com', 'b@example.com'])
    .column('phone', function=lambda x: x.isdigit() and len(x) == 10, description="Phone must be 10 digits")
    .column('missing_column')  # Test missing column detection
    .column('score', type='float', max=0.6, warn_only=True)  # Soft warning on score
    .only_defined_columns()
    .not_empty()
    .unique(columns=['id'])  # Uniqueness based on primary key
    .build()
)

result = validator.validate(df)
#print(result.summary())

# Optionally: show invalid rows
#print("\nInvalid rows:\n", result.get_invalid_rows(df))



import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

result = validator.validate(df)

if not result.is_valid:
    # Raise an error with only the failure messages
    raise ValueError("Validation errors:\n" + "\n".join(result.errors))

if result.warnings:
    # Log warnings (but continue execution)
    logger.warning("Validation warnings:\n" + "\n".join(result.warnings))
else:
    logger.info("DataFrame passed all checks.")












