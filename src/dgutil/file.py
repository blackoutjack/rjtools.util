
import os
import sys
import tempfile
import importlib.util

def insert_suffix_into_filename(filepath, suffix):
    base, ext = os.path.splitext(filepath)
    return f"{base}{suffix}{ext}"

