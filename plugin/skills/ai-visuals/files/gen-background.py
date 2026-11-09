#!/usr/bin/env python3
"""Make one background image with the Gemini API, and keep a note of how it was made.

    python3 gen-background.py prompt.txt public/bg/room.png              # shows the plan and the cost, spends nothing
    python3 gen-background.py prompt.txt public/bg/room.png --yes        # pays for one image

Options: --ref image.png (repeatable; a style reference sent with the prompt)
         --model gemini-nano-banana-2.1   --aspect 16:9   --size 2K

Writes the image, plus <image>.json beside it: prompt, model, date, cost estimate,
references and their SHA-256. The key comes from GEMINI_API_KEY and is sent only in
a request header. It is never printed or saved.

Written from Google's public docs on 2026-11-09 (the Interactions API). NOT RUN
against the paid API: only the no-key path, the plan and a local stand-in server
were tested. Prices are the Standard prices shown on the public pricing page that
day. Check them before you trust a total.
"""
import argparse
import base64
import datetime
import hashlib
import json
import mimetypes
import os
import pathlib
import sys
import urllib.error
import urllib.request

# US dollars for one output image, by model and size. Add a model or fix a price here.
PRICES = {
    'gemini-nano-banana-2.1': {'1K': 0.0336, '2K': 0.0504, '4K': 0.113},
    'gemini-3.1-flash-image': {'1K': 0.067, '2K': 0.101, '4K': 0.151},
    'gemini-3-pro-image': {'1K': 0.134, '2K': 0.134, '4K': 0.24},
}
EXTENSIONS = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp'}

parser = argparse.ArgumentParser()
parser.add_argument('prompt', type=pathlib.Path, help='a text file holding the prompt')
parser.add_argument('out', type=pathlib.Path, help='the image to write')
parser.add_argument('--ref', type=pathlib.Path, action='append', default=[])
parser.add_argument('--model', default='gemini-nano-banana-2.1')
parser.add_argument('--aspect', default='16:9')
parser.add_argument('--size', default='2K', help='1K, 2K or 4K. Uppercase K, or the API refuses it')
parser.add_argument('--timeout', type=int, default=300)
parser.add_argument('--yes', action='store_true', help='really call the paid API')
parser.add_argument('--base-url', default='https://generativelanguage.googleapis.com/v1beta')
args = parser.parse_args()

text = args.prompt.read_text()
price = PRICES.get(args.model, {}).get(args.size)
cost = f'about ${price:.3f} per image, plus a little for input' if price else 'unknown: check the pricing page'
print(f'model:  {args.model}\nsize:   {args.size}, {args.aspect}\nrefs:   {len(args.ref)}\ncost:   {cost}\nprompt: {text[:300]}')
if not args.yes:
    print('Nothing was sent and nothing was spent. Add --yes once the user has agreed the cost.')
    sys.exit(0)

key = os.environ.get('GEMINI_API_KEY')
if not key:
    sys.exit('GEMINI_API_KEY is not set. Ask the user to add it to the session environment. Do not paste a key into a file.')

parts = []
refs = []
for ref in args.ref:
    data = ref.read_bytes()
    kind = mimetypes.guess_type(ref.name)[0] or 'image/png'
    refs.append({'path': str(ref), 'sha256': hashlib.sha256(data).hexdigest()})
    parts.append({'type': 'image', 'mime_type': kind, 'data': base64.b64encode(data).decode()})
parts.append({'type': 'text', 'text': text})

request = urllib.request.Request(
    f'{args.base_url}/interactions',
    data=json.dumps({
        'model': args.model,
        'input': parts,
        'response_format': {'type': 'image', 'aspect_ratio': args.aspect, 'image_size': args.size},
    }).encode(),
    headers={'Content-Type': 'application/json', 'x-goog-api-key': key, 'Api-Revision': '2026-05-20'},
    method='POST',
)
started = datetime.datetime.now(datetime.timezone.utc)
try:
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        reply = json.load(response)
except urllib.error.HTTPError as error:
    # The body names the problem (quota, safety, a bad field). It holds no key.
    sys.exit(f'HTTP {error.code}: {error.read().decode(errors="replace")[:2000]}')
except urllib.error.URLError as error:
    sys.exit(f'Could not reach the API: {error.reason}. Test the host with curl, and ask the user to allow it if the proxy refuses it.')
seconds = (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()

# Over plain REST the image is inside steps[]. The last image block is the result.
blocks = [
    block
    for step in reply.get('steps', []) if step.get('type') == 'model_output'
    for block in step.get('content', []) if block.get('type') == 'image'
]
if not blocks:
    sys.exit(f'No image came back. Status: {reply.get("status")}. Reply without data: {json.dumps(reply)[:1500]}')
image = base64.b64decode(blocks[-1]['data'])
kind = blocks[-1].get('mime_type', 'image/png')

# Save under the extension of what really came back.
out = args.out.with_suffix(EXTENSIONS.get(kind, args.out.suffix))
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(image)
note = {
    'file': str(out),
    'sha256': hashlib.sha256(image).hexdigest(),
    'prompt': text,
    'model': args.model,
    'provider': 'Gemini API, interactions endpoint',
    'interaction_id': reply.get('id'),
    'date': started.isoformat(timespec='seconds'),
    'seconds': round(seconds, 1),
    'aspect': args.aspect,
    'size': args.size,
    'mime_type': kind,
    'refs': refs,
    'usage': reply.get('usage'),
    'cost_usd_estimate': price,
    'cost_note': 'An estimate from the public price list, not a bill. Check the account billing page.',
}
pathlib.Path(f'{out}.json').write_text(json.dumps(note, indent=2) + '\n')
print(f'wrote {out} ({len(image) / 1e6:.1f} MB, {seconds:.0f} s) and {out}.json')
