import subprocess
import click
import os
import shutil


@click.command(
	help='Convert a downloaded file (INFILE) into a series of images stored in (OUTDIR).')
@click.argument('infile')
@click.argument('outdir')
@click.option('--outformat', default='frame%04d.jpg', help='Frame output filename. ex: frame%04.jpg')
@click.option('--fps', default=1, help='Frames per second to export')
@click.option('--ffmpeg_bin', default=None, help='Path to ffmpeg executable. Automatically searches PATH')
def main(infile, outdir, outformat, fps, ffmpeg_bin):
	# ensure outdir exists
	os.makedirs(outdir, exist_ok=True)

	# If the user did not specify ffmpeg path, attempt to find with `which ffmpeg`
	if ffmpeg_bin is None:
		ffmpeg_bin = shutil.which('ffmpeg')
		if (ffmpeg_bin is None):
			print('Unable to find ffmpeg. Please ensure it is installed and on your path. Or provide an absolute path with --ffmpeg')
			sys.exit(1)
	ffmpeg_command = [
		ffmpeg_bin,
		'-hide_banner',
		'-i', infile,
		'-vf', 'fps={}'.format(fps),
		# '-an',
		# '-sn',
		# '-c:v', 'rawvideo',
		# '-pix_fmt', 'rgb24',
		# '-f', 'rawvideo',
		'{}{}{}'.format(outdir, os.sep, outformat)
	]

	print(' '.join(ffmpeg_command))

	proc = subprocess.Popen(ffmpeg_command,
		# stdout=subprocess.PIPE,
		# stderr=subprocess.PIPE,
		preexec_fn=os.setpgrp)

	# proc.wait()

if __name__ == '__main__':
	main()

"""
Export frame at specified time
ffmpeg -i video.webm -ss 00:00:07.000 -vframes 1 thumb.jpg

https://stackoverflow.com/a/42827058

ffmpeg -ss aa:bb:cc -to xx:yy:zz -i input.mp4 -c copy output.mp4



"""