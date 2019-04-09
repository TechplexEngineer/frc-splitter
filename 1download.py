import click
import youtube_dl


@click.command(
    help='Pass the URL (to download) and a FILENAME (Output file)')
@click.argument('url')
@click.argument('filename')

def download(url, filename):
    print("Downloading " + filename)
    ydl_opts = {
        'format': 'best',
        'fixup': 'never',
        'outtmpl': filename
    }
    # https://github.com/ytdl-org/youtube-dl/blob/master/README.md#embedding-youtube-dl
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return vodinf.get('created_at').timestamp()

if __name__ == '__main__':
    download()