import {Composition, registerRoot} from 'remotion';
import {Film, meta} from './film-01';
registerRoot(() => <Composition {...meta} component={Film} />);
