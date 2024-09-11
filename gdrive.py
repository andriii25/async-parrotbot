from pathlib import Path
import aiohttp

from shared import *

@slack_app.event("file_shared")
async def handle_file_shared(client, event, say, ack):
	await ack()
	file_data = (await client.files_info(file = event["file_id"])).data["file"]
	user_data = (await client.users_info(user = event["user_id"])).data["user"]
	print("File shared by ", user_data['real_name'], flush=True, file=info_stream)

	normalised_name = user_data['real_name'].replace(" ", "_")
	file_url = file_data['url_private_download']
	file_path = Path(f"{config['gdrive']['slack_local_path']}") / f"{normalised_name}" / file_data['name']
	headers = {
		"Authorization": f"Bearer {config['slack_bot_token']}",
	}
	await download_file(file_path, file_url, headers)

	dir_nice_name = f"{config['gdrive']['slack_remote_nice_name']}/{normalised_name}"
	msg_data = (await say(f"File uploading to {dir_nice_name}...")).data
	rclone_log = Path(config['gdrive']['rclone_log_path'])
	returncode = await rclone_sync(config['gdrive']['slack_local_path'], config['gdrive']['slack_remote_path'], rclone_log)

	await client.chat_update(
		channel  = msg_data['channel'],
		ts       = msg_data['ts'],
		text     = f"File uploaded to {dir_nice_name}" if returncode == 0 else f"File *failed* to upload to {dir_nice_name}"
	)

# We use listen() instead of event() to avoid overwriting the normal command parsing and to respond to events
# from multiple files (i.e. when writing future features)
@dc_app.listen()
async def on_message(msg: discord.Message):
	if msg.attachments:
		print(f"{len(msg.attachments)} file(s) shared by {msg.author.display_name}", flush=True, file=info_stream)
		normalised_name = msg.author.display_name.replace(" ", "_")
		file_paths = [Path(f"{config['gdrive']['discord_local_path']}") / f"{normalised_name}" / a.filename for a in msg.attachments]
		file_urls = [a.url for a in msg.attachments]
		coros = [download_file(fp, url) for fp, url in zip(file_paths, file_urls)]
		await asyncio.gather(*coros)

		dir_nice_name = f"{config['gdrive']['discord_remote_nice_name']}/{normalised_name}"
		status_msg = await msg.reply(f"{len(msg.attachments)} file(s) uploading to {dir_nice_name}...")

		rclone_log = Path(config['gdrive']['rclone_log_path'])
		returncode = await rclone_sync(config['gdrive']['discord_local_path'], config['gdrive']['discord_remote_path'], rclone_log)
		updated_status = (f"{len(msg.attachments)} file(s) "
					   f"{'uploaded' if returncode == 0 else '**failed** to upload'} to {dir_nice_name}")
		await status_msg.edit(content=updated_status)


async def rclone_sync(local: str, remote: str, log: Path):
	log.parent.mkdir(exist_ok=True, parents=True)
	with open(log, 'a+') as rclone_log_file:
		process = await asyncio.create_subprocess_exec('rclone',
													   'sync', local, remote,
													   stdout=rclone_log_file, stderr=rclone_log_file)
	await process.wait()
	if process.returncode != 0:
		print(f"Error code {process.returncode} occured during uploading to the remote via rclone. "
			  f"See {str(log)} for details.", file=err_stream)
	return process.returncode


async def download_file(file_path: Path, file_url, headers = None):
	file_path.parent.mkdir(exist_ok=True, parents=True)
	async with aiohttp.ClientSession(headers=headers) as session:
		async with session.get(file_url) as resp:
			if resp.status == 200:
				with open(file_path, 'wb') as f:
					async for chunk in resp.content.iter_chunked(4096):
						f.write(chunk)

			else:
				print(f"Received non-200 response when downloading file "
					  f"{file_url}", file=err_stream)
