#!/usr/bin/env python3
"""web-translate 的 Notion 专用工具。

子命令：
  extract <page-url-or-id> <out-blocks.json>   通过 loadPageChunk 公开 API 提取全文块
  build-css <tr_all.json> <out-tr.css>         把 {blockId: 译文} 生成 ::after 注入样式表
  inject-js <tr.css>                           打印可传给 webbridge evaluate 的注入 JS

用法见 SKILL.md 的「Notion 站点」一节。
"""
import json, re, sys, urllib.request


def page_id(s):
    m = re.search(r'([0-9a-f]{32})', s.replace('-', ''))
    if not m:
        sys.exit('cannot parse page id from ' + s)
    h = m.group(1)
    return f'{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}'


def fetch_chunks(pid, host):
    blocks, cursor, n = {}, {'stack': []}, 0
    while True:
        body = json.dumps({'pageId': pid, 'limit': 100, 'cursor': cursor,
                           'chunkNumber': n, 'verticalColumns': False}).encode()
        req = urllib.request.Request(host + '/api/v3/loadPageChunk', data=body,
                                     headers={'Content-Type': 'application/json',
                                              'User-Agent': 'Mozilla/5.0'})
        d = json.loads(urllib.request.urlopen(req, timeout=30).read())
        blocks.update(d['recordMap'].get('block', {}))
        cursor = d['cursor']
        n += 1
        if not cursor.get('stack'):
            return blocks


def rich_text(title):
    out = []
    for seg in title or []:
        if not isinstance(seg, list) or not seg:
            continue
        text, decs = seg[0], seg[1] if len(seg) > 1 else []
        eq = next((d[1] for d in decs or [] if d[0] == 'e'), None)
        out.append('$' + eq + '$' if eq is not None else text)
    return ''.join(out)


TYPE_TAG = {'header': 'h1', 'sub_header': 'h2', 'sub_sub_header': 'h3',
            'text': 'p', 'bulleted_list': 'li', 'numbered_list': 'li',
            'quote': 'quote', 'to_do': 'li', 'toggle': 'p', 'callout': 'callout'}


def extract(url, out):
    pid = page_id(url)
    m = re.match(r'https?://[^/]+', url)
    host = m.group(0) if m else 'https://www.notion.so'
    blocks = fetch_chunks(pid, host)
    result = []

    def walk(bid):
        entry = blocks.get(bid, {}).get('value')
        if not entry:
            return
        b = entry.get('value', entry)  # recordMap v3 多包一层 value
        if not isinstance(b, dict) or 'type' not in b:
            return
        btype, props = b['type'], b.get('properties') or {}
        if btype in TYPE_TAG:
            text = ' '.join(rich_text(props.get('title')).split())
            if text:
                result.append({'id': bid, 'tag': TYPE_TAG[btype], 'text': text})
        elif btype == 'image':
            cap = ' '.join(rich_text(props.get('caption')).split())
            result.append({'id': bid, 'tag': 'image',
                           'text': ('[图] ' + cap) if cap else '[图]'})
        elif btype == 'equation':
            result.append({'id': bid, 'tag': 'equation',
                           'text': '$$' + rich_text(props.get('title')) + '$$'})
        if btype in ('column_list', 'column', 'toggle', 'page'):
            for cid in b.get('content') or []:
                walk(cid)

    page = blocks[pid]['value']
    page = page.get('value', page)
    for cid in page.get('content', []):
        walk(cid)
    json.dump(result, open(out, 'w'), ensure_ascii=False, indent=1)
    print(f'blocks: {len(result)}, chars: {sum(len(r["text"]) for r in result)} -> {out}')


def css_escape(s):
    return (s.replace('\\', '\\\\').replace('"', '\\"').replace('</', '<\\/')
             .replace('\n', '\\A ').replace('\r', ' '))


def build_css(tr_path, out):
    tr = json.load(open(tr_path))
    rules = ['[data-block-id="%s"]::after{content:"%s";display:block;color:#0b6e4f;'
             'font-size:0.9em;line-height:1.7;margin-top:6px;font-weight:normal;'
             'font-style:normal;white-space:pre-wrap;}' % (bid, css_escape(zh))
             for bid, zh in tr.items() if zh.strip() and zh.strip() != '[图]']
    open(out, 'w').write('\n'.join(rules))
    print(f'rules: {len(rules)} -> {out}')


def inject_js(css_path):
    css = open(css_path).read()
    print("""(() => {
  const old = document.getElementById('zh-tr-style');
  if (old) old.remove();
  const st = document.createElement('style');
  st.id = 'zh-tr-style';
  st.textContent = %s;
  document.head.appendChild(st);
  return 'zh-tr-style: ' + document.styleSheets.length + ' sheets';
})()""" % json.dumps(css))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'extract':
        extract(sys.argv[2], sys.argv[3])
    elif cmd == 'build-css':
        build_css(sys.argv[2], sys.argv[3])
    elif cmd == 'inject-js':
        inject_js(sys.argv[2])
    else:
        sys.exit(__doc__)
