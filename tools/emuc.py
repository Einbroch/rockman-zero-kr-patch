"""emucap-mcp 를 직접 띄워 쓰는 작은 MCP 클라이언트.

  python emuc.py serve            # 백그라운드: emucap-mcp 자식 실행 + 127.0.0.1:47910 JSON 줄 서버
  python emuc.py call TOOL '{...}' # 도구 호출, 결과 JSON 출력
  python emuc.py stop
환경: EMUCAP_PORT(기본 47810) — 다른 세션의 47800 과 겹치지 않게.
"""
import sys, os, json, socket, subprocess, threading

EXE = r'D:\Games\Kor Patch\CLude\emucap\target\release\emucap-mcp.exe'
CTRL_PORT = 47910


def serve():
    env = dict(os.environ)
    env.setdefault('EMUCAP_PORT', '47810')
    p = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=open(os.path.join(os.path.dirname(__file__), '..', 'scratch', 'emuc_stderr.log'), 'wb'), env=env)
    lock = threading.Lock()
    nid = [0]

    def rpc(method, params=None, notify=False):
        with lock:
            msg = {'jsonrpc': '2.0', 'method': method}
            if params is not None:
                msg['params'] = params
            if not notify:
                nid[0] += 1
                msg['id'] = nid[0]
            p.stdin.write((json.dumps(msg) + '\n').encode()); p.stdin.flush()
            if notify:
                return None
            while True:
                line = p.stdout.readline()
                if not line:
                    raise RuntimeError('server exited')
                r = json.loads(line)
                if r.get('id') == msg['id']:
                    return r

    rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'emuc', 'version': '1'}})
    rpc('notifications/initialized', notify=True)
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('127.0.0.1', CTRL_PORT)); s.listen(4)
    print('ready', flush=True)
    while True:
        c, _ = s.accept()
        f = c.makefile('rwb')
        req = json.loads(f.readline())
        if req.get('stop'):
            f.write(b'{"stopped":true}\n'); f.flush(); c.close(); p.kill(); return
        try:
            r = rpc('tools/call', {'name': req['tool'], 'arguments': req.get('args', {})})
        except Exception as e:
            r = {'error': str(e)}
        f.write((json.dumps(r) + '\n').encode()); f.flush(); c.close()


def call(tool, args):
    c = socket.create_connection(('127.0.0.1', CTRL_PORT), timeout=600)
    f = c.makefile('rwb')
    f.write((json.dumps({'tool': tool, 'args': args}) + '\n').encode()); f.flush()
    r = json.loads(f.readline())
    res = r.get('result', r)
    out = []
    for item in res.get('content', []) if isinstance(res, dict) else []:
        if item.get('type') == 'text':
            out.append(item['text'])
        else:
            out.append(f"[{item.get('type')}]")
    return '\n'.join(out) if out else json.dumps(r)


if __name__ == '__main__':
    if sys.argv[1] == 'serve':
        serve()
    elif sys.argv[1] == 'stop':
        c = socket.create_connection(('127.0.0.1', CTRL_PORT)); c.sendall(b'{"stop":true}\n'); print(c.recv(100))
    else:
        print(call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}))
