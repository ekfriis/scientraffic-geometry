#!/bin/bash

virtualenv venv

source venv/bin/activate
pip install numpy
# needs sudo apt-get install python python-dev libatlas3-base-dev gcc gfortran
# g++
pip install git+http://github.com/scipy/scipy/@v0.12.0b1
pip install shapely
pip install descartes
pip install matplotlib
pip install ipython

# You have to do some trickery for this one.
# http://gis.stackexchange.com/questions/28966/python-gdal-package-missing-header-file-when-installing-via-pip
pip install GDAL
