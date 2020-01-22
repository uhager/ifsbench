"""
Install the ifsbench package.
"""
import os.path

from setuptools import setup, find_packages

import versioneer

with open(os.path.join(os.path.dirname(__file__), "README.md"), "r") as f:
    long_description = f.read()

setup(
    name="ifsbench",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="ECMWF",
    author_email="user_support_section@ecmwf.int",
    description="IFS benchmark and testing utilities in Python",
    long_description=long_description,
    packages=find_packages(),
)
