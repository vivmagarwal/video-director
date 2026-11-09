#!/usr/bin/env bash
# Checks the shape of a finished video file. It cannot tell you the video is good.
#   bash check-video.sh out/my-video.mp4 [expected seconds]
# Prints every reading. Lines starting with PROBLEM are worth opening.
# Exit code: 0 means no PROBLEM line, 1 means at least one, 2 means it could not read the file.
set -u
file=${1:?usage: check-video.sh <file> [expected seconds]}
expected=${2:-}
[ -f "$file" ] || { echo "no such file: $file"; exit 2; }
if command -v ffprobe >/dev/null; then probe=(ffprobe); else probe=(npx remotion ffprobe); fi
problems=0
problem() { echo "PROBLEM: $1"; problems=$((problems + 1)); }
field() { "${probe[@]}" -v error -select_streams "$1" -show_entries "$2" -of default=nw=1:nk=1 "$file" | head -1; }

video_codec=$(field v:0 stream=codec_name)
audio_codec=$(field a:0 stream=codec_name)
[ -n "$video_codec" ] || { echo "no video stream in $file"; exit 2; }
video_len=$(field v:0 stream=duration)
frame_rate=$(field v:0 stream=r_frame_rate)
avg_rate=$(field v:0 stream=avg_frame_rate)
size="$(field v:0 stream=width)x$(field v:0 stream=height)"
echo "video:  $video_codec $size $(field v:0 stream=pix_fmt), $frame_rate fps, $video_len s"
[ "$frame_rate" = "$avg_rate" ] || problem "frame rate is not constant: $frame_rate against $avg_rate"
if [ -n "$expected" ]; then
	awk -v a="$video_len" -v b="$expected" 'BEGIN { d = a - b; exit (d < 0 ? -d : d) > 0.5 }' ||
		problem "length is $video_len s, expected $expected s"
fi

if [ -z "$audio_codec" ]; then
	problem "no audio stream (fine only for a silent video)"
else
	audio_len=$(field a:0 stream=duration)
	echo "audio:  $audio_codec $(field a:0 stream=sample_rate) Hz, $audio_len s"
	awk -v a="$video_len" -v b="$audio_len" 'BEGIN { d = a - b; exit (d < 0 ? -d : d) > 0.1 }' ||
		problem "picture and sound differ in length: $video_len s against $audio_len s"
	loud=$(ffmpeg -hide_banner -nostats -i "$file" -vn -af ebur128=peak=true -f null - 2>&1 | sed -n '/Summary:/,$p')
	lufs=$(echo "$loud" | awk '/^ *I:/ {print $2}')
	peak=$(echo "$loud" | awk '/Peak:/ {print $2}')
	echo "sound:  $lufs LUFS loudness (a measure of how loud it feels), $peak dBFS true peak"
	awk -v l="$lufs" 'BEGIN { exit !(l < -40) }' && problem "almost no sound: $lufs LUFS"
	awk -v p="$peak" 'BEGIN { exit !(p > -0.5) }' && problem "the sound may clip: true peak $peak dBFS"
	silences=$(ffmpeg -hide_banner -nostats -i "$file" -vn -af silencedetect=n=-45dB:d=1.5 -f null - 2>&1 | grep silence_end | sed 's/.*silence_end: //')
	if [ -n "$silences" ]; then
		echo "$silences" | while read -r line; do echo "silence over 1.5 s, ends at (seconds | length): $line"; done
	fi
fi

blacks=$(ffmpeg -hide_banner -nostats -i "$file" -vf blackdetect=d=0.05:pix_th=0.05 -an -f null - 2>&1 | grep -o 'black_start.*')
if [ -n "$blacks" ]; then
	echo "$blacks" | while read -r line; do echo "PROBLEM: black frames: $line"; done
	problems=$((problems + 1))
fi

freezes=$(ffmpeg -hide_banner -nostats -i "$file" -vf freezedetect=n=0.001:d=4 -an -f null - 2>&1 | grep -E 'freeze_(start|duration)' | sed 's/.*lavfi.freezedetect.//' | paste -sd' ' -)
if [ -n "$freezes" ]; then
	echo "picture stopped for over 4 s (whole frame): $freezes"
fi

if [ "$problems" -gt 0 ]; then
	echo "$problems problem group(s). Open each one with your own eyes."
	exit 1
fi
echo "No PROBLEM lines. A file check cannot tell you the video is good: now look at the frames."
