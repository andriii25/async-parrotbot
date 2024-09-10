import asyncio
import logging
import sys
import argparse

import discord
from discord.ext import commands
import yaml
from slack_bolt.app.async_app import AsyncApp

parser = argparse.ArgumentParser()
parser.add_argument('--journald', action='store_true',
                    help='Use systemd journal outputs instead of stdout and stderr')
parser.add_argument('-c', '--config',
                    help='Specify a path for a config.yaml',
                    default='/etc/async-parrotbot/config.yaml')
parser.add_argument('--debug-discord', action='store_true',
					help='Log all debug events from discord.py. If not set then INFO is used to remove clutter.')
args = parser.parse_args()

# TODO: If we have to use logger anyway debug/info/warn/err stream could be done through logging as well...
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG if args.debug_discord else logging.INFO)

async def async_check_output(cmd, **kwargs):
	process = await asyncio.create_subprocess_shell(
		cmd,
		stdout=asyncio.subprocess.PIPE,
		stderr=asyncio.subprocess.PIPE,
		**kwargs
	)
	stdout, stderr = await process.communicate()
	if process.returncode == 0:
		return stdout
	else:
		print(f"Error occured while executing command "
			  f"`{cmd}` during /parrotcheckhealth:", file=err_stream)
		print(stderr, file=err_stream)

if args.journald:
	from systemd import journal
	debug_stream  = journal.stream('async-parrotbot', priority=7)
	info_stream   = journal.stream('async-parrotbot', priority=6)
	warn_stream   = journal.stream('async-parrotbot', priority=4)
	err_stream    = journal.stream('async-parrotbot', priority=3)

	sys.stdout = info_stream
	sys.stderr = err_stream

	journal_log = journal.JournalHandler(SYSLOG_IDENTIFIER='async-parrotbot')
	logger.addHandler(journal_log)

else:
	debug_stream  = sys.stdout
	info_stream   = sys.stdout
	warn_stream   = sys.stderr
	err_stream    = sys.stderr

if args.config is not None:
	config_file = args.config
	if args.config == '/etc/async-parrotbot/config.yaml':
		print("No config file specified, defaulting to /etc/async-parrotbot/config.yaml...",
		      file = warn_stream)
else:
	print("argparse is broken, I am confused, abort.", file=err_stream)
	raise SystemExit(1)


discord.utils.setup_logging()
config = yaml.load(open(config_file), Loader=yaml.loader.FullLoader)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
guild = discord.Object(id=config['discord']['guild_id'])

dc_app = commands.Bot(command_prefix='$', help_command=None, intents=intents)
slack_app = AsyncApp(token = config['slack_bot_token'])
