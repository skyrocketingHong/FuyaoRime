"""Build a Unicode 17 and source-backed Rime font audit corpus; does not test fonts."""

from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
import urllib.request
import yaml

BASE = 'https://www.unicode.org/Public/17.0.0/ucd/'
UCD_SHA256 = {
    'UnicodeData.txt': '2e1efc1dcb59c575eedf5ccae60f95229f706ee6d031835247d843c11d96470c',
    'Blocks.txt': 'c0edefaf1a19771e830a82735472716af6bf3c3975f6c2a23ffbe2580fbbcb15',
    'Scripts.txt': '9f5e50d3abaee7d6ce09480f325c706f485ae3240912527e651954d2d6b035bf',
    'DerivedCoreProperties.txt': '24c7fed1195c482faaefd5c1e7eb821c5ee1fb6de07ecdbaa64b56a99da22c08',
    'emoji/emoji-data.txt': '2cb2bb9455cda83e8481541ecf5b6dfda66a3bb89efa3fa7c5297eccf607b72b',
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1], help='FuyaoRime checkout containing upstream/rime-ice')
parser.add_argument('--ucd-dir', type=Path, default=Path('dist/font-audit/ucd'))
parser.add_argument('--output', type=Path, default=Path('dist/font-audit/corpus.json'))
parser.add_argument('--download', action='store_true', help='Download missing UCD files from fixed Unicode 17 URLs')
args = parser.parse_args()
ROOT, UCD, OUTPUT = args.repo.resolve(), args.ucd_dir, args.output
UCD.mkdir(parents=True, exist_ok=True)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
for name, expected_sha in UCD_SHA256.items():
    path = UCD / name.replace('/', '_')
    if not path.exists() and args.download:
        with urllib.request.urlopen(BASE + name, timeout=45) as response:
            content = response.read()
        if hashlib.sha256(content).hexdigest() != expected_sha:
            raise ValueError('Downloaded UCD content does not match pinned hash: ' + name)
        path.write_bytes(content)
    if not path.exists():
        raise FileNotFoundError(f'{path}: use --download to fetch the fixed Unicode 17 data')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ValueError('Local UCD content does not match pinned hash: ' + name)

def properties(name):
    result = defaultdict(set)
    for line in (UCD / name).read_text().splitlines():
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        span, prop, *_ = [field.strip() for field in line.split(';')]
        ends = span.split('..')
        low, high = int(ends[0], 16), int(ends[-1], 16)
        result[prop].update(range(low, high + 1))
    return result

categories = {}
pending = None
for line in (UCD / 'UnicodeData.txt').read_text().splitlines():
    fields = line.split(';')
    cp, name, category = int(fields[0], 16), fields[1], fields[2]
    if name.endswith(', First>'):
        pending = (cp, category)
    elif name.endswith(', Last>'):
        categories.update((value, pending[1]) for value in range(pending[0], cp + 1))
        pending = None
    else:
        categories[cp] = category

blocks = properties('Blocks.txt')
scripts = properties('Scripts.txt')
default_ignorable = properties('DerivedCoreProperties.txt')['Default_Ignorable_Code_Point']
emoji = properties('emoji_emoji-data.txt')
cjk = set().union(*(scripts[name] for name in ('Han', 'Hiragana', 'Katakana', 'Hangul', 'Bopomofo')))
standalone_exclusions = default_ignorable | emoji['Emoji_Modifier'] | set(range(0x1F1E6, 0x1F200))

COMMON_BLOCKS = '''General Punctuation
Superscripts and Subscripts
Currency Symbols
Letterlike Symbols
Number Forms
Arrows
Mathematical Operators
Miscellaneous Technical
Control Pictures
Optical Character Recognition
Enclosed Alphanumerics
Box Drawing
Block Elements
Geometric Shapes
Miscellaneous Symbols
Dingbats
Miscellaneous Mathematical Symbols-A
Supplemental Arrows-A
Braille Patterns
Supplemental Arrows-B
Miscellaneous Mathematical Symbols-B
Supplemental Mathematical Operators
Miscellaneous Symbols and Arrows
Supplemental Punctuation
CJK Symbols and Punctuation
Enclosed CJK Letters and Months
CJK Compatibility
Vertical Forms
CJK Compatibility Forms
Small Form Variants
Mahjong Tiles
Domino Tiles
Playing Cards
Musical Symbols
Mathematical Alphanumeric Symbols
Enclosed Alphanumeric Supplement
Enclosed Ideographic Supplement
Miscellaneous Symbols and Pictographs
Emoticons
Transport and Map Symbols
Geometric Shapes Extended
Supplemental Arrows-C
Supplemental Symbols and Pictographs
Chess Symbols
Symbols and Pictographs Extended-A'''.splitlines()

def visible(cp):
    return categories.get(cp, 'Cn')[0] in 'LNPS' and cp not in standalone_exclusions and cp not in cjk

items = {}
block_counts = Counter()
for block in COMMON_BLOCKS + ['Basic Latin', 'Latin-1 Supplement', 'Halfwidth and Fullwidth Forms']:
    for cp in sorted(blocks[block]):
        if not visible(cp):
            continue
        if block in ('Basic Latin', 'Latin-1 Supplement', 'Halfwidth and Fullwidth Forms'):
            if categories[cp][0] not in 'PS' and categories[cp] not in ('Nl', 'No'):
                continue
        text = chr(cp)
        items[text] = dict(id=f'U+{cp:04X}', text=text, category='block:' + block,
                           source=f'Unicode 17.0.0: {block}')
        block_counts[block] += 1

