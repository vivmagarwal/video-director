// WCAG contrast ratio between pairs of colours.
//   node contrast.mjs '#1F2430' '#FBF7EF' ['#C2410C' '#FBF7EF' ...]
// 4.5 or more is the usual target for normal text, 3 or more for large text.
const channel = (v) => {
	const c = v / 255;
	return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
const luminance = (hex) => {
	const n = Number.parseInt(hex.replace('#', ''), 16);
	const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255];
	return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
};
const args = process.argv.slice(2);
if (args.length < 2 || args.length % 2 === 1) {
	console.error("Usage: node contrast.mjs '#text' '#ground' ['#text2' '#ground2' ...]");
	process.exit(1);
}
for (let i = 0; i < args.length; i += 2) {
	const [a, b] = [luminance(args[i]), luminance(args[i + 1])];
	const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
	const verdict = ratio >= 4.5 ? 'fine for any text' : ratio >= 3 ? 'large text only' : 'too low';
	console.log(`${args[i]} on ${args[i + 1]}: ${ratio.toFixed(2)}:1  ${verdict}`);
}
