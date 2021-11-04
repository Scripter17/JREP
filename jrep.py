import argparse, os, sys, re, glob, mmap, copy, itertools

"""
	JREP
	Made by Github@Scripter17 / Reddit@Scripter17 / Twitter@Scripter171
	Released under the "Don't Be a Dick" public license
	https://dbad-license.org
	(Can be treated as public domain if your project requires that)
"""

parser=argparse.ArgumentParser()

parser.add_argument("regex"                 ,       nargs="?", default="", help="Regex to process matches for")
parser.add_argument("--string"              , "-s", action="store_true"  , help="Test for strings instead of regex")
parser.add_argument("--no-duplicates"       , "-D", action="store_true"  , help="Don't print duplicate matches")

parser.add_argument("--file-regex"          ,       nargs="+", default=[], help="Regexes files must match to be processed (unimplemented)")
parser.add_argument("--file-anti-regex"     ,       nargs="+", default=[], help="Regexes for files to not match")

parser.add_argument("--file"                , "-f", nargs="+", default=[], help="The file(s) to check")
parser.add_argument("--glob"                , "-g", nargs="+", default=[], help="The glob(s) to check")

_stdin=parser.add_mutually_exclusive_group()
_stdin.add_argument("--stdin-files"         , "-F", action="store_true"  , help="Treat STDIN as a list of files")
_stdin.add_argument("--stdin-globs"         , "-G", action="store_true"  , help="Treat STDIN as a list of globs")

parser.add_argument("--name-regex"          , "-t", nargs="+", default=[], help="Regex to test against relative file name")
parser.add_argument("--full-name-regex"     , "-T", nargs="+", default=[], help="Regex to test against absolute file name")
parser.add_argument("--name-anti-regex"     ,       nargs="+", default=[], help="Like --name-regex      but excludes file names that match")
parser.add_argument("--full-name-anti-regex",       nargs="+", default=[], help="Like --full-name-regex but excludes file names that match")

parser.add_argument("--sort"                , "-S",                        help="Sort files by ctime, mtime, atime, name, or size. Prefix key with \"r\" to reverse")
parser.add_argument("--no-headers"          , "-H", action="store_true"  , help="Don't print match: or file: before lines")
parser.add_argument("--print-directories"   , "-d", action="store_true"  , help="Print names of explored directories")
parser.add_argument("--print-file-names"    , "-n", action="store_true"  , help="Print file names as well as matches")
parser.add_argument("--print-full-paths"    , "-p", action="store_true"  , help="Print full file paths")
parser.add_argument("--print-posix-paths"   , "-P", action="store_true"  , help="Print C:/stuff instead of C:\\stuff")
parser.add_argument("--dont-print-matches"  , "-N", action="store_true"  , help="Don't print matches (use with -n to only print names)")
parser.add_argument("--print-match-offset"  , "-o", action="store_true"  , help="Print the match offset (ignores -H)")
parser.add_argument("--print-match-range"   , "-O", action="store_true"  , help="Print the match range  (implies -o)")
parser.add_argument("--count"               , "-c", action="store_true"  , help="Count matches per file")
parser.add_argument("--total-count"         , "-C", action="store_true"  , help="Total --count of all files")

parser.add_argument("--replace"             , "-r",                        help="Regex replacement")
parser.add_argument("--sub"                 , "-R", nargs="+", default=[], help="re.sub argument pairs after -r")
parser.add_argument("--escape"              , "-e", action="store_true"  , help="Replace \\, carriage returns, and newlines with \\\\, \\r, and \\n")

parser.add_argument("--file-match-limit"    , "--fml", type=int, default=0, help="Max matches per file")
parser.add_argument("--dir-match-limit"     , "--dml", type=int, default=0, help="Max matches per directory")
parser.add_argument("--total-match-limit"   , "--tml", type=int, default=0, help="Max matches overall")
parser.add_argument("--dir-file-limit"      , "--dfl", type=int, default=0, help="Max files per directory")
parser.add_argument("--total-file-limit"    , "--tfl", type=int, default=0, help="Max files overall")

