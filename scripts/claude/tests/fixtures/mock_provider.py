#!/usr/bin/env -S python3 -S
"""Offline gh/glab API contract fixture. Never contacts a provider."""
import json, os, sys
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
state_path=Path(os.environ['CES_MOCK_STATE'])
s=json.loads(state_path.read_text()); args=sys.argv[1:]
method=args[args.index('--method')+1]; endpoint=args[-1]
path=urlsplit(endpoint).path; page=int(parse_qs(urlsplit(endpoint).query).get('page',['1'])[0]); payload=json.load(sys.stdin) if '--input' in args else None
s.setdefault('calls',[]).append({'method':method,'endpoint':endpoint,'payload':payload})
def done(value=None,error=None):
 state_path.write_text(json.dumps(s))
 if error is not None:
  print('HTTP '+str(error)+' fixture request failure',file=sys.stderr); sys.exit(1)
 print(json.dumps(value)); sys.exit(0)
provider=s.get('provider','github'); base='repos/org/repo/pulls/7' if provider=='github' else 'projects/group%2Fproject/merge_requests/7'
notes='repos/org/repo/issues/7/comments' if provider=='github' else base+'/notes'
inline=base+('/comments' if provider=='github' else '/discussions')
if s.get('fail_reads') and method=='GET' and path in [notes,inline]: done(error=503)
if path=='user': done({'id':11})
if path==base and method=='GET':
 s['meta_reads']=s.get('meta_reads',0)+1
 sha=s.get('sha','a'*40)
 if s.get('stale_after') and s['meta_reads']>s['stale_after']: sha='b'*40
 text=s.get('description','Controlled fixture description')
 if provider=='github': done({'state':s.get('state','open'),'head':{'sha':sha,'ref':'feature'},'base':{'sha':'c'*40,'ref':'main'},'number':7,'body':text,'title':'Controlled fixture MR','user':{'login':'fixture-author'},'changed_files':1,'mergeable':True,'mergeable_state':'clean'})
 done({'state':s.get('state','opened'),'sha':sha,'diff_refs':{'head_sha':sha,'base_sha':'c'*40,'start_sha':'d'*40},'iid':7,'description':text,'title':'Controlled fixture MR','author':{'username':'fixture-author'},'changes_count':'1','detailed_merge_status':'mergeable','has_conflicts':False,'user_notes_count':2})
if path==base+'/versions': done([{'head_commit_sha':s.get('version_sha',s.get('sha','a'*40)),'base_commit_sha':'c'*40,'start_commit_sha':'d'*40}])
if path in [base+'/files',base+'/diffs']:
 if s.get('missing_patch'): done([{'filename':'a.bin'}] if provider=='github' else [{'new_path':'a.bin','too_large':True}])
 done([{'filename':'app/Test.php','patch':'@@ -1 +1 @@\n-old\n+new'}] if provider=='github' else [{'old_path':'app/Test.php','new_path':'app/Test.php','diff':'@@ -1 +1 @@\n-old\n+new'}])
if path in [notes,inline]:
 kind='notes' if path==notes else 'inline'
 if method=='GET':
  items=s.setdefault(kind,[]); done(items[(page-1)*100:page*100])
 if method=='POST':
  if kind=='inline' and s.get('inline_error'): done(error=s['inline_error'])
  if kind=='notes' and s.get('summary_error'): done(error=s['summary_error'])
  ident=1000+sum(len(s.get(k,[])) for k in ['notes','inline'])
  comment={'id':ident,'body':payload['body'],'user':{'id':11},'author':{'id':11}}
  stored={'id':str(ident),'notes':[comment]} if provider=='gitlab' and kind=='inline' else comment
  s.setdefault(kind,[]).append(stored); s.setdefault('posted',[]).append({'kind':kind,'payload':payload}); done({'id':ident})
done(error=404)
