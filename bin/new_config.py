#!/usr/bin/env python3

import jinja2
import re
import shutil
import subprocess
import sys
try:
    import readline  # noqa; pylint: disable=unused-import
except ImportError:
    pass

import config
import utils
from common import BIN, VIDEO_CONFIGS_DIR, logger


THUMBNAILER = BIN / 'thumbnail'

STAGES = [
    ('Team SⅡ', '第48区'),
    ('Team SⅡ', '美丽48区'),
    ('Team NⅡ', '以爱之名'),
    ('Team HⅡ', '美丽世界'),
    ('Team HⅡ', 'New H Stars'),
    ('Team HⅡ', '头号新闻'),
    ('Team X', '命运的X号'),
    ('Team XⅡ', '代号XⅡ'),
    ('Team Ft', '梦想的旗帜'),
    ('Team Ft', '双面偶像'),
    (None, '我们向前冲'),
    ('Team HⅡ', '头号新闻'),
    ('Team SⅡ', '美丽48区'),
    ('Team Ft', '双面偶像'),
    ('Team SⅡ', '重生计划'),
    ('Team NⅡ', 'N.E.W'),
]

TEAM_TAGS = {
    'Team SⅡ': ['Team SⅡ', 'SⅡ', 'Team SII', 'SII'],
    'Team NⅡ': ['Team NⅡ', 'NⅡ', 'Team NII', 'NII'],
    'Team HⅡ': ['Team HⅡ', 'HⅡ', 'Team HII', 'HII'],
    'Team X': ['Team X'],
    'Team XⅡ': ['Team XⅡ', 'XⅡ', 'Team XII', 'XII'],
    'Team Ft': ['Team Ft', 'Ft'],
}

CONFIG_TEMPLATE = jinja2.Template('''\
title: {{ title }}
datetime: {{ datetime }}
vod: {{ vod }}
{% if m3u8 -%}
m3u8: {{ m3u8 }}
{% endif -%}
tags:
{% for tag in tags -%}
  - {{ tag }}
{% endfor -%}
thumbnail: {{ thumbnail }}
playlists:
{% for playlist in playlists -%}
  - {{ playlist }}
{% endfor -%}
''')


def die(msg):
    logger.error(msg)
    sys.exit(1)


def inputs(prompt=''):
    return input(prompt).strip()


def hr():
    columns = shutil.get_terminal_size().columns
    print('-' * columns, file=sys.stderr)


def find_stage(stage):
    for team, stage_ in STAGES:
        if stage_ == stage:
            return team
    raise KeyError('stage %s not recognized' % stage)


def find_latest_live_id():
    for file, attrs in reversed(config.list_vod_configs(include_past=True)):
        live_id = int(attrs.live_id)
        if live_id:
            logger.info(f'latest live_id from {file}')
            return live_id
    return None


def find_latest_perfnum(stage):
    for file, attrs in reversed(config.list_vod_configs(include_past=True)):
        if attrs.stage == stage and attrs.perfnum:
            logger.info(f'latest perf # from {file}')
            return int(attrs.perfnum)
    return 0


def generate_config_file(date, time, platform, vid_input, special_stage, stage, m3u8):
    if not re.match(r'^\d{8}$', date):
        die(f'invalid date {date}')

    if not re.match(r'^\d{2}:\d{2}$', time):
        die(f'invalid time {time}')
    # ISO 8601
    datetime = f'{date[:4]}-{date[4:6]}-{date[6:]}T{time}:00+08:00'

    group_abbrevs = ['snh', 'bej', 'gnz', 'shy', 'ckg']
    if platform == 'live.48.cn':
        pass
    elif platform == 'zhibo.ckg48.com':
        die(f'historical address format since 27/02/2019 {platform}')
    elif platform == 'live.snh48.com':
        die(f'unrecognized platform {platform}')
    elif platform in [f'live.{g}48.com' for g in group_abbrevs]:
        pass
    else:
        die(f'unrecognized platform {platform}')
    platform_short = platform[5:8] if platform != 'zhibo.ckg48.com' else 'snh'
    assert platform_short in group_abbrevs

    if platform == 'live.48.cn':
        vid_default = find_latest_live_id() + 1
        vid = vid_input or vid_default
    else:
        vid = vid_input
    try:
        vid = int(vid)
    except (TypeError, ValueError):
        die(f'invalid video ID {vid}')

    if special_stage:
        # Special performance
        if not stage:
            die('name should not be empty')

        # Derive
        title = f'{date} {stage}'
        vod = f'https://live.48.cn/Index/invedio/club/1/id/{vid}'
        tags = ['SNH48']
        thumbnail = ''
        playlists = ['全部', '全部公演', '特别公演']

        file_default = f'{date}-{vid}-{stage}.yml'
        file_input = None
        file = VIDEO_CONFIGS_DIR / (file_input or file_default)
    else:
        # Regular performance
        team = find_stage(stage)

        perfnum_default = find_latest_perfnum(stage)
        if perfnum_default is not None:
            perfnum_default += 1
        perfnum_default_display = f' [{perfnum_default:02d}]' if perfnum_default else ''
        perfnum_input = None
        if perfnum_input:
            try:
                perfnum = int(perfnum_input)
            except ValueError:
                die(f'invalid performance # {perfnum_input}')
        elif perfnum_default:
            perfnum = perfnum_default
        else:
            die('performance # not given')

        # Derive
        if team is not None:
            title = f'{date} {team} {stage} {perfnum:02d}'
        else:
            # Multi-team, e.g. 我们向前冲
            title = f'{date} {stage} {perfnum:02d}'
        vod = f'http://{platform}/Index/invedio/club/1/id/{vid}'
        tags = ['SNH48', stage]
        tags.extend(TEAM_TAGS[team])
        thumbnail = f'{date}-{stage}-{perfnum:02d}.png'
        playlists = ['全部', '全部公演']
        if team is not None:
            playlists.extend([f'{team}', f'{team} — {stage}'])
        else:
            playlists.append(stage)

        pvid = str(vid) if platform_short == 'snh' else f'{platform_short}{vid}'
        file = VIDEO_CONFIGS_DIR / f'{date}-{pvid}-{stage}-{perfnum:02d}.yml'

    # Render and write config file
    hr()
    print(file)
    content = CONFIG_TEMPLATE.render(
        title=title,
        datetime=datetime,
        vod=vod,
        m3u8=m3u8,
        tags=tags,
        thumbnail=thumbnail,
        playlists=playlists,
    )
    with open(file, 'w') as fp:
        fp.write(content)

    # Generate thumbnail
    hr()
    if not special_stage:
        logger.info('Generating thumbanil...')
        logger.info(f'thumbnail {stage} {date} {perfnum:02d}')
        cmd = [THUMBNAILER, stage, date, f'{perfnum:02d}']
        subprocess.run(cmd)
    else:
        logger.info('Please remember to generate the thumbnail.')
