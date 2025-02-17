#!/usr/bin/env python3
# json2txt.py: converts Tab Session Manager session files to plain text
# Copyright (C) 2025 Selene ToyKeeper
# SPDX-License-Identifier: GPL-3.0-or-later

import gzip
import json
import re
import time
try:
    import zstd
except:
    zstd = None


verbose = False


def main(args):
    """json2txt.py - Converts Tab Session Manager json exports to readable text
    Usage: json2txt.py file1.json [file2.json.zst file3.json.gz ...]
    Output format:
        Window 1 ($Open / $Total tabs) [$WIDx$HGT+$LEFT+$TOP]: $WindowTitle
            - Open Tab :: $URL
            * Closed Tab :: $URL
            + Closed Tab With Open Children :: $URL
                - Open Tab :: $URL
                * Closed Tab :: $URL
            ! Focused Tab :: $URL
            ? <ERRTYPE> Broken Tab (broken tree structure) :: $URL
    "Open" tabs are loaded.  "Closed" tabs are unloaded or discarded.
    """

    inpaths = []
    i = 0
    while i < len(args):
        a = args[i]
        # TODO: implement command line options
        if a in ('-h', '--help'):
            print(main.__doc__)
            return
        #elif a in ('--html'):
        #    pass
        #elif a in ('-t', '--text'):
        #    pass
        #elif a in ('-o', '--out'):
        #    pass
        #elif a.startswith('-'):
        #    pass
        else:
            inpaths.append(a)
        i += 1

    for inpath in inpaths:
        if len(inpaths) > 1:
            print(f'===== {inpath} =====')
        jsn = load_json(inpath)
        tree = json2tree(jsn)
        lines = tree2lines(tree)
        print_lines(lines)


