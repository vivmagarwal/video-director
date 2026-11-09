import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {LineDiagram} from './LineDiagram';
import {FPS} from './kit';

registerRoot(() => (
	<Composition id="diagram" component={LineDiagram} durationInFrames={180} fps={FPS} height={1080} width={1920} />
));
