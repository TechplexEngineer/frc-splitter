import os
import click
import PIL
import PIL.ImageEnhance
import PIL.ImageOps
import matchobserver.frc2017 as frc2017
import time
# from matchobserver.frc2017 import FRC2017VisionCore
from multiprocessing import Pool
import multiprocessing

test = {
	# 'review1':      'frame0064.jpg',
	# 'rockets1':     'frame0066.jpg',
	# 'blankscores1': 'frame0070.jpg',
	# 'scores1':      'frame0071.jpg',
	# 'preview1':     'frame0105.jpg',
	# 'timeout':      'frame0156.jpg',

	'preview':      'frame0522.jpg', #@todo: get match
	'prematch':     'frame0649.jpg',
	'auto14':       'frame0653.jpg',
	'teleop135':    'frame0667.jpg',
	'teleop14':     'frame0789.jpg', #need to distingquish between this and auto14
	'end':          'frame0837.jpg',
	'results':      'frame0845.jpg'
}

def extract_digits(string):
	return ''.join([s for s in string if s.isdigit()])

MATCH_DEFAULTS = {
	'startframe': -1,
	'endframe': -1,
	'match_type': '',
	'match_number': -1
}



vc = None
framedir = None
def setup(_framedir):
	global vc
	global framedir
	framedir = _framedir

	files = os.listdir(framedir)

	# Assume all frames are the same size
	frame = PIL.Image.open(os.path.join(framedir, files[0]))
	width, height = frame.size
	vc = frc2017.VisionCore(width, height)


count = 0
def dowork(file):
	global count
	# print('***** {} {}'.format(name, file))
	# framestart = time.time()

	# print('bb ', framedir, file)
	start = time.time()
	frame = PIL.Image.open(os.path.join(framedir, file)) #@todo load only portion of frame
	info = vc.get_match_info(frame)

	if info['type'] == "game":
		info['time'] = vc.get_match_time(frame)
	print(info)

	print('frame {} took {:2f}'.format(file, time.time() - start))
	# typ = vc.get_frame_type(frame)

	# count += 1
	# print('{} {} type: {} num: {}'.format(count, typ, info['match_type'], info['match_number']))


	# print('frame took {:2f}'.format(time.time() - framestart))
	# print('-'*10,'\n')
	# return (match_type, match_number)
	return None

@click.command(help='Iterate through all frames')
@click.argument('framedir')
@click.option('--usemulti', default=False, help='Whether or not use multiprocessing')
def main(framedir, usemulti):


	if usemulti:
		setupargs = [framedir]
		multiprocessing.set_start_method('spawn') # this is needed for CV to work on osx
		start = time.time()
		p = Pool(processes=(os.cpu_count()-1), initializer=setup, initargs=setupargs)
		ret = p.map(dowork, test.values())
		print(ret)
		print('all {} frames took {:2f}'.format(len(test.items()), time.time() - start))
	else:
		start = time.time()
		setup(framedir)
		for name, file in test.items():
			dowork(file)
		print('all {} frames took {:2f}'.format(len(test.items()), time.time() - start))
		# 7 frames in for loop takes ~4.8/5

























	# match = MATCH_DEFAULTS.copy()

	# queue = []

	# files = os.listdir(framedir)

	# # Assume all frames are the same size
	# frame = PIL.Image.open(os.path.join(framedir, files[0]))
	# width, height = frame.size
	# vc = frc2017.VisionCore(width, height)

	# for name, file in test.items():
	# 	print('***** {} {}'.format(name, file))
	# # for file in files:
	# 	# print('***** {}'.format(file))
	# 	start = time.time()

	# 	frame = PIL.Image.open(os.path.join(framedir, file))
	# 	# width, height = frame.size
	# 	# frame.show()

	# 	vc.first(frame)
	# 	break

	# 	# vc = frc2017.VisionCore(frame)
	# 	# break;

	# 	# No previous frames have started
	# 	if match['startframe'] == -1 and vc.hasMatchStarted(frame):
	# 		#might want to subtract 5 or so frames to make sure we get the beginning of the match
	# 		match['startframe'] = extract_digits(file)
	# 		print('--- found start frame', match)

	# 	# We previously found start frame, but not match info yet
	# 	if match['startframe'] != -1 and match['match_number'] == -1:
	# 		info = vc.getMatchInfo(frame)
	# 		if info is not None:
	# 			match['match_number'] = info['match_number']
	# 			match['match_type'] = info['match_type']
	# 			print('--- got match info', match)


	# 	# @todo might need a timeout for number of frames. and timeout detection
	# 	#
	# 	# we previously found start frame and match number
	# 	if match['startframe'] != -1 \
	# 		and match['match_number'] != -1 \
	# 		and vc.hasMatchResults(frame):
	# 		# might want to add 5 or so frames to make sure we leave plenty of time for viewing scores
	# 		match['endframe'] = extract_digits(file)
	# 		results = match.copy()
	# 		print('--- found end frame', match)
	# 		# print('--'*5, match)
	# 		queue.append(results) #probs don't need this copy now that we copy MATCH_DEFAULTS
	# 		match = MATCH_DEFAULTS.copy()

	# 	# ret = vc.process_frame(frame)
	# 	# print(ret)
	# 	# break #@bb debugging
	# 	print ('frame took {:2f}'.format(time.time() - start))


if __name__ == '__main__':
	main()

"""
semis frame 138 starts timeout


getFrameType()
"""
