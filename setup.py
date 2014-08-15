#!/usr/bin/env python

from setuptools import setup

setup(name='caravan_fhem',
    version='0.0.1',
    description='FHEM communication module for Caravan',
    author='Alexey Balekhov',
    author_email='a@balek.ru',
    py_modules = ['caravan_fhem'],
    entry_points = {
        'autobahn.twisted.wamplet': [ 'fhem = caravan_fhem:AppSession' ]
    })