parser.add_argument("--verbose"             , "-v", action="store_true"  , help="Verbose info")
parsedArgs=parser.parse_args()

if parsedArgs.verbose:
	print("JREP preview version")
	print(parsedArgs)

# Simple implementation of --escape
if parsedArgs.escape:
	parsedArgs.sub.extend(["\\", "\\\\", "\r", "\\r", "\n", "\\n"])

# Dumb output fstring generation stuff
_header=not parsedArgs.no_headers
_mOffs1=parsedArgs.print_match_offset or parsedArgs.print_match_range
_mOffs2=parsedArgs.print_match_range
_mRange=("{range[0]:08x}"*_mOffs1)+("-{range[1]:08x}"*_mOffs2)
_mAt=_header and _mOffs1
_mRange=(" at "*_mAt) + (_mRange) + (": "*(_header or _mRange!=""))

# Output fstrings to make later usage easier
ofmt={
	"dname": (("Directory: "  *_header)+        "{dname}") * parsedArgs.print_directories,
	"fname": (("File: "       *_header)+        "{fname}") * parsedArgs.print_file_names,
	"match": (("Match"        *_header)+_mRange+"{match}") * (not parsedArgs.dont_print_matches),
	"count": (("Count: "      *_header)+        "{count}") * parsedArgs.count,
	"total": (("Total count: "*_header)+        "{count}") * parsedArgs.total_count,
}

def sortFiles(files, key=None):
	"""
		Sorts files if --sort is present
		Note that sorting files requires loading all file names in a directory into memory
		Also it's just generally slow
	"""
	if key==None:
		return files

	sorts={
		"ctime": lambda x:float("inf") if x["name"]=="-" else os.stat(x["name"]).st_ctime,
		"mtime": lambda x:float("inf") if x["name"]=="-" else os.stat(x["name"]).st_mtime,
		"atime": lambda x:float("inf") if x["name"]=="-" else os.stat(x["name"]).st_atime,
		"name" : lambda x:x["name"],
		"size" : lambda x:len(x["data"])
	}
	for sort in list(sorts.keys()):
		# Scopes suck
		sorts["r"+sort]=(lambda _sort:lambda x:-sorts[_sort](x))(sort)

	return sorted(files, key=sorts[key])

class JSObj:
	"""
		[J]ava[S]cript [Obj]ects
		JavaScript allows both {"a":1}.a and {"a":1}["a"]
		This class mimicks that
	"""
	def __init__(self, obj): object.__setattr__(self, "obj", copy.copy(obj))

	def __getattr__(self, key):      return self.obj[key]
	def __setattr__(self, key, val):        self.obj[key]=val
	def __delattr__(self, key):      del    self.obj[key]

	def __getitem__(self, key):      return self.obj[key]
	def __setitem__(self, key, val):        self.obj[key]=val
	def __delitem__(self, key):      del    self.obj[key]

def findAllSubs(pattern, replace, string):
	"""
		re.sub but yield all replaced substrings instead of returning the final string
		This is a very slow function but it works... somehow
	"""
	offs=0
	last=string
	for index, match in enumerate(re.finditer(pattern, string)):
		subbed=re.sub(pattern, replace, string, count=index+1)
		loffs=offs
		offs+=len(subbed)-len(last)
		yield JSObj({
			"span": lambda:(loffs+match.span()[0],offs+match.span()[1]),
			0     :  subbed[loffs+match.span()[0]:offs+match.span()[1]]
		})
		last=subbed

