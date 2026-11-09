import React from 'react';
import {AbsoluteFill, Audio, Composition, staticFile} from 'remotion';
import type {Caption} from '@remotion/captions';
import {Captions} from './Captions';

const FPS = 30;

type Props = {captions: Caption[]; bottomInset: number; left: number; right: number; fontSize: number};

const Film: React.FC<Props> = ({captions, bottomInset, left, right, fontSize}) => (
	<AbsoluteFill style={{background: 'linear-gradient(135deg, #2563eb, #d8b4fe)'}}>
		{/* Your picture goes here, under the captions. */}
		<Audio src={staticFile('voice.mp3')} />
		<Captions
			captions={captions}
			bottomInset={bottomInset}
			left={left}
			right={right}
			fontSize={fontSize}
			keepTogether={['six weeks']}
		/>
	</AbsoluteFill>
);

// Read the words once, before the render, and set the length of the video from them.
const calculateMetadata = async ({props}: {props: Props}) => {
	const captions: Caption[] = await (await fetch(staticFile('voice.captions.json'))).json();
	const seconds = captions[captions.length - 1].endMs / 1000 + 1;
	return {durationInFrames: Math.ceil(seconds * FPS), props: {...props, captions}};
};

export const Root: React.FC = () => (
	<>
		<Composition
			id="landscape"
			component={Film}
			width={1920}
			height={1080}
			fps={FPS}
			durationInFrames={30}
			defaultProps={{captions: [], bottomInset: 108, left: 200, right: 200, fontSize: 56}}
			calculateMetadata={calculateMetadata}
		/>
		<Composition
			id="vertical"
			component={Film}
			width={1080}
			height={1920}
			fps={FPS}
			durationInFrames={30}
			defaultProps={{captions: [], bottomInset: 672, left: 120, right: 300, fontSize: 72}}
			calculateMetadata={calculateMetadata}
		/>
	</>
);
