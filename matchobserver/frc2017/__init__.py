#!/usr/bin/env python

# vim: set tw=99:

# This file is part of FRC Replay, a system for automatically recording match
# videos from live streams of FIRST games.

# Copyright (C) 2017 Michael Smith <michael@spinda.net>

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.

# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <http://www.gnu.org/licenses/>.

import numpy
import os
import re
import scipy.spatial.distance
import sys
import time

import cv2
import PIL
import PIL.ImageEnhance
import PIL.ImageOps
import PIL.ImageDraw
import pytesseract

# The below constants use this size as a reference.
# If the video is different a scale is applied in the constructor
BASE_WIDTH = 1280
BASE_HEIGHT = 720

MATCH_LABEL_RECTS = [
    ((160, 560, 625, 610), 'game'),
    ((75,  53,  625, 110), 'outside'),
]
MATCH_RESULTS_RECTS = [
    # ((640, 51, 1030, 116), 'results'),
    # ((825, 51, 1201, 110), 'preview'),
    ((640, 51, 1201, 110), 'both')
]

FMS_BASE_X = BASE_WIDTH / 2
FMS_BASE_Y = 555

TIMEOUT_RECT = (543-FMS_BASE_X, 644-FMS_BASE_Y, 43+543-FMS_BASE_X, 52+644-FMS_BASE_Y)
TIMEOUT_COLOR = (217, 174, 125) #orange
TIMEOUT_COLOR = (0xCD, 0xCC, 0xCD) #grey
TIMEOUT_THRESHOLD = 10

# Needs to be adjusted for match under review icon
LEFT_COLOR_RECT = (623-FMS_BASE_X, 647-FMS_BASE_Y, 12+623-FMS_BASE_X, 55+647-FMS_BASE_Y)
RED_COLOR = (184, 39, 2)
BLUE_COLOR = (59, 133, 220)

LEFT_SCORE_RECT = (497-FMS_BASE_X, 643-FMS_BASE_Y, 136+497-FMS_BASE_X, 64+643-FMS_BASE_Y)
RIGHT_SCORE_RECT = (647-FMS_BASE_X, 643-FMS_BASE_Y, 136+647-FMS_BASE_X, 64+643-FMS_BASE_Y)

LEFT_HANGS_RECT = (98-FMS_BASE_X, 673-FMS_BASE_Y, 23+98-FMS_BASE_X, 26+673-FMS_BASE_Y)
LEFT_ROTORS_RECT = (210-FMS_BASE_X, 674-FMS_BASE_Y, 20+210-FMS_BASE_X, 26+674-FMS_BASE_Y)
LEFT_KPA_RECT = (317-FMS_BASE_X, 674-FMS_BASE_Y, 47+317-FMS_BASE_X, 27+674-FMS_BASE_Y)

RIGHT_HANGS_RECT = (1160-FMS_BASE_X, 673-FMS_BASE_Y, 19+1160-FMS_BASE_X, 26+673-FMS_BASE_Y)
RIGHT_ROTORS_RECT = (1049-FMS_BASE_X, 672-FMS_BASE_Y, 21+1049-FMS_BASE_X, 27+672-FMS_BASE_Y)
RIGHT_KPA_RECT = (917-FMS_BASE_X, 674-FMS_BASE_Y, 47+917-FMS_BASE_X, 27+674-FMS_BASE_Y)

MATCH_TIME_RECT = (614-FMS_BASE_X, 606-FMS_BASE_Y, 52+614-FMS_BASE_X, 27+606-FMS_BASE_Y)
MATCH_TIME_CONTRAST = 127
MATCH_TIME_THRESHOLD = 72

MODE_DISTINGUISH_RECT = (580-FMS_BASE_X, 604-FMS_BASE_Y, 21+580-FMS_BASE_X, 31+604-FMS_BASE_Y)

FIRST_PORTION_COLOR = (222, 188, 146)
FIRST_PORTION_THRESHOLD = 10

MATCH_ENDED_COLOR = (236, 54, 11)
MATCH_ENDED_THRESHOLD = 100

AUTON_TIME = 15
TELEOP_TIME = 135



SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

FIRST_LOGO_SCAN_RATIO = 1 / 4
FIRST_LOGO_TEMPLATE_PATH = '{}/first-logo.bmp'.format(SCRIPT_DIR)
FIRST_LOGO_FLANN_PARAMS = ({'algorithm': 0, 'trees': 5}, {'checks': 50})
FIRST_LOGO_MATCH_RATIO = 0.7
FIRST_LOGO_MIN_MATCH_COUNT = 10