def getFiles():
	"""
		Yields files selected with --file and --glob as {"file":filename, "data":mmapFile/bytes}
		Stdin has a filename of -
		Empty files and stdin use a bytes object instead of mmap
	"""
	def _getFiles():
		"""
			Get a raw list of files selected with --file and --glob
			This is just here so I don't have to write the mmap code twice
			Probably could replace the array addition with a few `yield from`s
		"""
		if not os.isatty(sys.stdin.fileno()):
			if parsedArgs.stdin_files:
				parsedArgs.file=sys.stdin.read().splitlines()+parsedArgs.file
			elif parsedArgs.stdin_globs:
				parsedArgs.glob=sys.stdin.read().splitlines()+parsedArgs.glob
		yield from parsedArgs.file # Whoever decided to add yield from: Thank you
		for pattern in parsedArgs.glob:
			yield from glob.iglob(pattern, recursive=True)

	def _processDir(dname):
		"""
			Print directory names if --print-directories is specified
		"""
		if os.path.isfile(dname):
			dname=os.path.dirname(dname)
		dname=dname or "."
		if parsedArgs.print_full_paths:  dname=os.path.realpath(dname)
		if parsedArgs.print_posix_paths: dname=dname.replace("\\", "/")
		if parsedArgs.print_directories and dname not in exploredDirs:
			print(ofmt["dname"].format(dname=dname))
			exploredDirs.append(dname)

	# Add stdin as a file
	if not os.isatty(sys.stdin.fileno()) and not parsedArgs.stdin_files and not parsedArgs.stdin_globs:
		yield {"name":"-", "data":sys.stdin.read().encode(errors="ignore")}

	exploredDirs=[]
	for file in _getFiles():
		if parsedArgs.verbose:
			print(f"Verbose: Processing file \"{file}\"")

		_processDir(file) # Handle --print-directories

		if os.path.isfile(file):
			if parsedArgs.dont_print_matches and\
			   not parsedArgs.regex and\
			   not parsedArgs.count and\
			   not parsedArgs.total_count and\
			   not parsedArgs.file_match_limit and\
			   not parsedArgs.dir_match_limit and\
			   not parsedArgs.total_match_limit and\
			   not parsedArgs.file_regex and\
			   not parsedArgs.file_anti_regex:
				# Does the file content matter? No? Ignore it then
				yield {"name":file, "data":b""}
			else:
				try:
					with open(file) as f:
						# Stream data from file instead of loading a 2.6GB file into RAM
						try:
							mmapFile=mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
						except ValueError:
							mmapFile=b""
						yield {"name": file, "data":mmapFile}
				except Exception as AAAAA:
					print(f"Warning: Cannot process \"{file}\" because of \"{AAAAA}\"", file=sys.stderr)

# Abbreviations to make my editor not show a horizontal scrollbar (my version of PEP8)
_FML=parsedArgs.file_match_limit
_DML=parsedArgs.dir_match_limit
_TML=parsedArgs.total_match_limit
_DFL=parsedArgs.dir_file_limit
_TFL=parsedArgs.total_file_limit

# Tracking stuffs
matchedStrings=[] # --no-duplicates handler
dirData={} # --file-limit and --dir-match-limit
totalMatches=0

