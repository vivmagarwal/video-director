import {Composition} from 'remotion';
import * as F01 from './films/film-01';
export const Root = () => (
  <>
    {[F01].map((f) => (
      <Composition key={f.meta.id} {...f.meta} component={f.Film} />
    ))}
  </>
);
