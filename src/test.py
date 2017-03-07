#!/usr/bin/env python

import sys
from botox import Botox

new_ep = Botox(sys.argv[1]).patch()
print "File %s patched. New entry point: 0x%.8X" % (sys.argv[1], new_ep)
