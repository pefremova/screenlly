# -*- coding: utf-8 -*-
from distutils.core import setup
from setuptools import find_packages

setup(name='screenlly',
      version='0.0.9',
      description="Get and compare screenshots tool based on Selenium and ImageMagick",
      author="Polina Efremova",
      author_email="pefremova@gmail.com",
      keywords=["selenium", "testing", "test tool", "screenshot",
                "compare screenshots", "full page screenshot"],
      include_package_data=True,
      packages=find_packages(),
      install_requires=['selenium>=3.12.0', 'Pillow>=5.1.0'],
      classifiers=(
          "Programming Language :: Python :: 3.6",
      ),)