for fileIndex, file in enumerate(sortFiles(getFiles(), key=parsedArgs.sort), start=1):
	if parsedArgs.verbose:
		print(f"Verbose: Processing {file}")

	# For both --file-limit and --dir-match-limit
	fileDir=os.path.dirname(file["name"])
	if fileDir not in dirData:
		if parsedArgs.verbose:
			print(f"Verbose: Adding {fileDir} to dirData")
		dirData[fileDir]={"files":0, "matches":0}

	# Handle --file-limit
	# Really slow on big directories
	if (_DFL!=0 and dirData[fileDir]["files"]==_DFL) or (_DML!=0 and dirData[fileDir]["matches"]>=_DML):
		continue
	dirData[fileDir]["files"]+=1

	# Handle --name-regex, --full-name-regex, --name-anti-regex, and--full-name-anti-regex
	if not (all([re.search(x,                  file["name"] ) for x in parsedArgs.name_regex          ]) and\
	        all([re.search(x, os.path.realpath(file["name"])) for x in parsedArgs.full_name_regex     ]) and\
	   not  any([re.search(x,                  file["name"] ) for x in parsedArgs.name_anti_regex     ]) and\
	   not  any([re.search(x, os.path.realpath(file["name"])) for x in parsedArgs.full_name_anti_regex])):
		# Really should make how this works configurable
		if parsedArgs.verbose:
			print(f"Verbose: File name \"{file['name']}\" or file path \"{os.path.realpath(file['name'])}\" failed the name regexes")
		continue

	# Main matching stuff
	try:
		printedName=False

		# Handle --file-regex and --file-anti-regex
		vibeCheckFailed=False
		# --file-regex
		for fileRegex in parsedArgs.file_regex:
			if not re.search(fileRegex.encode(errors="ignore"), file["data"]):
				vibeCheckFailed=True
				break
		if vibeCheckFailed:
			continue
		# --file-anti-regex
		for fileAntiRegex in parsedArgs.file_anti_regex:
			if re.search(fileAntiRegex.encode(errors="ignore"), file["data"]):
				vibeCheckFailed=True
				break
		if vibeCheckFailed:
			continue

		# Main regex handling
		# Turn regex into bytes
		regex=parsedArgs.regex.encode(errors="ignore")

		# Probably a bad idea
		if parsedArgs.string:
			regex=re.escape(regex)

		# Arguably should be an elif but this is easier to mentally process
		if parsedArgs.replace!=None:
			matches=findAllSubs(regex, parsedArgs.replace.encode(errors="ignore"), file["data"])
		else:
			matches=re.finditer(regex, file["data"])

		# Process matches
		matchIndex=0 # Just makes --count stuff easier
		for matchIndex, match in enumerate(matches, start=1):
			# Print file name
			if parsedArgs.print_file_names and not printedName:
				#print(fHeader+(os.path.realpath(file["name"]) if parsedArgs.print_full_paths else file["name"]))
				fname=file["name"]
				if parsedArgs.print_full_paths:  fname=os.path.realpath(fname)
				if parsedArgs.print_posix_paths: fname=fname.replace("\\", "/")
				print(ofmt["fname"].format(fname=fname))
				printedName=True

			totalMatches+=1
			dirData[fileDir]["matches"]+=1

			# Quick optimization for when someone just wants filenames that have a match
			if parsedArgs.dont_print_matches and\
			   not parsedArgs.count and\
			   not parsedArgs.total_count and\
			   not _FML and not _DML and not _TML:
				break

			# Handle --sub
			# TYSM mCoding for explaining how zip works
			# (zip(*arr) is a bit like transposing arr (arr[y][x] becomes arr[x][y]))
			for pair in zip(parsedArgs.sub[0::2], parsedArgs.sub[1::2]):
				match=JSObj({
					0     : re.sub(pair[0].encode(), pair[1].encode(), match[0]),
					"span": match.span
				})

			# Print matches
			if not parsedArgs.dont_print_matches and match[0].decode() not in matchedStrings:
				#print(mHeader+match[0].decode())
				print(ofmt["match"].format(range=match.span(), match=match[0].decode()))

			# Handle --no-duplicates
			if parsedArgs.no_duplicates:
				matchedStrings.append(match[0].decode())

			# Handle --match-limit, --dir-match-limit, and --total-match-limit
			if (_FML!=0 and matchIndex>=_FML) or\
			   (_DML!=0 and dirData[fileDir]["matches"]>=_DML) or\
			   (_TML!=0 and totalMatches>=_TML):
				break

		# Print match count (--count)
		if parsedArgs.count and matchIndex:
			print(ofmt["count"].format(count=matchIndex))

	except Exception as AAAAA:
		print(f"Warning: Cannot process \"{file}\" because of \"{AAAAA}\" on line {sys.exc_info()[2].tb_lineno}", file=sys.stderr)

	# Hanlde --total-match-limit and --total-file-limit
	if (_TML!=0 and totalMatches>=_TML) or (_TFL!=0 and fileIndex>=_TFL):
		break

# Print total match count (--total-count)
if parsedArgs.total_count:
	print(ofmt["total"].format(count=totalMatches))
