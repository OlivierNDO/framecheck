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

