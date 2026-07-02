#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOP 流程合併工具
=================
把從正式環境匯出的多個 SOP flow JSON 檔案（例如 SOP1_F116.json、SOP60_xxx.json...）
讀進來、攤平成統一的節點集合，並轉換成 sop-editor.html / detail.html 可以使用的格式：
  { "title": "...", "startNode": "...", "nodes": { ... } }

用法：
  python3 merge_sop_flows.py --input-dir ./sop_exports --output sop_flow.json
  python3 merge_sop_flows.py --input-dir ./sop_exports --output sop_flow.json --start-node SOP1_Node1

參數說明：
  --input-dir   放所有匯出 JSON 檔案的資料夾（會抓資料夾裡所有 *.json）
  --output      輸出檔名，預設 sop_flow.json
  --start-node  手動指定流程起始節點 id。不指定的話，工具會自動猜測
                （找「從沒被任何節點指向過」的節點，通常就是主流程的入口，
                 例如 SOP1_Node1）。如果自動猜測抓到不只一個候選，會全部列出來，
                 你再用這個參數指定正確的那一個重跑。
"""

import json, re, os, glob, argparse, sys

def strip_html(s):
    if not s:
        return ''
    s = re.sub(r'<[^>]+>', ' ', s)
    s = (s.replace('&nbsp;', ' ').replace('&quot;', '"')
           .replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>'))
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def parse_one_file(filepath):
    """讀取單一匯出檔案，回傳 (root_node_id, flow_title, {node_id: raw_node_dict})"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    try:
        flow = data['data']['flow']
    except (KeyError, TypeError):
        print(f"⚠️  {filepath}：不是預期的匯出格式（找不到 data.flow），已略過。")
        return None, None, {}

    nodes = flow.get('nodes', [])
    flow_desc = flow.get('flow_desc', {}) or {}
    root_id = flow_desc.get('root_node_id')
    title = flow_desc.get('flow_desc') or flow_desc.get('task_bot_name') or os.path.basename(filepath)

    byid = {n['node_id']: n for n in nodes if 'node_id' in n}
    return root_id, title, byid


def convert_raw_node(nid, n, all_ids, issues):
    """把單一原始節點轉換成中介格式 {kind, text, options:[(label,next_id)]}"""
    name = n.get('node_name', '')
    content_id = n.get('content_id', '')
    c = n.get('content', {}) or {}

    options = []
    node_kind = None
    body_text = None

    if content_id == 'dms.system' and c.get('branch_list'):
        node_kind = 'system'
        for b in c['branch_list']:
            label = b.get('desc') or '（未命名分支）'
            nxt = (b.get('jump_node') or {}).get('next_node_id', '')
            options.append((label, nxt))
        body_text = name

    elif c.get('selector_intent'):
        node_kind = 'manual'
        body_text = strip_html(c.get('selector_utterance', '')) or name
        for s in c['selector_intent']:
            label = s.get('intent_text') or '（未命名選項）'
            nxt = (s.get('jump_node') or {}).get('next_node_id', '')
            options.append((label, nxt))

    elif content_id == 'dms.end':
        node_kind = 'end'
        ab = (c.get('answer_branch_list') or [{}])[0]
        msg = ''
        for m in ab.get('messages', []):
            rt = (m.get('answer_action') or {}).get('rich_text', '')
            msg += strip_html(rt)
        body_text = msg or name

    elif content_id in ('dms.note_and_reminder', 'dms.pending_reason'):
        node_kind = 'manual'
        ab = (c.get('answer_branch_list') or [{}])[0]
        msg = ''
        for m in ab.get('messages', []):
            rt = (m.get('answer_action') or {}).get('rich_text', '')
            msg += strip_html(rt)
        body_text = msg or name
        nxt = ((ab.get('advance_setting') or {}).get('next_node') or {}).get('next_node_id', '')
        end_tag = (ab.get('advance_setting') or {}).get('end_tag', False)
        if end_tag or not nxt:
            node_kind = 'end'
        else:
            options.append(('繼續', nxt))
    else:
        node_kind = 'end'
        body_text = name
        issues.append(f"節點 {nid}（{name}）content_id={content_id} 是未預期的類型，先當作結束節點處理，請人工檢查。")

    return {'kind': node_kind, 'text': body_text, 'options': options}


