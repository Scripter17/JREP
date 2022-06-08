import re, functools, os

blockwiseSplit=re.compile(r"\d+|\D+")
def _blockwise(x, y):
	"""
		A windows-esque sort
		0. Splits "twitter/account/account-1234-1.png" into ["twitter", "account", "account-1234-1-png"]
		1. Splits "account-1234-1.png" into ["account-", "1234", "-", "1", ".png"]
		2. Compares path parts blockwise
		3. If the nth block is an int in both path parts, compare them as ints. Otherwise compare as strings
		So "account-1234-1.png">"account-50-1.png" despite a string-based comparison sorting them the other way
	"""
	if x and y and x[0].isdigit()==y[0].isdigit():
		for xblock, yblock in zip(blockwiseSplit.findall(x), blockwiseSplit.findall(y)):
			if xblock!=yblock:
				if xblock[0].isdigit(): return int(xblock)-int(yblock)
				return (xblock>yblock)-0.5
	return (x>y)-(x<y)

@functools.cmp_to_key
def blockwise(x, y):
	xlist=x.split("/")
	ylist=y.split("/")
	for xpart, ypart in zip(xlist, ylist):
		ret=_blockwise(xpart, ypart)
		if ret:
			return ret
	return len(xlist)-len(ylist)

@functools.cmp_to_key
def nameSort(x, y):
	return (x>y)-(x<y)

sorts={
	"ctime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_ctime,
	"mtime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_mtime,
	"atime"    : lambda x:float("inf") if x["stdin"] else os.stat(x["name"]).st_atime,
	"name"     : lambda x:nameSort(x["name"]),
	"blockwise": lambda x:blockwise(x["name"]),
	"size"     : lambda x:len(x["data"]) if x["stdin"] else os.path.getsize(x["name"])
}
def makeRSort(sort):
	@functools.cmp_to_key
	def ret(x, y):
		x=sorts[sort](x)
		y=sorts[sort](y)
		return (y>x)-(y<x)
	return ret

for sort in list(sorts):
	# Scopes suck
	sorts["r"+sort]=makeRSort(sort)
