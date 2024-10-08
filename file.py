
import os
import tempfile

def insert_suffix_into_filename(filepath, suffix):
    base, ext = os.path.splitext(filepath)
    return f"{base}{suffix}{ext}"

def create_temporary_file(fromFilepath, subdir, suffix):
    temporaryFile = insert_suffix_into_filename(fromFilepath, suffix)
    temporaryFile = os.path.join(
        tempfile.gettempdir(),
        subdir,
        os.path.relpath(temporaryFile, '/'))
    return temporaryFile
