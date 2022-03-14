import glob as _glob, common

import contextlib
import os
import re
import fnmatch
import itertools
import stat
import sys

def verbose(x, override=False):
	return
def warn(x, error=None, override=False):
	return

def glob(pathname, *, root_dir=None, dir_fd=None, recursive=False, runData=None):
    """Return a list of paths matching a pathname pattern.

    The pattern may contain simple shell-style wildcards a la
    fnmatch. However, unlike fnmatch, filenames starting with a
    dot are special cases that are not matched by '*' and '?'
    patterns.

    If recursive is true, the pattern '**' will match any files and
    zero or more directories and subdirectories.
    """
    return list(iglob(pathname, runData=runData, root_dir=root_dir, dir_fd=dir_fd, recursive=recursive))

def iglob(pathname, *, root_dir=None, dir_fd=None, recursive=False, runData=None):
	"""Return an iterator which yields the paths matching a pathname pattern.

	The pattern may contain simple shell-style wildcards a la
	fnmatch. However, unlike fnmatch, filenames starting with a
	dot are special cases that are not matched by '*' and '?'
	patterns.

	If recursive is true, the pattern '**' will match any files and
	zero or more directories and subdirectories.
	"""
	sys.audit("glob.glob", pathname, recursive)
	sys.audit("glob.glob/2", pathname, recursive, root_dir, dir_fd)
	if root_dir is not None:
		root_dir = os.fspath(root_dir)
	else:
		root_dir = pathname[:0]
	it = _iglob(pathname, root_dir, dir_fd, recursive, False, runData=runData)
	if not pathname or recursive and _glob._isrecursive(pathname[:2]):
		try:
			s = next(it)  # skip empty string
			if s:
				it = itertools.chain((s,), it)
		except StopIteration:
			pass
	return it

def _iglob(pathname, root_dir, dir_fd, recursive, dironly, runData=None):
	dirname, basename = os.path.split(pathname)
	if not _glob.has_magic(pathname):
		assert not dironly
		if basename:
			if _glob._lexists(_join(root_dir, pathname), dir_fd):
				yield pathname
		else:
			# Patterns ending with a slash should match only directories
			if _glob._isdir(_join(root_dir, dirname), dir_fd):
				yield pathname
		return
	if not dirname:
		if recursive and _glob._isrecursive(basename):
			yield from _glob2(root_dir, basename, dir_fd, dironly, runData=runData)
		else:
			yield from _glob1(root_dir, basename, dir_fd, dironly, runData=runData)
		return
	# `os.path.split()` returns the argument itself as a dirname if it is a
	# drive or UNC path.  Prevent an infinite recursion if a drive or UNC path
	# contains magic characters (i.e. r'\\?\C:').
	if dirname != pathname and has_magic(dirname):
		dirs = _iglob(dirname, root_dir, dir_fd, recursive, True)
	else:
		dirs = [dirname]
	if _glob.has_magic(basename):
		if recursive and _glob._isrecursive(basename):
			glob_in_dir = _glob2
		else:
			glob_in_dir = _glob1
	else:
		glob_in_dir = _glob0
	for dirname in dirs:
		for name in _glob.glob_in_dir(_join(root_dir, dirname), basename, dir_fd, dironly):
			yield os.path.join(dirname, name)

def _glob1(dirname, pattern, dir_fd, dironly=False, runData=None):
	"""
		A modified version of glob._glob1 for the sake of both customization and optimization
	"""
	names = _iterdir(dirname, dir_fd, dironly, runData=runData)
	if not _glob._ishidden(pattern):
		names = (x for x in names if not _glob._ishidden(x))
	for name in names:
		if fnmatch.fnmatch(name, pattern):
			verbose(f"Yielding \"{name}\"")
			yield name
		if runData["doneDir"]:
			runData["doneDir"]=False
			break

def _glob2(dirname, pattern, dir_fd, dironly, runData=None):
    assert _isrecursive(pattern)
    yield pattern[:0]
    yield from _rlistdir(dirname, dir_fd, dironly, runData=runData)

def _rlistdir(dirname, dir_fd, dironly=False, runData=None):
	"""
		A modified version of glob._rlistdir for the sake of both customization and optimization
	"""
	names = _glob._listdir(dirname, dir_fd, dironly)
	for x in names:
		if not _glob._ishidden(x):
			yield x
			path = _glob._join(dirname, x) if dirname else x
			for y in _rlistdir(path, dir_fd, dironly):
				yield _glob._join(x, y)
				if runData["doneDir"]:
					runData["doneDir"]=False
					break

def _listdir(dirname, dir_fd, dironly):
	"""
		For Python 3.6 compatibility
	"""
	with contextlib.closing(_iterdir(dirname, dir_fd, dironly, runData=runData)) as it:
		return list(it)

def _iterdir(dirname, dir_fd, dironly=False, runData=None):
	"""
		A modified version of glob._iterdir for both customization and optimization
	"""
	files=[]
	directories=[]
	try:
		fd = None
		fsencode = None
		if isinstance(dir_fd, bool):
			dir_fd=None

		if dir_fd is not None:
			if dirname:
				fd = arg = os.open(dirname, _glob._dir_open_flags, dir_fd=dir_fd)
			else:
				arg = dir_fd
			if isinstance(dirname, bytes):
				fsencode = os.fsencode
		elif dirname:
			arg = dirname
		elif isinstance(dirname, bytes):
			arg = bytes(os.curdir, 'ASCII')
		else:
			arg = os.curdir
		try:
			with os.scandir(arg) as it:
				for entry in it:
					try:
						if not dironly or entry.is_dir():
							if entry.is_dir():
								directories.append(entry.name)
							else:
								if fsencode is not None:
									files.append(fsencode(entry.name))
								else:
									files.append(entry.name)
					except OSError:
						pass
				# Yield files and folders in the right order
				files=common.sortDirFiles(files, dirname, key=runData["sortDir"])
				if runData["depthFirst"]:
					yield from directories
					yield from files
				else:
					yield from files
					yield from directories
		finally:
			if fd is not None:
				os.close(fd)
	except OSError:
		return

def _join(dirname, basename):
	# It is common if dirname or basename is empty
	if not dirname or not basename:
		return dirname or basename
	return os.path.join(dirname, basename)
