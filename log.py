
import sys

from util.msg import info, warn, err, dbg
from util.type import type_check


class Logger:
    def __init__(self, stdoutFiles=None, stderrFiles=None, debugFiles=None, suppressStandard=False):
        if stdoutFiles is None: stdoutFiles = []
        if stderrFiles is None: stderrFiles = []
        if debugFiles is None: debugFiles = []
        if not isinstance(stdoutFiles, list): stdoutFiles = [stdoutFiles]
        if not isinstance(stderrFiles, list): stderrFiles = [stderrFiles]
        if not isinstance(debugFiles, list): debugFiles = [debugFiles]
        self.suppress_standard = suppressStandard

        self.stdoutFiles=stdoutFiles
        self.stderrFiles=stderrFiles
        self.debugFiles=debugFiles

    def info(self, msg, indent=""):
        for target in self.stdoutFiles:
            info(msg, indent=indent, target=target)
        if not self.suppress_standard:
            info(msg, indent=indent)

    def dbg(self, msg):
        for target in self.stdoutFiles:
            dbg(msg, target=target)
        if not self.suppress_standard:
            dbg(msg)

    def warn(self, msg, indent=""):
        for target in self.stderrFiles:
            warn(msg, indent=indent, target=target)
        if not self.suppress_standard:
            warn(msg, indent=indent)

    def err(self, msg, indent=""):
        for target in self.stderrFiles:
            err(msg, indent=indent, target=target)
        if not self.suppress_standard:
            err(msg, indent=indent)

