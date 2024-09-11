import io
from datetime import datetime

import discord.ext.commands
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

from shared import *

if config['features_enabled'] is not None:
	for feat in config['features_enabled']:
		exec(f"import {feat}")

print("Starting parrotbot...", flush=True, file=info_stream)

@dc_app.event
async def on_ready():
	print(f"Logged in to Discord as {dc_app.user} (ID: {dc_app.user.id})", file=info_stream)

@dc_app.command(name="sync-command-tree")
async def sync_command_tree(ctx: discord.ext.commands.Context):
	invoker = ctx.message.author
	if invoker.top_role >= invoker.guild.get_role(config['discord']['min_sync_roleid']) \
		or invoker == invoker.guild.owner:
		dc_app.tree.copy_global_to(guild=guild)
		await dc_app.tree.sync(guild=guild)
		await ctx.reply("Synced the command tree.")
	else:
		await ctx.reply("You don't have a high enough role to invoke this command.")

@slack_app.command("/parrotcheckhealth")
async def parrotcheckhealth(client, ack, body, say):
	user_id = body["user_id"]
	await ack(f"Hi <@{user_id}>!")
	MAX_CHARS=2500

	log = await async_check_output(config['log']['command'], shell=True)
	log = log.decode().replace('files.slack.com', '********')
	log_lines = log.split('\n')
	log_messages = []
	# incredibly jank but whatever
	while len(log_lines) > 0:
		msg = ""
		while len(log_lines) > 0 and len(msg) + len(log_lines[0]) <= MAX_CHARS:
			msg += log_lines.pop(0) + '\n'
		log_messages.append(msg)

	if "quiet" in body['text']:
		await ack("I'm running! Here is my latest log:" \
		    "\n```\n" + log_messages[-1] + '```')
	else:
		await say("I'm running! Here is my log:")
		for msg in log_messages:
			await say("\n```\n" + msg + '```', unfurl_media = False, unfurl_links=False)
		await ack()

@dc_app.tree.command(name="parrotcheckhealth")
async def dc_parrotcheckhealth(interaction: discord.Interaction):
	log = await async_check_output(config['log']['command'], shell=True)
	log = log.decode().replace('files.slack.com', '********')
	timestamp = datetime.now()
	if len(log) > 2000:
		# Too long so upload a text file instead, this looks better imo than a series of embeds.
		dc_logfile = discord.File(io.StringIO(log), filename=f"parrotbotlog_{timestamp.strftime('%Y%M%d_%H%m%s')}.txt")
		await interaction.response.send_message("I'm running! Here is my log:", file=dc_logfile)
	else:
		await interaction.response.send_message(f"I'm running! Here is my log:\n"
												f"```\n{log}```\n")


async def main():
	# why no do while python??
	cursor = None
	while cursor != '':
		conversations = await slack_app.client.conversations_list(cursor=cursor)
		for chan in conversations['channels']:
			if not (chan['is_im'] or chan['is_member'] or chan['is_archived']):
				await slack_app.client.conversations_join(channel=chan['id'])
				print(f"Joined {chan['name']}", flush=True, file=info_stream)
		cursor = conversations['response_metadata']['next_cursor']
	slack_handler = AsyncSocketModeHandler(slack_app, config['slack_app_token'])

	await asyncio.gather(slack_handler.start_async(), dc_app.start(token=config['discord']['token']))

if __name__ == "__main__":
	import asyncio
	asyncio.run(main())
