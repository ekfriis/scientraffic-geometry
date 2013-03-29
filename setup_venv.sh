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
