"""
Copyright (C) 2019 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable.
"""
#from distutils.core import setup
from setuptools import setup
from allyapi import get_version_string

import sys

if sys.version_info < (3,1):
    sys.exit("Only Python 3.1 and greater is supported") 

setup(
    name='ibapi',
    version=get_version_string(),
    packages=['allyapi'],
    url='https://github.com/faangbait/allyapi',
    license='None',
    author='Limitless Interactive LLC',
    author_email='sam@madeof.glass',
    description='Python Ally Invest API'
)
