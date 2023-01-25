'''Test file system access wrapper in util.fs'''

from util import fs

def test_binary_basic():
    '''Open a file in binary mode and read the contents'''
    fl = fs.binary_open("/topdir/filetree/basic.txt")
    contents = fl.read().decode('utf-8')
    return contents == "some text here"

def test_text_basic():
    '''Open a file in text mode and read the contents'''
    fl = fs.text_open_utf8("/topdir/filetree/basic.txt")
    contents = fl.read()
    return contents == "some text here"