MATCH_LABEL_LEFT_PADDING = 15
MATCH_LABEL_RIGHT_PADDING = 15

# pagesegmode values are: (--psm)
#   0 = Orientation and script detection (OSD) only.
#   1 = Automatic page segmentation with OSD.
#   2 = Automatic page segmentation, but no OSD, or OCR
#   3 = Fully automatic page segmentation, but no OSD. (Default)
#   4 = Assume a single column of text of variable sizes.
#   5 = Assume a single uniform block of vertically aligned text.
#   6 = Assume a single uniform block of text.
#   7 = Treat the image as a single text line.
#   8 = Treat the image as a single word.
#   9 = Treat the image as a single word in a circle.
#   10 = Treat the image as a single character.
NUMBER_TESSERACT_CONFIG = '--psm 6 digits'
MATCH_LABEL_TESSERACT_CONFIG = \
    '-psm 7 --tessdata-dir {}/matchlabel_tessdata matchlabel'.format(SCRIPT_DIR)



# regex for anything that might be a number comming out of OCR
NUMBER_PATTERN = '0-9ZSO'
def np(r):
    return r.replace('@', NUMBER_PATTERN)

# Used to match against error prone OCR text
MATCH_ID_FORMATS = [
    (re.compile(np(r'^Qualif[^@]+([@\s]+)of'), re.M), 'Qualification Match'),

    (re.compile(np(r'^Quart[^T]+Tieb[^@]+([@\s]+)$'), re.M), 'Quarterfinal Tiebreaker'),
    (re.compile(np(r'^Quart[^@]+([@\s]+)of'), re.M), 'Quarterfinal Match'),
    (re.compile(np(r'^Quart[^@]+([@\s]+)$'), re.M), 'Quarterfinal Match'),

    (re.compile(np(r'^Semi[^T]+Tieb[^@]+([@\s]+)'), re.M), 'Semifinal Tiebreaker'),
    (re.compile(np(r'^Semi[^@]+([@\s]+)of'), re.M), 'Semifinal Match'),
    (re.compile(np(r'^Semi[^@]+([@\s]+)$'), re.M), 'Semifinal Match'),

    (re.compile(np(r'^Fin[^T]+Tieb[^@]+([@\s]+)'), re.M), 'Final Tiebreaker'),
    (re.compile(np(r'^Fin[^@]+([@\s]+)of'), re.M), 'Final Match'),
    (re.compile(np(r'^Fin[^@]+([@\s]+)$'), re.M), 'Final Match'),

    (re.compile(np(r'^Practice[^@]+([@\s]+)of'), re.M), 'Practice Match'),

    (re.compile(np(r'^Einst[^F]+Fin[^T]+Tieb[^@]+([@\s]+)'), re.M), 'Final Tiebreaker'),
    (re.compile(np(r'^Einst[^F]+Fin[^@]+([@\s]+)of'), re.M), 'Final Match'),
    (re.compile(np(r'^Einst[^F]+Fin[^@]+([@\s]+)$'), re.M), 'Final Match'),

    (re.compile(np(r'^Einst[^T]+Tieb[^@]+([@\s]+)'), re.M), 'Playoff Tiebreaker'),
    (re.compile(np(r'^Einst[^@]+([@\s]+)of'), re.M), 'Playoff Match'),
    (re.compile(np(r'^Einst[^@]+([@\s]+)$'), re.M), 'Playoff Match')
]

WHITESPACE_RE = re.compile(r'\s+', )
NOT_DIGIT_RE = re.compile(r'[^0-9]')

# Turns out OCR (tesseract) has some common errors. Since we expect text to
# contain only digits we can make some replacements. Remove all whitespace
def fix_digits(text):
    return WHITESPACE_RE.sub('', text) \
        .replace('Z', '2') \
        .replace('S', '5') \
        .replace('O', '0')

# Remove all non-digits and cleanup OCR artifacts
def interpret_as_number(text):
    text = NOT_DIGIT_RE.sub('', fix_digits(text))
    if len(text) == 0:
        return None
    return int(text)

# Image to number using tesseract the number config
def read_number(img):
    out = pytesseract.image_to_string(img, config=NUMBER_TESSERACT_CONFIG)
    return interpret_as_number(out)

# Use tesseract to find text in a small image. Then check if that text matches
# any of the MATCH_ID_FORMATS to determine what type of match.
def read_match_id(cropped_frame):
    text = pytesseract.image_to_string(cropped_frame)
    # print('txt: "{}"'.format(text))

    for regex, match_type in MATCH_ID_FORMATS:
        match = regex.search(text.strip())
        # print('match ', match is not None and match.groups())
        if match:
            match_number = fix_digits(match.group(1))
            if len(match_number) == 0:
                return (None, None)
            else:
                return (match_type, match_number)
    return (None, None)