# convenience class
class Empty(dict):
    def __init__(self, *args, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            return None

    def __setattr__(self, item, value):
        self.__setitem__(item, value)
        if value is None:
            del self[item]


def load_json(inpath):
    raw = ''
    with open(inpath, 'rb') as fp:
        raw = fp.read()
        if inpath.endswith('.gz'):
            raw = gzip.decompress(raw)
        elif inpath.endswith('.zst') or inpath.endswith('.zstd'):
            raw = zstd.decompress(raw)
    if not raw: return

    jsn = json.loads(raw)
    return jsn


def json2tree(jsn):
    """Convert TSM json data into a nested tree of windows and tabs.
    """
    tree = []
    if isinstance(jsn, dict):
        jsn = [jsn]

    # FIXME: this parser sucks, rewrite cleaner
    for session in jsn:
        s = Empty()
        tree.append(s)
        for key, value in session.items():
            # handle these two separately
            if key in ('windows', 'windowsInfo'):
                pass
            # everything else just gets copied as-is
            else:
                s[key] = value
        # convert the window and tab info
        s.windows = []
        for windowId in session['windows']:
            w = Empty()
            s.windows.append(w)
            w.id = windowId
            # copy basic window info
            for key, value in session['windowsInfo'][w.id].items():
                w[key] = value
            # copy tabs, creating a tree of them
            tabs = session['windows'][windowId]
            #w.tabs = Empty(**tabs)
            w.tabs = []
            w.by_id = {}
            # keep going over the tab list until all are loaded into the tree
            done = False
            passes = 0
            maxdepth = 100
            while not done:
                found = False
                passes += 1
                prev_tabId = None
                for tabId, tabdata in tabs.items():
                    tabId = str(tabId)
                    # helps fix tabs with non-existent parent
                    if not prev_tabId:
                        prev_tabId = tabId
                    # found an unprocessed tab
                    if tabId not in w.by_id:
                        found = True
                        # broken tab, refers to non-existent parent
                        if passes > maxdepth:
                            tabdata['broken'] = 'ORPHAN'
                            if 'openerTabId' in tabdata:
                                # try to connect it to nearest tab
                                tabdata['openerTabId'] = prev_tabId
                        # broken tab, is its own parent
                        if ('openerTabId' in tabdata) and (tabId == str(tabdata['openerTabId'])):
                            tabdata['broken'] = 'OUROBOROS'
                            del tabdata['openerTabId']
                        # root-level tab
                        if 'openerTabId' not in tabdata:
                            parent_id = 'w' + windowId
                            if verbose:
                                title = tabdata['title']
                                print(f'{parent_id} -> {tabId}: {title}')
                            t = Empty(**tabdata)
                            t.children = []
                            t.parent = None
                            t.depth = 0
                            w.tabs.append(t)
                            w.by_id[tabId] = t
                            if verbose:
                                print(f'{t.title}')
                        # child tab
                        else:
                            parent_id = str(tabdata['openerTabId'])
                            if verbose:
                                title = tabdata['title']
                                print(f'{parent_id} -> {tabId}: {title}')
                            # parent already loaded, so add the child
                            if parent_id in w.by_id:
                                parent = w.by_id[parent_id]
                                t = Empty(**tabdata)
                                t.children = []
                                t.parent = parent
                                t.depth = parent.depth + 1
                                parent.children.append(t)
                                w.by_id[tabId] = t
                                if verbose:
                                    print(('    ' * parent.depth) + f'{parent.title}')
                                    print(('    ' * t.depth) + f'{t.title}')
                    # save for the next loop, just in case
                    prev_tabId = tabId
                if not found:
                    done = True

    return tree


# True if this tab or any of its children, recursively, are loaded
def any_tabs_open(tabs):
    for tab in tabs:
        if (not tab.hidden) and (not tab.discarded):
            return True
        elif tab.children:
            if any_tabs_open(tab.children):
                return True
    return False


def num_tabs_open(window):
    total = len([ tab for tab in window.by_id.values()
                  if ((not tab.hidden) and (not tab.discarded))
                ])
    return total


def tree2lines(tree):
    """Convert a tree structure to a list of text lines for printing.
    """
    lines = []

    # omit the URL if it contains any of these
    hide_pats = (
            # the user's local homepage file
            r'/home/.*/.mozilla/homepage.html',
            # Tree Style Tab's "Group Tab" page
            r'moz-extension://.*/resources/group-tab.html',
            )

    # convert tabs to a string, recursively
    def append_tabs(tabs):
        for tab in tabs:
            broken = ''
            if tab.broken:
                broken = f'<{tab.broken}> '
                prefix = '?'
            elif tab.highlighted or tab.active:
                prefix = '!'
            elif (not tab.hidden) and (not tab.discarded):
                prefix = '-'
            elif any_tabs_open(tab.children):
                prefix = '+'
            else:
                prefix = '*'
            url = ' :: ' + tab.url
            for hide in hide_pats:
                if re.search(hide, tab.url):
                    url = ''
            lines.append(('    ' * (1+tab.depth)) + f'{prefix} {broken}{tab.title}{url}')
            append_tabs(tab.children)

    def jdate(millis):
        return time.strftime('%Y-%m-%d %H:%M:%S %z', time.localtime(millis / 1000.0))

    for session in tree:
        num_open = sum([num_tabs_open(window) for window in session.windows])
        lines.append(f'Session ({session.windowsNumber} windows, {num_open} / {session.tabsNumber} tabs): {session.name}')
        lines.append(f'    - Date Exported: {jdate(session.date)}')
        lines.append(f'    - Date Started:  {jdate(session.sessionStartTime)}')
        lines.append('')
        for wnum, window in enumerate(session.windows):
            incog = ''
            if window.incognito: incog = ' (incognito)'
            geom = f'{window.width}x{window.height}+{window.left}+{window.top}'
            num_tabs = len(window.by_id)
            num_open = num_tabs_open(window)
            lines.append(f'Window {1+wnum} ({num_open} / {num_tabs} tabs) [{geom}]{incog}: {window.title}')
            append_tabs(window.tabs)
            lines.append('')

    return lines


def print_lines(lines):
    for line in lines:
        print(line)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

