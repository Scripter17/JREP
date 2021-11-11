# JREP

JREP is a work-in-process replacement/companion for the Linux command GREP designed to be cross-platform, feature rich, and very intuitive.

Basically I got annoyed at the lack of GREP for Windows and decided to do it myself.

The current --help message:

```
usage: jrep.py [-h] [--string] [--no-duplicates] [--file FILE [FILE ...]]
               [--glob GLOB [GLOB ...]] [--stdin-files | --stdin-globs]
               [--name-regex NAME_REGEX [NAME_REGEX ...]]
               [--full-name-regex FULL_NAME_REGEX [FULL_NAME_REGEX ...]]
               [--name-anti-regex NAME_ANTI_REGEX [NAME_ANTI_REGEX ...]]
               [--full-name-anti-regex FULL_NAME_ANTI_REGEX [FULL_NAME_ANTI_REGEX ...]]
               [--file-regex FILE_REGEX [FILE_REGEX ...]]
               [--file-anti-regex FILE_ANTI_REGEX [FILE_ANTI_REGEX ...]]
               [--sort SORT] [--no-headers] [--print-directories]
               [--print-file-names] [--print-full-paths] [--print-posix-paths]
               [--dont-print-matches] [--print-match-offset]
               [--print-match-range] [--replace REPLACE [REPLACE ...]]
               [--sub SUB [SUB ...]] [--escape] [--count COUNT [COUNT ...]]
               [--limit LIMIT [LIMIT ...]] [--depth-first]
               [--print-whole-lines] [--print-non-matching-files] [--no-warn]
               [--weave-matches] [--strict-weave] [--verbose]
               [regex ...]

positional arguments:
  regex                 Regex(es) to process matches for

options:
  -h, --help            show this help message and exit
  --string, -s          Test for strings instead of regex
  --no-duplicates, -D   Don't print duplicate matches
  --file FILE [FILE ...], -f FILE [FILE ...]
                        The file(s) to check
  --glob GLOB [GLOB ...], -g GLOB [GLOB ...]
                        The glob(s) to check
  --stdin-files, -F     Treat STDIN as a list of files
  --stdin-globs, -G     Treat STDIN as a list of globs
  --name-regex NAME_REGEX [NAME_REGEX ...], -t NAME_REGEX [NAME_REGEX ...]
                        Regex to test relative file names for
  --full-name-regex FULL_NAME_REGEX [FULL_NAME_REGEX ...], -T FULL_NAME_REGEX [FULL_NAME_REGEX ...]
                        Regex to test absolute file names for
  --name-anti-regex NAME_ANTI_REGEX [NAME_ANTI_REGEX ...]
                        Like --name-regex but excludes file names that match
  --full-name-anti-regex FULL_NAME_ANTI_REGEX [FULL_NAME_ANTI_REGEX ...]
                        Like --full-name-regex but excludes file names that
                        match
  --file-regex FILE_REGEX [FILE_REGEX ...]
                        Regexes to test file contents for
  --file-anti-regex FILE_ANTI_REGEX [FILE_ANTI_REGEX ...]
                        Like --file-regex but excludes files that match
  --sort SORT, -S SORT  Sort files by ctime, mtime, atime, name, or size.
                        Prefix key with "r" to reverse. A windows-esque
                        "blockwise" sort is also available (todo: document)
  --no-headers, -H      Don't print match: or file: before lines
  --print-directories, -d
                        Print names of explored directories
  --print-file-names, -n
                        Print file names as well as matches
  --print-full-paths, -p
                        Print full file paths
  --print-posix-paths, -P
                        Print replace \ with / in file paths
  --dont-print-matches, -N
                        Don't print matches (use with --print-file-names to
                        only print names)
  --print-match-offset, -o
                        Print the match offset (ignores -H)
  --print-match-range, -O
                        Print the match range (implies -o)
  --replace REPLACE [REPLACE ...], -r REPLACE [REPLACE ...]
                        Regex replacement
  --sub SUB [SUB ...], -R SUB [SUB ...]
                        re.sub argument pairs after --replace is applied
  --escape, -e          Replace \, carriage returns, and newlines with \\, \r,
                        and \n
  --count COUNT [COUNT ...], -c COUNT [COUNT ...]
                        Count match/file/dir per file, dir, and/or total (Ex:
                        --count fm df)
  --limit LIMIT [LIMIT ...], -l LIMIT [LIMIT ...]
                        Count match/file/dir per file, dir, and/or total (Ex:
                        --limit fm=1 td=5)
  --depth-first         Enter subdirectories before processing files
  --print-whole-lines   Print whole lines like FINDSTR
  --print-non-matching-files
                        Print file names with no matches
  --no-warn             Don't print warning messages
  --weave-matches, -w   Weave regex matchdes
  --strict-weave, -W    Only print full match sets
  --verbose, -v         Verbose info
```

Some example snippits:

- `jrep -g *.py -NCH` - Count all `.py` files in a directory
- `jrep -g */*.mp4 -nNd --limit df=5 | jrep "Directory: (.+)(\nFile: .+){5}" -r \1 -H` - List all directories with 5 or more `.mp4` files
