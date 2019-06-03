# frc-splitter

The goal is to provide a top of the line FIRST Robotics Competition match video splitter with realtime and post-process capabilities.

The team that built FRCReplay did an amazing job and we want to leverage their work for the next era of automatic match video splitting and upload.

For context, the FIRST Robotics Competion is often livestreamed with services like Twitch however the streams on twitch only have a 30 day lifespan and afterward are lost for good.
Many members of the FRC community have come together to download the stream videos and split them into single matches. The single match videos are then uploaded to YouTube and the links shared on The Blue Alliance.

[FRCReplay](https://www.chiefdelphi.com/t/frc-live-replay-match-videos-automatically-recorded-and-uploaded-in-minutes/159204) was an innovative system operated during the 2017 FRC and FTC seasons. Their system would connect to a live stream, and in real time process (about ever 3rd frame) to detect match start and end times and automatically upload the match video to Streamable. Their technical approach to detecting Timeouts and the start of match (with openCV and TesseractOCR) will be used here.

Our goal is to support both processing the live stream as well as whole days of match video that can be downloaded after the fact.

In an ideal system a generic flow that would go something like:
1. Scan for when a match starts [Label: Start of Match]
2. Offset by match length. [Label: End of Match]
3. Scan for score screen posting [Label: Score Posted] (I've heard the FRC Events API publishes this time.)
4. Generate FFMPEG command to copy from the input stream (don't transcode) [Start of Match]-5sec to [End of Match]+5sec and Append [Score Posted] to [Score Posted]+5sec

A rough outline of the code in this repository:
1. (download or stream) video
2. Convert the video to frames 1 frame every 1 second or less (ex: 1 frame every 5 seconds)
3. Process the frames with OCR/OpenCV and store what we learned from the process in a queue
4. Then run the data through a state machine. Turns out the OCR data is quite noisy. The thinking was with a state machine we could say (seen the same thing a couple of times must be true)
5. Then based on the output of the state machine generate and execute the needed ffmpeg commands

# For anyone interested in contributing:
Here are some [sample frames](https://github.com/TechplexEngineer/frc-splitter/files/3249665/interesting.zip)
frame0522.jpg shows a match preview
frame0653.jpg is where the match actually starts
frame0667.jpg is where teleop starts
frame0789.jpg is when there are 14 seconds left in teleop
frame0837.jpg is the end of the match
frame0845.jpg is when the results are posted.

## Many of the needed pieces are here some remaining work includes:
- When to process frames vs when to seek (for performance)
- Where to upload videos. Youtube has a 100 video/(some time period) limit
- Field faults and match play doesn't match the one match after another model.
- Some sort State machine to determine match times