# Find the mean color in an image.
def mean_color(img):
    return cv2.mean(numpy.array(img))[:3]

# Find the distance between two colors
def color_dist(color1, color2):
    return scipy.spatial.distance.euclidean(color1, color2)



class VisionCore:
    def __init__(self, video_width, video_height):

        #@bb quicker than scaling the image?

        # If the frame is not BASE_WIDTH by BASE_HEIGHT we re-scale our coords
        self._x_scale = video_width / BASE_WIDTH
        self._y_scale = video_height / BASE_HEIGHT
        self._scaled_label_rects = self.rescale_rects(MATCH_LABEL_RECTS)
        self._scaled_results_rects = self.rescale_rects(MATCH_RESULTS_RECTS)

        self._half_video_width = video_width / 2
        self._label_x2 = self._half_video_width - MATCH_LABEL_RIGHT_PADDING

        # setup to be able to search for FIRST Logo location
        logo = FIRST_LOGO_TEMPLATE_PATH
        template = cv2.cvtColor(cv2.imread(logo), cv2.COLOR_BGR2RGB)
        self._template_height, self._template_width = template.shape[:2]
        self._feature_detector = cv2.xfeatures2d.SURF_create()
        self._flann_matcher = cv2.FlannBasedMatcher(*FIRST_LOGO_FLANN_PARAMS)
        self._template_keypoints, self._template_descriptors = \
            self._feature_detector.detectAndCompute(template, None)

    def rescale_rects(self, rects):
        ret = []
        for (x1, y1, x2, y2), typ in rects:
            ret.append(((
                x1 * self._x_scale, y1 * self._y_scale,
                x2 * self._x_scale, y2 * self._y_scale
            ), typ))
        return ret

    def _get_match_info(self, frame):
        def process(rect, typ):
            newframe = frame.crop(rect)
            # newframe.show()
            match_type, match_number = read_match_id(newframe)
            # print('match', match_type, match_number)
            if match_type is not None \
                    and len(match_type) > 0 \
                    and match_number is not None \
                    and len(match_number) > 0:
                return {
                    'match_type':   match_type,
                    'match_number': match_number,
                    'rect':         rect,
                    'type':         typ
                }
            return None

        # Search known locations
        for rect, typ in self._scaled_label_rects:
            ret = process(rect, typ)
            if ret is not None:
                return ret
        # if not found use _find_label_rect
        found_rect = self._find_label_rect(frame)
        return process(found_rect, "game")

    def get_match_info(self, frame):
        ret = self._get_match_info(frame)

        if ret['type'] == "game":
            self.label_rect = ret['rect']

        return ret

    def get_match_time(self, frame):
        if self.label_rect is None:
            return None
        match_time_img = self._crop_rel(frame, self.label_rect, MATCH_TIME_RECT)
        # match_time_img.show()

        match_time_enhanced = \
            PIL.ImageEnhance.Contrast(match_time_img).enhance(MATCH_TIME_CONTRAST)
        # match_time_enhanced.show()

        match_time_thresholded = \
            match_time_enhanced \
            .convert('L') \
            .point(lambda x: 0 if x < MATCH_TIME_THRESHOLD else 255, '1')
        # match_time_thresholded.show()

        match_time = read_number(match_time_thresholded)
        # print('first: ', match_time)
        if match_time is None:
            match_time = read_number(match_time_enhanced)
            # print('second: ', match_time)
        if match_time is None:
            match_time = read_number(match_time_img)
            # print('third: ', match_time)

        return match_time

    def hasMatchStarted(self, frame):
        t = self.getMatchTime(frame)
        if t is not None:
            return t > 0
        return None

    def getMatchInfo(self, frame):
        if self.match_type is not None \
                and len(self.match_type) > 0 \
                and self.match_number is not None \
                and len(self.match_number) > 0:
            return {
                'match_type': self.match_type,
                'match_number': self.match_number,
            }
        return None

    # determine if preview or results frame
    def get_frame_type(self, frame):
        # Check if the upper right corner says results

        for rect, typ in self._scaled_results_rects:
            newframe = frame.crop(rect)
            # newframe.show()
            text = pytesseract.image_to_string(newframe)
            # print('found', text)
            match = re.match(r'Match[^R]+Res', text, re.I)
            if match:
                return 'results'
            match = re.match(r'Match[^P]+Pre', text, re.I)
            if match:
                return 'preview'
        return None

    def first(self, frame):
        # # Search the left quarter of the image for the first logo
        # found_rect = self._find_label_rect(frame)
        # if found_rect is not None:
        #     self._scaled_label_rects = [(found_rect, 'game')] + self._scaled_label_rects

        # colors=['red','green','blue']
        # count=0
        # tmp = frame.copy()
        # for rect, typ in self._scaled_label_rects:
        #     color = colors[count]
        #     count+=1
        #     draw = PIL.ImageDraw.Draw(tmp)
        #     # print(rect[0])
        #     draw.rectangle(((rect[0], rect[1]), (rect[2], rect[3])), fill=None, outline=color)
        # tmp.show()

        # Grab a section of the frame for each found rect and use tesseract
        # to extract the match id. Stop as soon as we get some matching text
        for rect, typ in self._scaled_label_rects:
            newframe = frame.crop(rect)
            # newframe.show()
            match_type, match_number = read_match_id(newframe)
            if match_type is not None \
                    and len(match_type) > 0 \
                    and match_number is not None \
                    and len(match_number) > 0:

                self.match_type = match_type
                self.match_number = match_number
                self.match_status = typ # (One of: outside, game)
                if (self.match_status == 'game'):
                    self.label_rect = rect
                else:
                    self.label_rect = None
                break

        if self.match_type is None:
            # Search the left quarter of the image for the first logo
            found_rect = self._find_label_rect(frame)
            if found_rect is not None:
                (found_rect, 'game')



        if match_type is None \
                or len(match_type) <= 0 \
                or match_number is None \
                or len(match_number) <= 0:
            print('unable to get match information, will try with next frame')
            self.match_type = None
            self.match_number = None
            self.match_status = None
            self.label_rect = None


    


    """
    def ____process_frame(self, frame):
        candidate_label_rects = self._scaled_label_rects

        found_rect = self._find_label_rect(frame)
        if found_rect is not None:
            print('found_rect = {}'.format(found_rect))
            candidate_label_rects = [found_rect] + candidate_label_rects

            # colors=['red','green','blue']
            # count=0
            # tmp = frame.copy()
            # for rect in candidate_label_rects:
            #     color = colors[count]
            #     count+=1
            #     draw = PIL.ImageDraw.Draw(tmp)
            #     draw.rectangle(((rect[0], rect[1]), (rect[2], rect[3])), fill=None, outline=color)
            # tmp.show()

        newlist = []
        for rect in candidate_label_rects:
            newframe = frame.crop(rect)
            # newframe.show()
            matchid = read_match_id(newframe)
            newlist.append((matchid, rect))

        candidate_match_ids = newlist

        # candidate_match_ids = \
        #     ((read_match_id(frame.crop(rect)), rect) for rect in candidate_label_rects)

        match_id = None
        label_rect = None
        for candidate_match_id, candidate_label_rect in candidate_match_ids:
            match_id = candidate_match_id
            label_rect = candidate_label_rect
            if match_id is not None and len(match_id) > 0:
                break

        # If we found a match number, see if there is a timeout
        if match_id is not None:
            # frame.show()
            cropped = self._crop_rel(frame, label_rect, TIMEOUT_RECT)
            # cropped.show()
            meancolor = mean_color(cropped)
            timeout_dist = color_dist(meancolor, TIMEOUT_COLOR)
            print('distance', timeout_dist)
            if timeout_dist < TIMEOUT_THRESHOLD:
                print('timeout detected')
                match_id = None

        match_info = {}
        if self._advanced_scraping and match_id is not None:
            frame.show()
            left_color_img = self._crop_rel(frame, label_rect, LEFT_COLOR_RECT)
            left_color_img.show()
            left_mean_color = mean_color(left_color_img)
            left_red_dist = color_dist(left_mean_color, RED_COLOR)
            left_blue_dist = color_dist(left_mean_color, BLUE_COLOR)

            left_team = 'red' if left_red_dist < left_blue_dist else 'blue'
            right_team = 'blue' if left_team == 'red' else 'red'

            left_score_img = \
                PIL.ImageOps.invert(self._crop_rel(frame, label_rect, LEFT_SCORE_RECT).convert('L'))
            right_score_img = \
                PIL.ImageOps.invert(self._crop_rel(frame, label_rect, RIGHT_SCORE_RECT).convert('L'))

            match_info['{}_score'.format(left_team)] = read_number(left_score_img)
            match_info['{}_score'.format(right_team)] = read_number(right_score_img)


            modeimg = self._crop_rel(frame, label_rect, MODE_DISTINGUISH_RECT)
            mode_distinguish_color = \
                mean_color(modeimg)
            modeimg.show()

            first_portion_dist = color_dist(mode_distinguish_color, FIRST_PORTION_COLOR)
            first_portion = first_portion_dist < FIRST_PORTION_THRESHOLD

            match_ended_dist = color_dist(mode_distinguish_color, MATCH_ENDED_COLOR)
            match_ended = match_ended_dist < MATCH_ENDED_THRESHOLD

            if match_ended:
                match_info['match_period'] = 'ended'
                match_info['match_time'] = 0
            else:
                match_time_img = self._crop_rel(frame, label_rect, MATCH_TIME_RECT)
                #match_time_img.save('a.png')

                match_time_enhanced = \
                    PIL.ImageEnhance.Contrast(match_time_img).enhance(MATCH_TIME_CONTRAST)
                #match_time_enhanced.save('b.png')

                match_time_thresholded = \
                    match_time_enhanced \
                        .convert('L') \
                        .point(lambda x: 0 if x < MATCH_TIME_THRESHOLD else 255, '1')
                #match_time_thresholded.save('c.png')

                match_period = 'teleop'
                match_time = read_number(match_time_thresholded)
                if match_time is None:
                    match_time = read_number(match_time_enhanced)
                if match_time is None:
                    match_time = read_number(match_time_img)

                if match_time == 0:
                    match_info['match_period'] = None
                    match_info['match_time'] = None
                else:
                    if match_time is not None and first_portion and match_time <= AUTON_TIME:
                        match_period = 'auton'
                        match_time += TELEOP_TIME
                    match_info['match_period'] = match_period
                    match_info['match_time'] = match_time

        return (match_id, match_info)
    """

    def _crop_rel(self, frame, origin_rect, rel_rect):
        ox1, oy1, ox2, oy2 = origin_rect
        rx1, ry1, rx2, ry2 = rel_rect

        x1 = rx1 * self._x_scale + self._half_video_width
        y1 = ry1 * self._y_scale + oy1
        x2 = rx2 * self._x_scale + self._half_video_width
        y2 = ry2 * self._y_scale + oy1

        return frame.crop((x1, y1, x2, y2))

    # Attempt to find match label rectangle
    # Says something like: Qualification 1 of 74
    def _find_label_rect(self, frame):
        frame_crop = (0, 0, frame.width * FIRST_LOGO_SCAN_RATIO, frame.height)
        frame_array = numpy.array(frame.crop(frame_crop))
        keypoints, descriptors = self._feature_detector.detectAndCompute(frame_array, None)

        if descriptors is None:
            print('no descriptors')
            return None

        matches = self._flann_matcher.knnMatch(self._template_descriptors, descriptors, k=2)

        # store all the good matches as per Lowe's ratio test.
        good_matches = []
        for m, n in matches:
            if m.distance < FIRST_LOGO_MATCH_RATIO * n.distance:
                good_matches.append(m)

        if len(good_matches) > FIRST_LOGO_MIN_MATCH_COUNT:
            src_pts = numpy.float32([self._template_keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
            dst_pts = numpy.float32([keypoints[m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)

            t = cv2.estimateRigidTransform(src_pts, dst_pts, False)
            if t is not None:
                scale = t[0, 0]
                x1 = t[0, 2]
                y1 = t[1, 2]
                x2 = x1 + self._template_width * scale
                y2 = y1 + self._template_height * scale
                return (x2 + MATCH_LABEL_LEFT_PADDING, y1, self._label_x2, y2)

        return None

if __name__ == '__main__':
    vision_core = VisionCore(BASE_WIDTH, BASE_HEIGHT)

    frames_dir = os.path.join(SCRIPT_DIR, '../../samples')
    frames_files = []
    if len(sys.argv) > 1:
        frames_files = sys.argv[1:]
    else:
        frames_files = sorted(os.listdir(frames_dir))

    for frame_file in frames_files:
        if frame_file == ".DS_Store":
            continue

        print('Processing {}'.format(frame_file))

        frame_path = frame_file
        if not os.path.isfile(frame_path):
            frame_path = os.path.join(frames_dir, frame_file)

        frame = PIL.Image.open(frame_path)
        start_time = time.time()
        match_id, match_info = vision_core.process_frame(frame)
        print('({:.2f}) {} = {}: {}'.format(time.time() - start_time, frame_file, match_id, match_info))
        print()
