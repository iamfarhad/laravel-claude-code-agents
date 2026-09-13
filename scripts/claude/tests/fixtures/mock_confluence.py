#!/usr/bin/env python3
"""Offline stand-in for `curl` as lib/confluence.php invokes it. State file: CES_CONFLUENCE_MOCK (JSON)."""
import json, os, sys
state_path=os.environ['CES_CONFLUENCE_MOCK']; state=json.load(open(state_path))
args=sys.argv[1:]; url=args[-1]
config=sys.stdin.read() if '-K' in args else ''
state['calls']=state.get('calls',[])+[{'url':url,'header_config':config,'argv':args[:-1]}]
json.dump(state,open(state_path,'w'))
if state.get('unreachable'):
    sys.stderr.write("curl: (7) Failed to connect to host port 443: Connection refused\n"); sys.exit(7)
body='{"message":"not found"}'; code=404
prefix=state.get('prefix','/rest/api/content/')
for pid,page in state.get('pages',{}).items():
    if prefix+pid+'?' in url:
        if state.get('deny'): body='{"message":"forbidden"}'; code=403
        else: body=json.dumps({'id':pid,'title':page['title'],'version':{'number':page.get('version',1)},'space':{'key':page.get('space','B2BTP')},'body':{'storage':{'value':page['storage']}}}); code=200
if '-w' in args: sys.stdout.write(body+"\n"+str(code))
else: sys.stdout.write(body)
