import {Audio, staticFile} from 'remotion';
import {Title} from '../kit/Title';
export const meta = {id: 'film-01', durationInFrames: 150, fps: 30, width: 1280, height: 720};
export const Film = () => (
  <>
    <Title text="Film 01" color="#264653" />
    <Audio src={staticFile('films/film-01/voice.mp3')} />
  </>
);
