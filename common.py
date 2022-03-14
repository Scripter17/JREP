import inspect, os, functools, re

# Compatibility for old Python versions
if not hasattr(functools, "cache"):
	functools.cache=functools.lru_cache(maxsize=None)

def verbose(x, override=False):
	calls=inspect.stack()[1:]
	print(f"Verbose on lines {', '.join([f'{call[2]}:{call[3]}' for call in calls])}: {x}")
def warn(x, error=None, override=False, hard=False):
	if hard:
		raise error or Exception(f"No error provided (Message: \"{x}\")")
	else:
		calls=inspect.stack()[1:]
		print(f"Waring on lines {', '.join([f'{call[2]}:{call[3]}' for call in calls])}: {x}", file=sys.stderr)

@functools.cache
def _blockwiseSort(x, y):
	"""
		The main blockwise sort handler
		This sort key mimics how the Windows file explorer places "abc10.txt" after "abc2.txt" but more generally
		It first splits both x and y into chunks of integer substrings and non-integer substrings
		"abc123def" -> ["abc", "123", "def"]
		It then compares the Nth element of each list (a "blocK") as strings UNLESS both blocks are integers, in which case it compares them as integers
		So while "2" is larger than "10", they'd be compared as 2 and 10 and would thus be sorted properly
	"""
	xblocks=re.findall(r"\d+|[^\d]+", x) # "abc123def" -> ["abc", "123", "def"]
	yblocks=re.findall(r"\d+|[^\d]+", y)
	for xblock, yblock in zip(xblocks, yblocks):
		if xblock.isdigit() and yblock.isdigit():
			# Compare the blocks as ints
			if int(xblock)!=int(yblock):
				return int(xblock)-int(yblock) # An output of -53245 is treated the same as -1
			# If they're equal, move on to the next block pair
		else:
			# Compare the blocks as strings
			if xblock!=yblock:
				return (xblock>yblock)-(xblock<yblock)
	return 0

@functools.cmp_to_key
def blockwiseSort(x, y):
	"""
		Prevents the blockwise sort from splitting 123abc/def456 into ["123", "abc/def", "456"]
	"""
	xlist=x.replace("\\", "/").split("/")
	ylist=y.replace("\\", "/").split("/")
	for xitem, yitem in zip(xlist, ylist):
		if _blockwiseSort(xitem, yitem)!=0:
			return _blockwiseSort(xitem, yitem)
	return (len(xlist)>len(ylist))-(len(xlist)<len(ylist))


sorts={
	"ctime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_ctime,
	"mtime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_mtime,
	"atime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_atime,
	"name"     : lambda x:x["name"],
	"blockwise": lambda x:blockwiseSort(x["name"]),
	"size"     : lambda x:len(x["data"]) if x["stdin"] else os.path.getsize(x["name"])
}

def sortFiles(files, key=None, sortRegex=[]):
	"""
		Sorts files if --sort is present
		Note that sorting files requires loading all file names in a directory into memory
		Also it's just generally slow for large file sets
		Unless you're using really high end SSD, CPU, and RAM
		And if you are then I'm sorry for writing JREP in Python
	"""
	if key==None:
		return files

	for sort in list(sorts.keys()):
		# Scopes suck
		sorts["r"+sort]=(lambda _sort:lambda x:-sorts[_sort](x))(sort)

	if key in ["name", "blockwise", "rname", "rblockwise"] and sortRegex:
		for pattern, replace in zip(sortRegex[0::2], sortRegex[1::2]):
			files=map(lambda file: {"orig":file["orig"] if "orig" in file else file, "name":re.sub(pattern, replace, file["name"])}, files)

	return ((file["orig"] if "orig" in file else file) for file in sorted(files, key=sorts[key]))

	#return sorted(files, key=sorts[key])

def sortDirFiles(names, dirname, key=None):
	"""
		Handler for --sort-dir
	"""
	if key is None:
		yield from names
		return
	files=map(lambda name:{"name":os.path.join(dirname, name), "stdin":False}, names)
	for file in sortFiles(files, key=key, sortRegex=[]): # TEMP SOLUTION
		yield oa.path.relpath(file["name"], dirname)