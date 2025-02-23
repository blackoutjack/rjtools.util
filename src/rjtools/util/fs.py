"""
Filesystem access wrapper to support redirection

Includes wrappers for `open` and relevant `os[.path]` methods and that also
hit the fs.
"""

import io
import os
import stat
import sys
import time

from .testutil import Link
from .msg import err, info

class StandardFS:
    """
    Simple wrappers calling the standard `os[.path]` methods.
    """

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

    def get_file_size(self, path):
        return os.stat(path).st_size


class StubFS:
    """
    Present in-memory data as a filesystem
    """
    def __init__(self, mockfiles=None):
        if mockfiles is None:
            mockfiles = {}
        self.mockfiles = mockfiles

    # Process startup time (approx.) for `getmtime` mock
    startTime = time.time()

    def is_file_content(self, val):
        return isinstance(val, bytes)

    def is_directory_content(self, val):
        return isinstance(val, dict)

    def is_symlink_content(self, val):
        return isinstance(val, Link)

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
        cur = self.mockfiles
        for part in parts:
            if self.is_file_content(cur):
                # Resolved a file, now trying to resolve another path segment
                raise NotADirectoryError(
                    f"[Errno 20] Not a directory: '{cur}'")

            if self.is_directory_content(cur):
                if part not in cur:
                    raise FileNotFoundError(
                        f"[Errno 2] No such file or directory: '{path}'")
                cur = cur[part]
                prefix = os.path.join(prefix, part)

            elif self.is_symlink_content(cur):
                prefix, cur = self.resolve(cur.target)
            else:
                raise ValueError(
                    f"Unexpected type in mock filesystem: {type(cur)}")

        return prefix, cur

    def binary_open(self, filepath):
        path, contents = self.resolve(filepath)
        if isinstance(contents, dict):
            # The filepath pointed to a directory.
            raise IsADirectoryError(f"[Errno 21] Is a directory: '{path}'")
        return io.BytesIO(contents)

    def text_open(self, filepath):
        return io.TextIOWrapper(
            self.binary_open(filepath),
            sys.getdefaultencoding())

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
        _, thedir = self.resolve(dirname)
        del thedir[filename]

    def get_modify_time(self, path):
        return type(self).startTime

    def walk(self, path):
        _, base = self.resolve(path)
        if isinstance(base, str):
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

        do_walk(self, path)
        return

    def get_real_path(self, path, strict=False):
        return path

    def get_file_size(self, path):
        filepath, contents = self.resolve(path)
        return len(contents)

fs = StandardFS()

"""
Top-level functions to call into the current fs instance
"""


def install_mocks(mockfiles):
    global fs
    fs = StubFS(mockfiles)

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


"""
Other utility functions
"""

def insert_suffix_into_filename(filepath, suffix):
    """
    Inject the given suffix into the filename prior to the extension.

    :param filepath: the path or filename to insert `suffix` into
    :param suffix: suffix to insert
    """
    base, ext = os.path.splitext(filepath)
    return f"{base}{suffix}{ext}"

def is_root(filepath):
    """
    Detect whether the given path is the root of the filesystem

    :param filepath: the path or filename to insert `suffix` into
    """
    realpath = get_real_path(filepath, strict=False)
    return realpath == os.path.dirname(realpath)

def is_hidden(filepath):
    filename = os.path.basename(filepath)
    if filename.startswith('.'):
        return True

    # Windows. %%% Untested
    try:
        attributes = os.stat(filepath).st_mode
        return bool(attributes & stat.FILE_ATTRIBUTE_HIDDEN)
    except AttributeError:
        return None
    except FileNotFoundError:
        return None

def is_empty(filepath):
    try:
        return fs.get_file_size(filepath) == 0
    except (FileNotFoundError, PermissionError, NotADirectoryError, UnicodeEncodeError, OSError) as ex:
        # Caller that doesn't care can take this as false.
        # One who does can check.
        err(str(ex))
        return None


