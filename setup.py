# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

setup(name='screenlly',
      version='0.0.1',
      description="Get and compare screenshots tool based on Selenium and ImageMagick",
      include_package_data=True,
      packages=find_packages(),
      install_requires=['selenium>=3.12.0', 'Pillow>=5.1.0'])
