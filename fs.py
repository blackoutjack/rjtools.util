#
# Wrap filesystem access to allow redirection
#
# Includes wrappers for `open` and relevant `os[.path]` methods and that also
# hit the fs.
#

import io
import os
import os.path
import sys
import time

from util.msg import dbg

from util.test.testfs import files, Link

class StandardFS:

    def binary_open(self, filepath):
        return open(filepath, 'rb')

    def text_open(self, filepath):
        return open(filepath, 'r', encoding=sys.getdefaultencoding())

    def text_open_utf8(self, filepath):
        return open(filepath, 'r', encoding='utf-8')

    def is_file(self, path):
        return os.path.isfile(path)

    def is_dir(self, path):
        return os.path.isdir(path)

    def is_link(self, path):
        return os.path.islink(path)

    def unlink(self, path):
        os.unlink(path)

    def walk(self, path):
        return os.walk(path)
 
    def get_modify_time(self, path):
        return os.path.getmtime(path)       

    def get_real_path(self, path, strict=False):
        return os.path.realpath(path, strict=strict)

# %%% Move this to its own file
class StubFS:

    # Process startup time (approx.) for `getmtime` mock
    startTime = time.time()

    def is_file_content(self, val):
        return type(val) is bytes

    def is_directory_content(self, val):
        return type(val) is dict

    def is_symlink_content(self, val):
        return type(val) is Link

    def resolve(self, path):

        prefix = path
        parts = []
        while prefix not in ["", "/"]:
            prefix, part = os.path.split(prefix)
            parts.insert(0, part)

        # Doesn't really matter, as we currently assume CWD is at the fs root.
        absolute = prefix == "/"

        # Starting at the fs root, resolve the file/directory contents

        # Tracks the value we've resolved to so far
        # %%% Allow the client to indicate the fs contents
        cur = files
        for part in parts:
            if self.is_file_content(cur):
                # We resolved a file, now trying to resolve another path segment
                raise NotADirectoryError(
                    "[Errno 20] Not a directory: '%s'" % cur)

            if self.is_directory_content(cur):
                if part not in cur:
                    raise FileNotFoundError(
                        "[Errno 2] No such file or directory: '%s'" % path)
                cur = cur[part]
                prefix = os.path.join(prefix, part)

            elif self.is_symlink_content(cur):
                prefix, cur = self.resolve(cur.target)
            else:
                raise ValueError("Unexpected type in mock filesystem: %r"
                    % type(cur))
            
        return prefix, cur

    def binary_open(self, filepath):
        path, contents = self.resolve(filepath)
        if type(contents) == dict:
            # The filepath pointed to a directory.
            raise IsADirectoryError("[Errno 21] Is a directory: '%s'" % path)
        return io.BytesIO(contents)
        
    def text_open(self, filepath):
        return io.TextIOWrapper(self.binary_open(filepath), sys.getdefaultencoding())

    def text_open_utf8(self, filepath):
        return io.TextIOWrapper(self.binary_open(filepath), 'utf-8')

    def is_file(self, path):
        _, content = self.resolve(path)
        return self.is_file_content(content)

    def is_dir(self, path):
        _, content = self.resolve(path)
        return self.is_directory_content(content)

    def is_link(self, path):
        _, content = self.resolve(path)
        return self.is_symlink_content(content)

    def unlink(self, path):
        dirname = os.path.dirname(path)
        filename = os.path.basename(path)
        dirpath, thedir = self.resolve(dirname)
        del thedir[filename]

    def get_modify_time(self, path):
        return type(self).startTime

    def walk(self, path):
        _, base = self.resolve(path)
        if type(base) == str:
            return

        def do_walk(self, path):
            base, subs = self.resolve(path)
            # Passing a file to `walk` generates nothing
            if self.is_file_content(subs):
                return

            files = []
            subdirs = []
            for sub in subs:
                subpath = os.path.join(base, sub)
                if self.is_file(subpath):
                    files.append(sub)
                elif self.is_dir(subpath):
                    subdirs.append(sub)
                else:
                    raise ValueError("Not handling links in walk yet")
                    
            yield base, subdirs, files

            for subdir in subdirs:
                # %%% Unnecessary complexity due to always resolving from `/`
                subpath = os.path.join(base, subdir)
                yield from do_walk(self, subpath)
        
        return do_walk(self, path)

    def get_real_path(self, path, strict=False):
        # %%% Review
        return path

fs = StandardFS()

def use_stubs():
    global fs
    if not isinstance(fs, StubFS):
        fs = StubFS()

def binary_open(filepath):
    return fs.binary_open(filepath)

def text_open(filepath):
    return fs.text_open(filepath)
    
def text_open_utf8(filepath):
    return fs.text_open_utf8(filepath)

def is_file(path):
    return fs.is_file(path)

def is_dir(path):
    return fs.is_dir(path)

def is_link(path):
    return fs.is_link(path)

def unlink(path):
    fs.unlink(path)

def walk(path):
    return fs.walk(path)

def get_modify_time(path):
    return fs.get_modify_time(path)

def get_real_path(path, strict=False):
    return fs.get_real_path(path, strict)
            
