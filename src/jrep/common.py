from typing import *

ofmt          : Dict[str, str]=None # type: ignore
regex         : Any           =None # type: ignore
enhancedEngine: bool          =None # type: ignore

def init(parsedArgs):
	global ofmt, regex, enhancedEngine
	_header=not parsedArgs.no_headers
	_mOffs1=parsedArgs.print_match_offset or parsedArgs.print_match_range
	_mOffs2=parsedArgs.print_match_range
	_mRange=("{range[0]:08x}"*_mOffs1)+("-{range[1]:08x}"*_mOffs2)
	_mAt=_header and _mOffs1
	_mRange=(" at "*_mAt) + (_mRange) + (": "*(_header or _mRange!=""))
	ofmt={
		"dname"        : b"Directory: "                              *_header,
		"fname"        : b"File: "                                   *_header,
		"match"        : ("Match (R{regexIndex})"                    *_header)+_mRange,
		"rundata"      : ("runData: "                                *_header)+"{runData}",
		"countFiltered": ("{filter} {cat} {subCat} (R{regexIndex}): "*_header)+"{count}",
		"countTotal"   : ("{cat} {subCat} (R{regexIndex}): "         *_header)+"{value}",
	} # Type: ignore

	if parsedArgs.enhanced_engine:
		from regex import regex
		enhancedEngine=True
