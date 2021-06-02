# IPA-DN-PyNeko-v1
# 
# Copyright (c) 2021- IPA CyberLab.
# All Rights Reserved.
# 
# Author: Daiyuu Nobori
# Description

import subprocess

from submodules.IPA_DN_PyNeko.v1.PyNeko import *


res = EasyExec.ShellExecutePiped("sleep 5", ignoreError=True, timeoutSecs=1)

print("code = " + str(res.ExitCode))

lines = res.StdOutAndErr.splitlines()
for line in lines:
    print(F"# {line}")





