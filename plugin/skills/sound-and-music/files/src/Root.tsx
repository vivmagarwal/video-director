import React from 'react';
import {AbsoluteFill, Audio, Composition, Sequence, staticFile} from 'remotion';
import {Bed} from './Bed';
import {Sfx} from './Sfx';

// 3 s of music alone, then the voice, then a tail. speech comes from the captions file.
const VOICE_AT = 90;
const Film: React.FC = () => (
	<AbsoluteFill style={{background: '#16213e'}}>
		<Bed src="music.mp3" openDb={-7.7} duckedDb={-17.7} speech={[[VOICE_AT + 4, VOICE_AT + 390], [VOICE_AT + 424, VOICE_AT + 870]]} />
		<Sequence from={VOICE_AT} layout="none">
			<Audio src={staticFile('voice.mp3')} />
		</Sequence>
		<Sfx src="whoosh.wav" at={45} peak={0.078} gainDb={-8} />
	</AbsoluteFill>
);

export const Root: React.FC = () => (
	<Composition id="mix" component={Film} width={1280} height={720} fps={30} durationInFrames={1110} />
);
