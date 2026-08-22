// web-translate 合并脚本：DOM 提取 + 译文注入 + LaTeX 修复，一次 evaluate 完成。
// 用法：把 __TR__ 替换为 {"b0": "译文", ...} 的 JSON 字面量，通过 kimi-webbridge
// evaluate 在目标页面执行。可重复执行（已注入的块会跳过）。
// 依赖：页面正文容器选择器按站点调整（Wikipedia: #mw-content-text .mw-parser-output）。
(() => {
  const TR = __TR__;
  const CONTENT_SEL = '#mw-content-text .mw-parser-output';
  const SKIP_ANCESTOR = '.navbox,.metadata,.ambox,.mw-references-wrap,.reflist,table.sidebar,.sistersitebox';
  const NOISE_IN_BLOCK = '.mw-editsection,sup.reference,style,script';

  const content = document.querySelector(CONTENT_SEL) || document.querySelector('.mw-parser-output');
  if (!content) return JSON.stringify({error: 'content area not found'});

  if (!document.getElementById('zh-tr-style')) {
    const st = document.createElement('style');
    st.id = 'zh-tr-style';
    st.textContent = '.zh-tr{color:#0b6e4f;font-size:0.95em;margin:2px 0 14px;line-height:1.7;} li+.zh-tr{margin-left:40px;}';
    document.head.appendChild(st);
  }

  // 1. 提取 + 标记 + 注入（块顺序确定，id 与提取阶段一致）
  let tagged = 0, injected = 0;
  const blockTexts = [];
  content.querySelectorAll('h2,h3,h4,p,li').forEach(el => {
    if (el.closest(SKIP_ANCESTOR)) return;
    const clone = el.cloneNode(true);
    clone.querySelectorAll(NOISE_IN_BLOCK).forEach(x => x.remove());
    const text = clone.textContent.replace(/\[\d+\]/g, '').replace(/\s+/g, ' ').trim();
    if (!text) return;
    const id = 'b' + (tagged++);
    el.setAttribute('data-trid', id);
    blockTexts.push({id, tag: el.tagName.toLowerCase(), text});
    const zh = TR[id];
    if (zh === undefined) return;
    if (el.nextElementSibling && el.nextElementSibling.classList.contains('zh-tr')) return;
    const div = document.createElement('div');
    div.className = 'zh-tr';
    div.textContent = zh;
    el.insertAdjacentElement('afterend', div);
    injected++;
  });

  // 2. LaTeX 修复：把译文中的「字形噪声+LaTeX 源码」替换为原文已渲染的
  //    .mwe-math-element 克隆。只用 indexOf——宽松空白正则会在长公式上
  //    灾难性回溯，卡死页面 JS 线程。
  const norm = s => s.replace(/\s+/g, ' ');
  const mathReport = [];
  document.querySelectorAll('[data-trid]').forEach(el => {
    const zh = el.nextElementSibling;
    if (!zh || !zh.classList.contains('zh-tr')) return;
    const maths = [...el.querySelectorAll('.mwe-math-element')];
    if (!maths.length) return;
    let text = norm(zh.textContent);
    const holders = {};
    let ok = 0, fail = 0;
    maths.map((m, i) => ({m, i,
        full: norm(m.textContent),
        ann: norm(m.querySelector('annotation') ? m.querySelector('annotation').textContent : '')}))
      .sort((a, b) => b.full.length - a.full.length)  // 长式先匹配，防截断
      .forEach(({m, i, full, ann}) => {
        const token = '\u0000M' + i + '\u0000';
        let pat = null, idx = text.indexOf(full);
        if (idx >= 0) pat = full;
        else if (ann && (idx = text.indexOf(ann)) >= 0) pat = ann;
        if (!pat) { fail++; return; }
        text = text.slice(0, idx) + token + text.slice(idx + pat.length);
        holders[token] = m;
        ok++;
      });
    zh.textContent = '';
    text.split(/(\u0000M\d+\u0000)/).forEach(p => {
      if (holders[p]) zh.appendChild(holders[p].cloneNode(true));
      else if (p) zh.appendChild(document.createTextNode(p));
    });
    mathReport.push({id: el.getAttribute('data-trid'), ok, fail});
  });

  // 3. 清理公式克隆前的残留字形噪声（单字符 token 序列，如 "w ~ i"）
  const cleaned = [];
  document.querySelectorAll('.zh-tr .mwe-math-element').forEach(m => {
    const prev = m.previousSibling;
    if (!prev || prev.nodeType !== Node.TEXT_NODE) return;
    const raw = prev.textContent;
    const GLYPH = '(?:[A-Za-z0-9~()+\\u2212,]|[\\u0300-\\u036f])';
    const match = raw.match(new RegExp('(' + GLYPH + '(?:\\s+' + GLYPH + ')*)\\s*$'));
    if (!match) return;
    const tokens = match[1].trim().split(/\s+/);
    if (tokens.some(t => t.replace(/[\u0300-\u036f]/g, '').length > 1)) return;
    if (!/[A-Za-z~]/.test(match[1])) return;
    prev.textContent = raw.slice(0, raw.length - match[0].length) + ' ';
    cleaned.push(match[1].trim());
  });

  return JSON.stringify({tagged, injected, mathReport, cleaned, blocks: blockTexts});
})()
