# -*- coding: utf-8 -*-
"""
Created on Sat Apr  5 11:22:02 2025

@author: user
"""



import os
os.system('pytest')



for fn in os.listdir('tests/'):
    if 'test' in fn:
        if '.py' in fn:
            print(f'### Running {fn}')
            os.system(f'python -m unittest tests/{fn}')
            print('\n\n\n')
            
