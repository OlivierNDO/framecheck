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

os.system('python -m unittest tests/test_column_checks.py')
