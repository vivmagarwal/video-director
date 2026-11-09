import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
export const Title: React.FC<{text: string; color: string}> = ({text, color}) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame, [0, 149], [0, 300]);
  return (
    <AbsoluteFill style={{backgroundColor: color, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{transform: `translateY(${y}px)`, color: 'white', fontFamily: 'sans-serif', fontSize: 120}}>{text}</div>
      <div style={{position: 'absolute', bottom: 40, right: 60, color: 'white', fontFamily: 'sans-serif', fontSize: 40}}>frame {frame}</div>
    </AbsoluteFill>
  );
};
