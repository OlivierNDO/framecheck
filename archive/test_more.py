# -*- coding: utf-8 -*-
"""
Created on Sat Apr  5 11:22:02 2025

@author: user
"""

import src.frame_check
from src.frame_check import FrameCheck
#from tests import test_framecheck
import importlib
import pandas as pd


import os
os.system('python -m unittest tests/test_validation_result.py')



# Reload core modules in correct order
importlib.reload(src.frame_check)

# Example 1
df = pd.DataFrame({
    'letter': ['a', 'b', 'c'],
    'score': [0.1, 0.3, 0.8],
    'some_int': [9, 3, 5]
})

validator = (
    FrameCheck()
    .column('letter', type='string', in_set = ['a', 'b', 'c'])
    .column('score', type='float', min=0.0, warn_only=True)
    .only_defined_columns()
    .build()
)

result = validator.validate(df, verbose = True)