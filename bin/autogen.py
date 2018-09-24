#!/usr/bin/env python3

import argparse
import re

import requests

from new_config import generate_config_file

def main():
    parser = argparse.ArgumentParser()
    add = parser.add_argument
    add('vid', type=int)
    add('platform', choices=['snh', 'bej', 'gnz', 'shy', 'ckg'], default='snh')
    add('-s', '--special', action='store_true')
    args = parser.parse_args()
    if args.platform == 'snh':
        platform = 'zhibo.ckg48.com'
    else:
        platform = 'live.%s48.com' % args.platform
    url = 'http://%s/Index/invedio/id/%d' % (platform, args.vid)
    resp = requests.get(url).text
    stage_pattern = re.search('<span class="title1">(.*)</span>', resp).group(1)
    try:
        stage = re.match(r'^《(.*)》.*$', stage_pattern).group(1)
    except AttributeError:
        stage = stage_pattern
    m2 = re.search('<span class="title2">.*(?P<date>\d{4}-\d{2}-\d{2}) (?P<time>\d{2}:\d{2}):\d{2}</span>', resp)
    date = m2.group('date').replace('-', '')
    time = m2.group('time')
    m3u8 = re.findall('https?://.*\.m3u8[^"]*', resp)[0]
    generate_config_file(date, time, platform, args.vid, args.special, stage, m3u8)

if __name__ == '__main__':
    main()
