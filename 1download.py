import click
import twitch
import youtube_dl


@click.command(
    help='Pass the ID (Twitch ID to download) and a FILENAME (Output file)')
@click.argument('id')
@click.argument('filename')

def download(id, filename):
    print("Downloading " + filename)
    twitch_client = twitch.TwitchClient(client_id='a57grsx9fi8ripztxn8zbxhnvek4cp')
    vodinf = twitch_client.videos.get_by_id(id)
    ydl_opts = {
        'format': 'best',
        'fixup': 'never',
        'outtmpl': filename
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([vodinf.get('url')])
    return vodinf.get('created_at').timestamp()

if __name__ == '__main__':
    download()