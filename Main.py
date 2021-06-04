# IPA-DN-PyNeko-v1
#
# Copyright (c) 2021- IPA CyberLab.
# All Rights Reserved.
#
# Author: Daiyuu Nobori
# Description

import os
import json
import subprocess
import inspect
from typing import List, Tuple, Dict, Set
import typing

from submodules.IPA_DN_PyNeko.v1.PyNeko import *

print(Str.ReplaceStr("abcdef", "C", "_", caseSensitive=True))
exit(0)

ret = Docker.GetContainer("hardcore_turing")
Print(ret)

