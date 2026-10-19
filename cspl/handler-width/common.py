"""Opyt 22: breadth of handler use. Shared helpers: REST calls to Extella, model calls, handler registration."""
import json, os, time, urllib.request, ast
TOKEN = open(os.path.expanduser('~/.extella/api_token.txt')).read().strip()
ENV = dict(l.split('=', 1) for l in open(os.path.expanduser('~/extella-recon/.env')).read().splitlines() if '=' in l and not l.lstrip().startswith('#'))
clean = lambda v: v.strip().strip('"').strip("'")
MAC = clean(ENV['RECON_DEVICE_A'])
MODEL_AGENT = os.environ.get('OPYT22_AGENT', '<agent-large-model>')   # platform Qwen max by default; qwen-flash: <agent-small-model>
TAG = os.environ.get('OPYT22_TAG', '')
SCOPE_AGENT = '<agent-large-model>'                          # experts of this experiment live in the scope of the same clean agent

def api(path, body, agent=SCOPE_AGENT, timeout=180):
    r = urllib.request.Request('https://api.extella.ai/api' + path, data=json.dumps(body).encode(),
        headers={'X-Auth-Token': TOKEN, 'X-Profile-Id': 'default', 'X-Agent-Id': agent, 'Content-Type': 'application/json'})
    try:
        return json.load(urllib.request.urlopen(r, timeout=timeout))
    except urllib.error.HTTPError as e:
        return {'status': 'http_error', 'code': e.code, 'body': e.read()[:500].decode('utf-8', 'ignore')}

def unwrap(out):
    r = out.get('result', out) if isinstance(out, dict) else out
    for _ in range(4):
        if isinstance(r, dict) and 'result' in r and len(r) <= 4: r = r['result']
        elif isinstance(r, str):
            for loader in (json.loads, ast.literal_eval):
                try: r = loader(r); break
                except Exception: pass
            else: break
        else: break
    return r

def ask_model(prompt, timeout=240):
    """One stateless call to the platform model. Returns (text, seconds, usage dict or None)."""
    t = time.time()
    out = api('/agent/run', {'agent_id': MODEL_AGENT, 'input': prompt, 'store': False, 'run_timeout': timeout}, timeout=timeout + 30)
    text, usage = '', None
    if isinstance(out, dict):
        usage = out.get('usage')
        for item in out.get('output', []) or []:
            for c in item.get('content', []) or []:
                if c.get('type') in ('output_text', 'text'): text += c.get('text', '')
        if not text: text = out.get('output_text') or out.get('text') or ''
    return text.strip(), round(time.time() - t, 1), usage, (out if not text else None)

def save_expert(name, code, cspl):
    return api('/expert/save', {'name': name, 'code': code, 'description': 'opyt22 ' + name, 'cspl': cspl})

def run_expert(name, params=None, device=None):
    t = time.time()
    out = api('/expert/run', {'name': name, 'params': params or {}, 'targets': [device or MAC]})
    return unwrap(out), round(time.time() - t, 1)

def registrar_code(lang, handler_text):
    """Expert that registers handler_text as the handler of language `lang` on the device it runs on."""
    assert chr(92) not in handler_text and "'" * 3 not in handler_text
    name = 'opyt22_register_' + lang
    code = ('$extens("include.py")\ninclude("import os", [])\n\ndef %s() -> dict:\n    import disnet\n    handler_code = \'\'\'%s\'\'\'\n'
            '    d = disnet.Disnet(url="https://disnet.extella.ai")\n'
            '    envelope = {"filtered_source_code": "", "func_name": "", "args": None, "kwargs": None, "cspl": "%s", "response_format": None}\n'
            '    d.container(code=handler_code, func_name="%s", container_path="%s", args=None, kwargs=envelope, cspl_type="fython", push=False)\n'
            '    return {"status": "success", "registered": "%s", "bytes": len(handler_code)}\n') % (name, handler_text, lang, lang, lang, lang)
    return name, code

def register(lang, handler_text, device=None):
    name, code = registrar_code(lang, handler_text)
    s = save_expert(name, code, 'fython')
    r, sec = run_expert(name, device=device)
    return {'save': s.get('status') if isinstance(s, dict) else s, 'run': r, 'seconds': sec}
