#!/usr/bin/python
##############################################################################
# Cake Build Tool
##############################################################################

import sys
import os.path

libDir = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(libDir)

import cake.main

sys.exit(cake.main.run(sys.argv[1:]))
