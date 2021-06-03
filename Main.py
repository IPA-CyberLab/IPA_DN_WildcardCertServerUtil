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


ret = Docker.RunDockerCommandJson(["ps", "-a"], DockerProcessItem, exact=True)

Print(ret)
exit(0)

#Print(res.StdOut.splitlines()[0])




class TestClass1:
    LocalVolumes: str

list = Json.JsonLinesToObjectList(res.StdOut, TestClass1)

Print(list)

