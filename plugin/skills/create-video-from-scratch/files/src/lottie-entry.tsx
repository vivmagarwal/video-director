import {Lottie, type LottieAnimationData} from '@remotion/lottie';
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, cancelRender, Composition, continueRender, delayRender, registerRoot, staticFile} from 'remotion';

const Figure: React.FC = () => {
	const [handle] = useState(() => delayRender('Loading the Lottie file'));
	const [data, setData] = useState<LottieAnimationData | null>(null);
	useEffect(() => {
		fetch(staticFile('figure.json'))
			.then((r) => r.json())
			.then((json) => {
				setData(json);
				continueRender(handle);
			})
			.catch((err) => cancelRender(err));
	}, [handle]);
	return (
		<AbsoluteFill style={{alignItems: 'center', background: '#FBF7EF', justifyContent: 'center'}}>
			{data ? <Lottie animationData={data} style={{height: 400, width: 400}} /> : null}
		</AbsoluteFill>
	);
};
registerRoot(() => <Composition id="figure" component={Figure} width={1920} height={1080} fps={30} durationInFrames={60} />);
