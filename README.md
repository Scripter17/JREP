# JREP

JREP is a general-purpose command line utility that takes the basic concept of GREP and transforms it into an infinitely more versatile tool fit for the modern world.

Basically I couldn't find a good GREP for windows and GREP itself kinda sucks so I did it myself. Excpect dumb bodges and messy code despite my efforts to keep both to a minimum.

JREP is released under the "Don't Be a Dick" public license. Please see [dbad-license.org](https://dbad-license.org) or [LICENSE](LICENSE) for more details.

All images used for testing have been provided by wikimedia under Crative Commons.

To install via PIP: [`pip install JREP`](https://pypi.org/project/JREP/)

To install from GitHub: `git clone https://github.com/Scripter17/JREP & pip install ./JREP`

Check [here](#compatibility) for compatibility info

The current output of `jrep --help`:  
For details, [check below](#extended-help-messages)

<!--<HELP MSG>-->
```
usage: jrep [--help [topic]] [--enhanced-engine] [--file FILE [FILE ...]]
            [--glob GLOB [GLOB ...]] [--include-dirs]
            [--stdin-files | --stdin-globs | --stdin-anti-match-strings]
            [--no-duplicates] [--no-name-duplicates]
            [--name-regex Regex [Regex ...]]
            [--name-anti-regex Regex [Regex ...]]
            [--name-ignore-regex Regex [Regex ...]]
            [--full-name-regex Regex [Regex ...]]
            [--full-name-anti-regex Regex [Regex ...]]
            [--full-name-ignore-regex Regex [Regex ...]]
            [--name-glob Glob [Glob ...]] [--name-anti-glob Glob [Glob ...]]
            [--name-ignore-glob Glob [Glob ...]]
            [--full-name-glob Glob [Glob ...]]
            [--full-name-anti-glob Glob [Glob ...]]
            [--full-name-ignore-glob Glob [Glob ...]]
            [--dir-name-regex Regex [Regex ...]]
            [--dir-name-anti-regex Regex [Regex ...]]
            [--dir-name-ignore-regex Regex [Regex ...]]
            [--dir-full-name-regex Regex [Regex ...]]
            [--dir-full-name-anti-regex Regex [Regex ...]]
            [--dir-full-name-ignore-regex Regex [Regex ...]]
            [--file-regex Regex [Regex ...]]
            [--file-anti-regex Regex [Regex ...]]
            [--file-ignore-regex Regex [Regex ...]]
            [--match-regex Regex [Regex ...]]
            [--match-anti-regex Regex [Regex ...]]
            [--match-ignore-regex Regex [Regex ...]] [--sort SORT]
            [--sort-dir SORT_DIR] [--sort-regex Regex [Regex ...]]
            [--no-headers] [--print-dir-names] [--print-file-names]
            [--print-full-paths] [--print-posix-paths] [--dont-print-matches]
            [--print-match-offset] [--print-match-range]
            [--replace Regex [Regex ...]] [--sub Regex [Regex ...]]
            [--name-sub Regex [Regex ...]] [--dir-name-sub Regex [Regex ...]]
            [--escape] [--count COUNT [COUNT ...]] [--limit LIMIT [LIMIT ...]]
            [--depth-first] [--glob-root-dir GLOB_ROOT_DIR]
            [--print-failed-files] [--json] [--no-warn] [--hard-warn]
            [--weave-matches] [--strict-weave] [--no-exec]
            [--pre-match-exec cmd] [--match-exec cmd]
            [--if-match-exec-before cmd] [--if-match-exec-after cmd]
            [--if-no-match-exec-after cmd] [--pre-file-exec cmd]
            [--file-exec cmd] [--if-file-exec-before cmd]
            [--if-file-exec-after cmd] [--if-no-file-exec-after cmd]
            [--pre-dir-exec cmd] [--dir-exec cmd] [--if-dir-exec-before cmd]
            [--if-dir-exec-after cmd] [--if-no-dir-exec-after cmd]
            [--order ORDER [ORDER ...]] [--no-flush] [--force-flush]
            [--verbose]
            [Regex ...]

options:
  --help [topic], -h [topic]            show this help message and exit OR use
                                        `--help [topic]` for help with [topic]

Global behaviour:
  --enhanced-engine, -E                 Use alternate regex engine from
                                        https://pypi.org/project/regex/

Files and regexes:
  Regex                                 Regex(es) to process matches for
                                        (reffered to as "get regexes")
                                        
                                        
  --file FILE [FILE ...], -f FILE [FILE ...]
                                        A list of files to check
  --glob GLOB [GLOB ...], -g GLOB [GLOB ...]
                                        A list of globs to check
  --include-dirs                        Process directories as files
                                        
  --stdin-files, -F                     Treat STDIN as a list of files
  --stdin-globs, -G                     Treat STDIN as a list of globs
  --stdin-anti-match-strings            Treat STDIN as a list of strings to
                                        not match

Filters:
  --no-duplicates, -D                   Don't print duplicate matches (See
                                        also: --order)
  --no-name-duplicates                  Don't process files whose names have
                                        already been processed (takes --name-
                                        sub, --print-full-paths and --print-
                                        posix-paths)
                                        
  --name-regex Regex [Regex ...], -t Regex [Regex ...]
                                        If a file name matches all supplied
                                        regexes, keep going. Otherwise
                                        continue
  --name-anti-regex Regex [Regex ...], -T Regex [Regex ...]
                                        Like --name-regex but excludes file
                                        names that match any of the supplied
                                        regexes
  --name-ignore-regex Regex [Regex ...]
                                        Like --name-anti-regex but doesn't
                                        contribute to --count *-failed-files
  --full-name-regex Regex [Regex ...]   Like --name-regex but for absolute
                                        file paths (C:/xyz instead of xyz)
  --full-name-anti-regex Regex [Regex ...]
                                        Like --name-anti-regex but applied to
                                        full file paths
  --full-name-ignore-regex Regex [Regex ...]
                                        Like --full-name-anti-regex but
                                        doesn't contribute to --count
                                        *-failed-files
                                        
  --name-glob Glob [Glob ...]           If a file name matches all supplied
                                        globs, keep going. Otherwise continue
  --name-anti-glob Glob [Glob ...]      Like --name-glob but excludes file
                                        names that match any of the supplied
                                        globs
  --name-ignore-glob Glob [Glob ...]    Like --name-anti-glob but doesn't
                                        contribute to --count *-failed-files
  --full-name-glob Glob [Glob ...]      Like --name-glob but for absolute file
                                        paths (C:/xyz instead of xyz)
  --full-name-anti-glob Glob [Glob ...]
                                        Like --name-anti-glob but applied to
                                        full file paths
  --full-name-ignore-glob Glob [Glob ...]
                                        Like --full-name-anti-glob but doesn't
                                        contribute to --count *-failed-files
                                        
  --dir-name-regex Regex [Regex ...]    If a directory name matches all
                                        supplied regexes, enter it. Otherwise
                                        continue
  --dir-name-anti-regex Regex [Regex ...]
                                        Like --dir-name-regex but excludes
                                        directories that match any of the
                                        supplied regexes
  --dir-name-ignore-regex Regex [Regex ...]
                                        Like --dir-name-anti-regex but doesn't
                                        contribute to --count total-failed-
                                        dirs
  --dir-full-name-regex Regex [Regex ...]
                                        Like --dir-name-regex but for absolute
                                        directory paths (C:/xyz instead of
                                        xyz)
  --dir-full-name-anti-regex Regex [Regex ...]
                                        Like --dir-name-anti-regex but applied
                                        to full directory paths
  --dir-full-name-ignore-regex Regex [Regex ...]
                                        Like --dir-full-name-anti-regex but
                                        doesn't contribute to --count total-
                                        failed-dirs
                                        
  --file-regex Regex [Regex ...]        Regexes to test file contents for
  --file-anti-regex Regex [Regex ...]   Like --file-regex but excludes files
                                        that match of the supplied regexes
  --file-ignore-regex Regex [Regex ...]
                                        Like --file-anti-regex but doesn't
                                        contribute to --count *-failed-files
                                        
  --match-regex Regex [Regex ...]       Groups are split along lone *. Matches
                                        from the Nth get regex are tested with
                                        the Nth group
  --match-anti-regex Regex [Regex ...]  Like --match-regex but excludes
                                        matches that match any of the supplied
                                        regexes
  --match-ignore-regex Regex [Regex ...]
                                        Like --match-anti-regex but doesn't
                                        contribute to --count *-failed-matches

Sorting:
  --sort SORT, -S SORT                  Sort files by ctime, mtime, atime,
                                        name, or size. Prefix key with "r" to
                                        reverse. A windows-esque "blockwise"
                                        sort is also available. Run jrep
                                        --help blockwise for more info
  --sort-dir SORT_DIR                   --sort on a per-directory basis
  --sort-regex Regex [Regex ...]        Regexes to apply to file names keys
                                        (like --replace) for purposes of
                                        sorting (EXPERIMENTAL)

Output:
  --no-headers, -H                      Don't print match: or file: before
                                        lines
                                        
  --print-dir-names, -d                 Print names of explored directories
  --print-file-names, -n                Print file names as well as matches
  --print-full-paths, -p                Print full file paths
  --print-posix-paths, -P               Replace \ with / when printing file
                                        paths
  --dont-print-matches, -N              Don't print matches (use with --print-
                                        file-names to only print names)
  --print-match-offset, -o              Print where the match starts in the
                                        file as a hexadecimal number (ignores
                                        -H)
  --print-match-range, -O               Print where the match starts and ends
                                        in the file as a hexadecimal number
                                        (implies -o)

Replace/Sub:
  --replace Regex [Regex ...], -r Regex [Regex ...]
                                        Regex replacement
  --sub Regex [Regex ...], -R Regex [Regex ...]
                                        re.sub argument pairs after --replace
                                        is applied. Run jrep.py --help sub for
                                        more info
  --name-sub Regex [Regex ...]          Applies --sub to file names. A lone *
                                        separates subsitutions for y/z and
                                        C:/x/y/z
  --dir-name-sub Regex [Regex ...]      --name-sub but for directory names
  --escape, -e                          Escape back slashes, newlines,
                                        carriage returns, and non-printable
                                        characters

Misc.:
  --count COUNT [COUNT ...], -c COUNT [COUNT ...]
                                        Count match/file/dir per file, dir,
                                        and/or total (Ex: --count fm dir-
                                        files)
  --limit LIMIT [LIMIT ...], -l LIMIT [LIMIT ...]
                                        Limit match/file/dir per file, dir,
                                        and/or total (Ex: --limit filematch=1
                                        total_dirs=5)
                                        
  --depth-first                         Enter subdirectories before processing
                                        files
  --glob-root-dir GLOB_ROOT_DIR         Root dir to run globs in (JANK)
                                        
  --print-failed-files                  Print file names even if they fail
                                        (Partially broken)
  --json, -j                            Print output as JSON
  --no-warn                             Don't print warning messages
  --hard-warn                           Throw errors instead of warnings
  --weave-matches, -w                   Weave regex matchdes (print first
                                        results for each get regex, then
                                        second results, etc.)
  --strict-weave, -W                    Only print full weave sets

Exec:
  --no-exec                             Don't run any exec functions. Useful
                                        if using user input (STILL NOT SAFE)
                                        
  --pre-match-exec cmd                  Command to run before printing each
                                        match
  --match-exec cmd                      Command to run after printing each
                                        match
  --if-match-exec-before cmd            Command to run as soon as least one
                                        match passes
  --if-match-exec-after cmd             Command to run at the end if at least
                                        one match passed
  --if-no-match-exec-after cmd          Command to run at the end if at no
                                        matches passed
                                        
  --pre-file-exec cmd                   Command to run before printing each
                                        file name
  --file-exec cmd                       Command to run after printing each
                                        file name
  --if-file-exec-before cmd             Command to run as soon as least one
                                        file passes
  --if-file-exec-after cmd              Command to run at the end if at least
                                        one file passed
  --if-no-file-exec-after cmd           Command to run at the end if at no
                                        files passed
                                        
  --pre-dir-exec cmd                    Command to run before printing each
                                        dir name
  --dir-exec cmd                        Command to run after printing each dir
                                        name
  --if-dir-exec-before cmd              Command to run as soon as least one
                                        dir passes
  --if-dir-exec-after cmd               Command to run at the end if at least
                                        one dir passed
  --if-no-dir-exec-after cmd            Command to run at the end if at no
                                        dirs passed

Debugging/Advanced:
  --order ORDER [ORDER ...]             The order in which modifications to
                                        matches are applied. Run jrep --help
                                        order for more info
  --no-flush                            Improves speed by disabling manually
                                        flushing the stdout buffer (ideal for
                                        chaining commands)
  --force-flush                         Always flush STDOUT (slow)
  --verbose, -v                         Verbose info
The following have extended help that can be seen with --help [topic]: sub, blockwise, order, exec
```
<!--</HELP MSG>-->

# Extended help messages

These can be accessed by doing `jrep --help [topic]` where `[topic]` is the part in parenthesis

<!--<EXTHELP MSGS>-->
## (`sub`) --sub advanced usage
The easiest way to explain advanced uses of `--sub` is to give an example. So take `--sub a ? b ? c d e f + x ? y z * ? t ? e d * abc xyz` as an example.    
What it means is the following
  
- `a ? b ? c d e f`: If a match from get regex 0 matches `a` and not `b`, replace `c` with `d` and `e` with `f`  
- `+`: New conditions but stay on the same get regex  
- `x ? y z`: If a match from get regex 0 matches `x`, replace `y` with `z`  
- `*`: Move on to the next get regex  
- `? t ? e d`: If a match from get regex 1 does't match `t`, replace `e` with `d`  
- `*`: Move on to the next get regex  
- `abc xyz`: Replace `abc` with `xyz` without any conditions  
  
Obviously 99% of use cases don't need conditionals at all so just doing `--sub abc def * uvw xyz` is sufficient

## (`blockwise`) Blockwise sorting
A generic sort function will think "file10.jpg" comes before "file2.jpg"  
Windows, on the other hand, has code that treats the number part as a number  
Blockwise sort mimics this behaviour by  
1. Splitting filenames into groups of number and non-number characters. Ex. `abc123def456.jpg` -> `["abc", "123", "def", "456", ".jpg"]`  
2. When comparing 2 filenames, compare the first element ("block") of both name's lists according to the following two rules
	1. If either block is made of non-number characters, compare the two blocks as strings  
	2. If both blocks are numbers, compare them as numbers  
  
The end result is that file2.jpg is correctly placed before file10.jpg

## (`order`) `--order` usage
`--order` determines the order of functions that process matches  
- The default value for `--order` is replace, match-whole-lines, sub, stdin-anti-match-strings, match-regex, no-name-duplicates, no-duplicates, print-dir-name, print-name, print-match  
- Changing the order of `sub`, `replace`, and `match-whole-lines` will mostly "work" but the output will make next to no sense  
- The main purpose of this is to move `match-regex` and `no-duplicates` to earlier in the chain

## (`exec`) Using the `--exec` family of options
Usage looks like `--exec "echo {}"` or just `--exec "echo"`  
To use the filename/dir multiple times use `{0}` (this is for future proofing)  
`--match-exec`/`--exec`: after  printing matches  
`--pre-match-exec`: before printing matches  
  
`--match-exec`: after  printing file names  
`--pre-match-exec`: before printing file names  
`--if-file-exec-before`: Run once before the first file is processed  
`--if-file-exec-after`: Run once after the last file is processed  
`--if-no-file-exec-after`: Run at the end if no file is ever processed  
  
`--dir-exec`: after  printing directory names  
`--pre-dir-exec`: before printing directory names  
`--if-dir-exec-before`: Run once before the first dir is processed  
`--if-dir-exec-after`: Run once after the last dir is processed  
`--if-no-dir-exec-after`: Run at the end if no dir is ever processed
<!--</EXTHELP MSGS>-->

# Compatibility

Currently due to [technical limitations](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#choosing-github-hosted-runners) I can only do automatic testing for Ubuntu 20.04, Windows Server 2022, and macOS Big Sur 11

The end goal is for JREP to 100% work on
- Windows 7 through 11
- The past decade of every major Linux distro
- The past decade of Mac machines

I don't think there's much (if any) platform-specific jank in JREP but it'll take a while to confirm that
