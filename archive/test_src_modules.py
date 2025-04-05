# -*- coding: utf-8 -*-
"""
Created on Fri Apr  4 14:51:58 2025

@author: user
"""
import importlib
import pandas as pd

# Reload core modules in correct order
#import src.schema
#import src.frame_check
#importlib.reload(src.schema)
#importlib.reload(src.frame_check)

from src.frame_check import FrameCheck


#from src.frame_check import Schema
#print(Schema.validate.__code__.co_filename)


# Sample DataFrame
df = pd.DataFrame({
    'id': ['a98325jh', '235lkjl25', '23543k5'],
    'age': [25, 18, 85.0],
    'score': [0.5, 0.9, 0.56],
    'subscribed': [True, False, True],
    'signup_date': pd.to_datetime(['2022-01-01', '2023-01-01', '2024-01-01']),
    'email': ['a@example.com', 'abc@gmail.com', 'b@example.com'],
    'phone': ['1231235757', '2828437222', '2139499999']
})

# Define validation schema
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

# Run validation and show summary
result = schema.validate(df)
print(result.summary())


invalid_df = result.get_invalid_rows(df, include_warnings=False)
print(invalid_df)



# Current way of doing this
validator = (
    FrameCheck()
    .column('id')
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0, max=0.55, warn_only=True)
    .build()
)


# I'm thinking out loud here. What if I wanted an error for a score below 0 but a warning for a score above 0.55? 
# Would this work as intended?
validator = (
    FrameCheck()
    .column('id')
    .column('age', type='int', min=18, max=99)
    .column('score', type='float', min=0.0)
    .column('score', type='float', max=0.55, warn_only=True)
    .build()
)





import pandas as pd
from src.frame_check import FrameCheck

def test_dual_severity_checks():
    df = pd.DataFrame({
        'letter': ['a', 'b', 'c'],
        'score': [-1.0, 0.3, 0.8],
        'some_int': [9, 3, 5]
    })

    validator = (
        FrameCheck()
        .column('letter', type='string', in_set = ['a', 'b', 'c'])
        .column('score', type='float', min=0.0)                     # should trigger error on -1.0
        .column('score', type='float', max=0.55, warn_only=True)   # should trigger warning on 0.8
        .only_defined_columns()
        .build()
    )

    result = validator.validate(df)

    assert not result.is_valid
    assert len(result.errors) == 1
    assert len(result.warnings) == 1
    assert '-1.0' in result.errors[0] or 'less than' in result.errors[0]
    assert '0.8' in result.warnings[0] or 'greater than' in result.warnings[0]

    print("✅ test_dual_severity_checks passed!")
    return result

# Run it




import src.frame_check
from src.frame_check import FrameCheck
import importlib
import pandas as pd

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


result._failing_row_indices # {0}

df_inval = result.get_invalid_rows(df)






Errors content: []
Warnings content: ["Column 'score' has values less than 0.0."]





# Example 2
df = pd.DataFrame({
    'letter': ['a', 'b', 'c'],
    'score': [-1.0, 0.3, 0.8],
    'some_int': [9, 3, 5]
})

validator = (
    FrameCheck()
    .column('letter', type='string', in_set = ['a', 'b', 'c'])
    .column('score', type='float', min=0.0) 
    .column('score', type='float', max=0.55, warn_only=True) 
    .column('letter', type='string', regex=r'a')
    .only_defined_columns()
    .build()
)

result = validator.validate(df)

Errors content: ["Column 'score' has values less than 0.0.", "Column 'letter' has values not matching regex 'a': ['b', 'c']."]
Warnings content: ["Column 'score' has values greater than 0.55."]
















df_inval = result.get_invalid_rows(df)







df = pd.DataFrame({
    'letter': ['a', 'b', 'c'],
    'score': [-1.0, 0.3, 0.8],
    'some_int': [9, 3, 5]
})

validator = (
    FrameCheck()
    .column('letter', type='string', in_set = ['a', 'b', 'c'])
    .column('score', type='float', min=0.0)                     # should trigger error on -1.0
    .column('score', type='float', max=0.55, warn_only=True)   # should trigger warning on 0.8
    .only_defined_columns()
    .build()
)


result = validator.validate(df)





































