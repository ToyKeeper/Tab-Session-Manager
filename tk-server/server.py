#!/usr/bin/env python3
# tab-session-manager-server.py: receive TSM session data and save to disk
# Copyright (C) 2025 Selene ToyKeeper
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This is a super simple and janky web server with only one function:
# Receive session data from the Tab Session Manager browser extension,
# via unauthorized plaintext HTTP POST,
# and save it to local files on disk.
# Because TSM's file export auto-save thing is broken.
#
# Requires:
# - Python 3.7 or newer
# - python3-flask
# - python3-flask-cors
# Recommends:
# - python3-zstd

import json
import os, os.path
import socket
import sys
import time

import flask
from flask import request, jsonify
# https://flask-cors.readthedocs.io/en/latest/
from flask_cors import CORS, cross_origin

# compress the output files, zstd (preferred) or gzip
try:
    import zstd
    compress = zstd.compress
    zext = 'zst'
except:
    import gzip
    compress = gzip.compress
    zext = 'gz'


program_name = 'tab-session-manager-server'

basedir = os.path.join(os.environ['HOME'], '.tsm')
tcp_port = 4820

# forcefully work around python's stupid unicode handling
## python3
import importlib
importlib.reload(sys)
#sys.setdefaultencoding('utf-8')

web = flask.Flask(program_name)
CORS(web)
web.config["DEBUG"] = True


def main(args):
    """tab-session-manager-server.py
    Listens for session dumps from the Tab Session Manager browser extension,
    and saves those dumps to local files.
    """

    # placeholder for maybe supporting command line parameters someday
    i = 0
    while i < len(args):
        a = args[i]

        if a in ('-h', '--help'):
            print(main.__doc__)
            return

        else:
            print(main.__doc__)
            return

        i += 1

    web.run(host='0.0.0.0', port=tcp_port, use_reloader=False)


@web.route('/', methods=['GET'])
def frontpage():
    text = '''
    <html>
    <head><title>Go Away</title></head>
    <body>Nothing to see here.</body>
    </html>
    '''
    return text


@web.route('/api/v1/session/post', methods=['POST'])
@cross_origin()  # allow requests from CORS 'preflight" browsers
def submit():

    # who is this request from?
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
    hostname = ip
    try:
        hostname = socket.gethostbyaddr(ip)[0]
    except socket.herror:
        pass

    def err_exit(text):
        log('Error: ' + text, hostname)
        return jsonify(dict(error=text))

    raw = request.data
    session = request.json
    #log(str(session))

    if not session:
        err_exit('No session provided.')

    try:
        millis = session['date']
    except:
        err_exit('No session, or no session date')

    try:
        tags = '.' + '-'.join(session['tag'])
    except:
        tags = ''

    try:
        # save to ~/.tsm/$year/month/$day/$hostname.$tags.$time.json.zst
        when = time.localtime(millis / 1000.0)
        datedir = time.strftime('%Y/%m/%d', when)
        outdir = f'{basedir}/{datedir}'
        timestamp = time.strftime('%Y-%m-%d_%H:%M:%S', when)
        outname = f'{hostname}{tags}.{timestamp}.json.{zext}'
        outpath = f'{basedir}/{datedir}/{outname}'
        numbytes = 0
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        with open(outpath, 'wb') as fp:
            text = raw
            ztext = compress(text, 9)
            fp.write(ztext)
            numbytes = len(ztext)
        log(f'==> {outpath} ({numbytes} bytes)', hostname)
    except Exception as e:
        err_exit(f'Error writing output file: {e}')

    return jsonify('OK')


def log(msg, host=None):
    now = time.time()
    date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
    millis = ('%.3f' % (now % 1.0))[2:]
    if not host:
        host = 'server'
    print('%s.%s %s\t%s' % (date, millis, host, msg))


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