input_paths = []
input_counts = {}
rejected = Counter()
candidate_sources = defaultdict(set)
candidate_texts = set()

def candidate(text, source, allow_single_letter=False):
    if not text:
        return
    cps = list(map(ord, text))
    if any(categories.get(cp, 'Cn') in ('Cn', 'Cc', 'Cs', 'Co') for cp in cps):
        rejected['unassigned_control_private'] += 1
        return
    if any(cp in cjk for cp in cps):
        rejected['CJK_script'] += 1
        return
    regional_pair = len(cps) == 2 and all(0x1F1E6 <= cp <= 0x1F1FF for cp in cps)
    if not regional_pair and not any(visible(cp) for cp in cps):
        rejected['no_standalone_visible_base'] += 1
        return
    symbolic = any(categories.get(cp, '')[:1] in 'PS' or categories.get(cp) in ('Nl', 'No') for cp in cps)
    combining = any(categories.get(cp, '').startswith('M') or cp in default_ignorable for cp in cps)
    if not symbolic and not combining and not (allow_single_letter and len(cps) == 1):
        rejected['plain_word'] += 1
        return
    candidate_texts.add(text)
    candidate_sources[text].add(source)
    if text in items:
        return
    sequence = len(cps) > 1
    emoji_sequence = sequence and (0x200D in cps or 0xFE0F in cps or 0x20E3 in cps or
                                  any(cp in emoji['Emoji_Modifier'] or 0x1F1E6 <= cp <= 0x1F1FF for cp in cps))
    category = 'emoji-sequence' if emoji_sequence else ('combining-sequence' if combining else
               ('rime-symbol-sequence' if sequence else 'rime-symbol' if symbolic else 'rime-letter'))
    items[text] = dict(id='rime:' + hashlib.sha256(text.encode()).hexdigest()[:12], text=text,
                       category=category, source=source)

for name in ('symbols_v.yaml', 'symbols_caps_v.yaml'):
    rel = 'upstream/rime-ice/' + name
    path = ROOT / rel
    input_paths.append(path)
    table = yaml.safe_load(path.read_text())['symbols']
    input_counts[rel] = dict(keys=len(table), values=sum(map(len, table.values())))
    for key, values in table.items():
        if key.lower() in ('vhelp', 'vlist'):
            continue
        for value in values:
            candidate(value, rel + ':' + key, allow_single_letter=True)

rel = 'upstream/rime-ice/others/emoji-map.txt'
path = ROOT / rel
input_paths.append(path)
for n, line in enumerate(path.read_text().splitlines(), 1):
    if not line.strip() or line.lstrip().startswith('#'):
        continue
    candidate(line.split()[0], rel + ':' + str(n))

for name in ('opencc/emoji.txt', 'opencc/others.txt'):
    rel = 'upstream/rime-ice/' + name
    path = ROOT / rel
    input_paths.append(path)
    for n, line in enumerate(path.read_text().splitlines(), 1):
        if '\t' not in line or line.startswith('----------'):
            continue
        for value in line.split('\t', 1)[1].split():
            candidate(value, rel + ':' + str(n))

rel = 'upstream/rime-ice/default.yaml'
path = ROOT / rel
input_paths.append(path)
def visit(value, source):
    if isinstance(value, str):
        candidate(value, source)
    elif isinstance(value, list):
        for child in value:
            visit(child, source)
    elif isinstance(value, dict):
        for key, child in value.items():
            if not str(key).startswith('__'):
                visit(child, source + ':' + str(key))
visit(yaml.safe_load(path.read_text())['punctuator'], rel + ':punctuator')

for text, sources in candidate_sources.items():
    items[text]['source'] += ' | Rime:' + ';'.join(sorted(sources))

OUTPUT.write_text(json.dumps(list(items.values()), ensure_ascii=False, indent=2) + '\n')
metadata = dict(
    unicode_version='17.0.0', schema='flat array of {id,text,category,source}; no normalization or added selectors',
    count=len(items), block_count=sum(block_counts.values()), block_counts=dict(block_counts),
    distinct_candidate_strings=len(candidate_texts), candidate_only_count=len(items)-sum(block_counts.values()),
    categories=dict(Counter(item['category'] for item in items.values())), source_counts=input_counts,
    candidate_rejections=dict(rejected),
    filters=['Scalar sets: assigned L/N/P/S only, no CJK scripts, marks, separators, default-ignorables, emoji modifiers, regional indicators.',
             'Candidate sets: preserve exact sequences including VS/ZWJ/combining marks; exclude standalone formatting/marks and CJK scripts.',
             'No block sweep for ancient scripts, Alchemical Symbols, Byzantine Musical Symbols, Ancient Greek Musical Notation, Tai Xuan Jing, legacy computing; source candidates may still include them.',
             'CJK-named blocks retain only non-CJK-script punctuation, number symbols, and compatibility units.'],
    ucd_sources={name: dict(url=BASE+name, sha256=sha) for name, sha in UCD_SHA256.items()},
    input_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in input_paths},
    corpus_sha256=hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
)
OUTPUT.with_suffix('.metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
style = yaml.safe_load((ROOT / 'overlay/squirrel.custom.yaml').read_text())['patch']['style']
OUTPUT.with_suffix('.style.json').write_text(json.dumps(style, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({key: metadata[key] for key in ('count','block_count','distinct_candidate_strings','candidate_only_count','categories','candidate_rejections')}, ensure_ascii=False, indent=2))
