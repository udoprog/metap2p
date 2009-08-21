from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='MetaP2P',
      version=version,
      description="MetaP2P lightweight P2P Framework",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='p2p meta',
      author='John-John Tedro',
      author_email='johnjohn.tedro@gmail.com',
      url='',
      license='GPLv3',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=True,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
