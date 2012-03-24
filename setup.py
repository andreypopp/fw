from setuptools import setup, find_packages
import sys, os

version = "0.1"
requires = []

setup(
    name="fw",
    version=version,
    description="FriendWave -- making mixes of your friends",
    url="fw.zvooq.ru",
    license="BSD",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    entry_points="""
    [console_scripts]
    fw = fw:main
    fwshell = fw:shell
    """)
