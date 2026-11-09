import {AbsoluteFill, Composition, interpolate, registerRoot, useCurrentFrame} from 'remotion';

const Smoke = () => {
  const frame = useCurrentFrame();
  const x = interpolate(frame, [0, 59], [0, 1400]);
  return (
    <AbsoluteFill style={{backgroundColor: '#14213d'}}>
      <div
        style={{
          position: 'absolute',
          top: 200,
          left: 100,
          color: 'white',
          fontFamily: 'sans-serif',
          fontSize: 120,
        }}
      >
        Smoke test
      </div>
      <div
        style={{
          position: 'absolute',
          top: 600,
          left: 100 + x,
          width: 200,
          height: 200,
          backgroundColor: '#fca311',
        }}
      />
    </AbsoluteFill>
  );
};

export const Root = () => (
  <Composition
    id="smoke"
    component={Smoke}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={60}
  />
);

registerRoot(Root);
