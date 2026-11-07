# -*- coding: utf-8 -*-
"""主播名归一（唯一权威表：主播业绩/anchor_aliases.json）

用法（业绩解析脚本里）：
    from anchor_aliases import normalize, ALIASES
    rec['anchor'] = normalize(raw_name)

规则：
- `ALIASES` 是「旧名/错别字 → 标准名」的映射，只做一次替换（不做链式递归，避免 A→B→C 意外）；
- 表里没有的名字原样返回；
- 新增怪名前先改 JSON，再重跑解析，这样历史与当日口径一致。
"""
import io
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     '主播业绩', 'anchor_aliases.json')

_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            with io.open(_PATH, encoding='utf-8') as f:
                _cache = json.load(f).get('aliases', {})
        except (OSError, ValueError):
            _cache = {}
    return _cache


ALIASES = _load()


def normalize(name):
    """把源表里的主播名换成标准名；未登记的原样返回。"""
    if name is None:
        return name
    s = str(name).strip()
    return ALIASES.get(s, s)


def check_unknown(names, known):
    """返回既不在别名表、也不在页面既有名单里的名字（供解析脚本报警）。"""
    return sorted({n for n in map(str, names) if n.strip() and n not in known and n not in ALIASES})


if __name__ == '__main__':
    for k, v in sorted(ALIASES.items()):
        print('%s → %s' % (k, v))
    print('共 %d 条别名' % len(ALIASES))
