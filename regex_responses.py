from pathlib import Path

import discord

from shared import dc_app, config, info_stream, warn_stream, err_stream
from util.regex_response import RegexResponse

regex_responses = []

def init_responses(reset_cooldowns: bool = False):
	response_dir = Path(config['regex_responses']['responses_dir'])
	print(f"Loading regex responses from {response_dir.name}", file=info_stream, flush=True)
	for response_path in response_dir.glob('*.yaml'):
		regex_responses.append(RegexResponse(response_path))
		if reset_cooldowns:
			regex_responses[-1].reset_cooldown()
		print(f"Loaded regex response {response_path.name}", file=info_stream, flush=True)

# TODO: Add slack implementation here

@dc_app.listen()
async def on_message(msg: discord.Message):
	# Filter out commands and ParrotBot messages
	if msg.content[0] != '$' and msg.author != dc_app.user:
		response = None
		for regex_response in regex_responses:
			response = regex_response.check_response(msg.content)
			if response is not None:
				print(f"Found content matching pattern of regex response {regex_response.name}", file=info_stream, flush=True)
				break
		if response is not None:
			await msg.channel.send(response)


@dc_app.tree.command(name="resetcooldown")
@discord.app_commands.describe(response_name="Name of RegEx response file")
async def reset_cooldown(interaction: discord.Interaction, response_name: str):
	"""Resets cooldown of a particular RegEx response"""
	# hopefully still ok in async func as this is fast
	response_path = Path(config['regex_responses']['responses_dir']) / f"{response_name}.yaml"
	cooldown_path = response_path.with_suffix('.cooldown')
	if response_path.exists():
		if cooldown_path.exists():
			cooldown_path.unlink()
			print(f"Reset cooldown of {response_name}", file=info_stream, flush=True)
		else:
			print(f"Cooldown file {cooldown_path.name} does not exist, not doing anything...", file=warn_stream, flush=True)
		await interaction.response.send_message(f"Resetting cooldown of {response_name} response", ephemeral=True)
	else:
		print(f"Response file {response_path} does not exist, cannot reset its cooldown", file=err_stream, flush=True)
		await interaction.response.send_message(f"RegEx response {response_name} does not exist, cannot reset its cooldown.", ephemeral=True)


@dc_app.tree.command(name="reloadresponses")
@discord.app_commands.describe(reset_cooldown="Resets cooldown of all RegEx responses if True (default False)")
async def reload_responses(interaction: discord.Interaction, reset_cooldowns: bool = False):
	"""Reloads all RegEx responses, does not affect cooldown files."""
	await interaction.response.send_message("Reloading responses...", ephemeral=True)
	regex_responses.clear()
	init_responses(reset_cooldowns)

init_responses(False)