def main():
    ap = argparse.ArgumentParser(description="合併多個 SOP flow 匯出檔案")
    ap.add_argument('--input-dir', required=True, help="放所有匯出 JSON 檔案的資料夾")
    ap.add_argument('--output', default='sop_flow.json', help="輸出檔名")
    ap.add_argument('--start-node', default=None, help="手動指定起始節點 id")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.input_dir, '*.json')))
    if not files:
        print(f"❌ 在 {args.input_dir} 裡沒有找到任何 .json 檔案。")
        sys.exit(1)

    print(f"找到 {len(files)} 個檔案，開始讀取...")

    all_raw_nodes = {}      # node_id -> raw node dict
    candidate_roots = []    # (root_node_id, title, source_file)
    dup_count = 0

    for fp in files:
        root_id, title, byid = parse_one_file(fp)
        if root_id:
            candidate_roots.append((root_id, title, os.path.basename(fp)))
        for nid, n in byid.items():
            if nid in all_raw_nodes:
                dup_count += 1
            all_raw_nodes[nid] = n

    print(f"共讀到 {len(all_raw_nodes)} 個不重複節點（{dup_count} 個重複 id，已用後面檔案覆蓋前面）。")

    all_ids = set(all_raw_nodes.keys())

    # 決定 startNode
    start_node = args.start_node
    start_title = None
    if not start_node:
        # 優先找 root_node_id 指向、且該節點確實從沒被其他節點指到過的
        never_targeted = set(all_ids)
        for n in all_raw_nodes.values():
            c = n.get('content', {}) or {}
            for b in c.get('branch_list', []):
                t = (b.get('jump_node') or {}).get('next_node_id', '')
                never_targeted.discard(t)
            for s in c.get('selector_intent', []):
                t = (s.get('jump_node') or {}).get('next_node_id', '')
                never_targeted.discard(t)
            for b in c.get('answer_branch_list', []):
                t = ((b.get('advance_setting') or {}).get('next_node') or {}).get('next_node_id', '')
                never_targeted.discard(t)

        root_candidates = [r for r in candidate_roots if r[0] in never_targeted]
        if len(root_candidates) == 1:
            start_node, start_title, src = root_candidates[0]
            print(f"自動判斷起始節點：{start_node}（來自 {src}，標題：{start_title}）")
        elif len(root_candidates) > 1:
            print("\n⚠️ 找到多個候選起始節點，請用 --start-node 指定正確的那一個，重新執行：")
            for r in root_candidates:
                print(f"   - {r[0]}  (來自 {r[2]}, 標題: {r[1]})")
            sys.exit(1)
        else:
            print("\n❌ 沒辦法自動判斷起始節點，請用 --start-node 手動指定。")
            print("   候選 root_node_id 清單（來自各檔案的 flow_desc）：")
            for r in candidate_roots:
                print(f"   - {r[0]}  (來自 {r[2]}, 標題: {r[1]})")
            sys.exit(1)
    else:
        # 找對應標題
        for r in candidate_roots:
            if r[0] == start_node:
                start_title = r[1]
                break

    if start_node not in all_ids:
        print(f"❌ 指定的起始節點 {start_node} 不在任何一個檔案裡，請確認。")
        sys.exit(1)

    # 轉換所有節點
    issues = []
    mid_nodes = {}
    for nid, n in all_raw_nodes.items():
        mid_nodes[nid] = convert_raw_node(nid, n, all_ids, issues)

    converted = {}
    outcome_counter = [0]

    def make_outcome_id():
        outcome_counter[0] += 1
        return f"__auto_outcome_{outcome_counter[0]}"

    for nid, info in mid_nodes.items():
        if info['kind'] == 'end' or not info['options']:
            text = info['text'] or nid
            is_not_support = ('暫不支援' in text) or ('not support' in text.lower())
            converted[nid] = {
                'type': 'outcome',
                'result': 'incorrect' if is_not_support else 'correct',
                'text': text,
                'note': ''
            }
        else:
            opts_out = []
            for label, nxt in info['options']:
                if not nxt:
                    oid = make_outcome_id()
                    converted[oid] = {
                        'type': 'outcome', 'result': 'correct',
                        'text': f"{info['text']}：{label}",
                        'note': '（原始資料此分支未指定下一節點，視為結束）'
                    }
                    opts_out.append({'label': label, 'next': oid})
                elif nxt not in all_ids:
                    oid = make_outcome_id()
                    converted[oid] = {
                        'type': 'outcome', 'result': 'correct',
                        'text': f"{info['text']}：{label}（找不到目標節點 {nxt}）",
                        'note': f"這條分支指向的節點 {nxt} 沒有出現在你提供的任何一個檔案裡，可能還缺少對應的匯出檔案。"
                    }
                    opts_out.append({'label': label, 'next': oid})
                    issues.append(f"節點 {nid} 的分支「{label}」指向 {nxt}，在所有已提供的檔案裡都找不到，可能還缺這個流程的匯出檔。")
                else:
                    opts_out.append({'label': label, 'next': nxt})
            converted[nid] = {
                'type': 'question',
                'kind': info['kind'],
                'text': info['text'] or nid,
                'options': opts_out
            }

    output = {
        'title': start_title or 'Merged SOP Flow',
        'startNode': start_node,
        'nodes': converted
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"\n✅ 完成！輸出到 {args.output}（{size_kb:.1f} KB）")
    print(f"   總節點數：{len(converted)}（含自動產生的結束節點）")
    print(f"   仍缺資料的跨流程斷點數：{sum(1 for i in issues if '找不到' in i)}")

    if issues:
        print(f"\n=== 需要人工檢查的項目（共 {len(issues)} 筆）===")
        for i in issues[:50]:
            print("-", i)
        if len(issues) > 50:
            print(f"...（還有 {len(issues)-50} 筆，可以打開輸出檔案自己搜尋 __auto_outcome 找到全部）")


if __name__ == '__main__':
    main()
