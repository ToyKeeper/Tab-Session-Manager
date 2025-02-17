# ToyKeeper's Jank Plus Ultra Web Server For Tab Session Manager Exports

Phew!  That's a mouthful.  Maybe this project should have a better name.  But
then, it needs a better *everything else* too.

This is a very primitive web server which simply accepts raw json from the Tab
Session Manager browser extension, and saves it to local files on disk.
Because TSM's built-in feature to save local files doesn't work.  So this is
a workaround for that problem.

Also included is a hacked-up script to convert those json files to
a human-friendly plain text format.

This project makes no attempt at authentication or encryption or any form of
privacy or safety.  The only thing it does to prevent abuse is hard-coding the
server URL to localhost.  If you need more security than that, this is not the
hack you're looking for.  It is simply the minimum amount of code necessary to
work around TSM's broken file export function.


## Requirements

The server needs:

- Python 3.7 or newer
- python3-flask
- python3-flask-cors
- python3-zstd (optional, but recommended)

The json2txt conversion script needs:

- Python 3.7 or newer
- python3-zstd (optional, but recommended)

Why Python3.7?  Because that's when the "dict" object type was upgraded to be
an OrderedDict instead of unordered.  TSM stores tabs in a dict instead of
a list, which I consider to be a mistake, and it results in tabs being in the
wrong order sometimes.  That's complicated to fix though, so I recommend at
least preserving what semblance of order remains.  And for that, Python3.7's
ordered dicts are needed.

In my testing, TSM's export files still have tabs in the wrong order
sometimes... but they are at least in a *consistent* order.  So this hack
attempts to preserve that order.


## Installation

Not much is needed.  Run the server, install the browser extension, and maybe
put the json2txt script in your path somewhere if you want to use it.

To run the server:

- `cd tk-server`
- `./server.py`

It should save files to `~/.tsm/` whenever it receives any session data.

To install the browser extension:

- Refer to TSM's [main readme file](../README.md).  You'll probably have to
  install npm and build the extension file with `npm run build` or similar.

To use the json2txt script:

- Simply run `path/to/json2txt.py path/to/myfile.json.zst` and it should dump
  the text to stdout.  Redirect it to a file if you want to save it.  For
  example:
  - `~/src/tsm/tk-server/json2txt.py ~/.tsm/2025/01/01/localhost.2025-01-01_00:00:00.json.zst > session.txt`
  - `vim session.txt`

You can, of course, use standard shell features or scripts to make this more
convenient.  I usually just `cd ~/.tsm ; ./latest.zsh` if I want to peek at my
most recent session.  I also have syntax highlighting for this format in Vim,
to make the session files look nicer.

