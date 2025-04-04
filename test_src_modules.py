# -*- coding: utf-8 -*-
"""
Created on Fri Apr  4 14:51:58 2025

@author: user
"""
import importlib
import os
import pandas as pd
import src.schema_builder
importlib.reload(src.schema_builder)
from src.schema_builder import FrameCheck

df = pd.DataFrame({
    'id': ['a98325jh', '235lkjl25', '23543k5'],
    'age': [25, 18, 85.0],
    'score': [0.5, 0.9, 0.56],
    'subscribed': [True, False, True],
    'signup_date': pd.to_datetime(['2022-01-01', '2023-01-01', '2024-01-01']),
    'email': ['a@example.com', 'abc@gmail.com', 'b@example.com'],
    'phone': ['1231235757', '2828437222', '2139499999']
})

schema = (
    FrameCheck()
    .column('id')
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0, max=0.55, warn_only=True)  # intentionally triggers a warning
    .column('subscribed', type='bool')
    .column('signup_date', type='datetime', min='2022-01-01', max='2025-12-31')
    .column('email', type='string', regex=r'.+@.+\..+')
    .build()
)

result = schema.validate(df)
print(result.summary())
