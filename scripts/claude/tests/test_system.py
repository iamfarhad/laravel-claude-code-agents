#!/usr/bin/env python3
"""CES offline regression suite. No network or real provider credentials required.
Run: python3 scripts/claude/tests/test_system.py
Optional: --json /absolute/path/report.json --package /path/to/package
"""
from __future__ import annotations
import argparse, copy, hashlib, html, json, os, re, shlex, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[3]
PHP=shutil.which('php')
REPORT=None

def run(argv,cwd=None,data=None,env=None,timeout=25):
 return subprocess.run([str(x) for x in argv],cwd=cwd,input=None if data is None else (data if isinstance(data,str) else json.dumps(data)),text=True,capture_output=True,env=env,timeout=timeout)
PRD_SECTIONS=['Problem Statement','Context / Evidence','Goals','Non-Goals','Users / Actors','Functional Requirements','Acceptance Criteria','Failure / Negative Behavior','Non-Functional Requirements','Observability Requirements','Dependencies','Rollout / Migration Expectations','Success Metrics','Risks','Open Questions','Out of Scope']
def valid_prd():
 sections=PRD_SECTIONS
 text='# Controlled test PRD\nStatus: READY_FOR_ENGINEERING\nOwner: Test fixture\n\n'
 for sec in sections:
  text+='## '+sec+'\n'
  if sec=='Functional Requirements': text+='- FR-01: Return the expected controlled result.\n'
  elif sec=='Acceptance Criteria': text+='### AC-01: Valid input\nGiven: An isolated fixture\nWhen: The controlled action executes\nThen: The expected assertion passes\nVerification: The controlled fixture assertion\nRequirement: FR-01\n'
  elif sec=='Open Questions': text+='None\n'
  else: text+='Concrete fixture content for '+sec+'.\n'
  text+='\n'
 return text

class Fixture(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ces-tests-'); self.outer=Path(self.tmp.name); self.repo=self.outer/'repo'; shutil.copytree(P,self.repo,ignore=shutil.ignore_patterns('__pycache__','runtime','backups'))
  self.env=dict(os.environ); self.env.update({'GIT_CONFIG_GLOBAL':os.devnull,'GIT_CONFIG_NOSYSTEM':'1','GIT_TERMINAL_PROMPT':'0'})
  (self.repo/'docs/prd').mkdir(parents=True,exist_ok=True); (self.repo/'docs/prd/T-1.md').write_text(valid_prd())
  (self.repo/'.gitignore').write_text('.claude/engineering-system/runtime/\n.claude/engineering-system/backups/\n__pycache__/\n')
  self.conf=json.loads((self.repo/'.claude/engineering-system/config.json').read_text())
  self.conf.update({'allowed_hosts':['github.test','gitlab.test'],'execution_isolated':True,'checks':{m:{'trusted':True,'kind':'test','roles':['tester','regression-tester','developer','qa-support','incident-investigator','performance-reviewer'],'argv':[PHP,'scripts/claude/tests/fixtures/check.php',m],'timeout_seconds':1 if m=='timeout' else 10,'env':{'APP_ENV':'testing'}} for m in ['pass','fail','timeout','mutate','noisy','env']}})
  self.saveconf(); self.git('init','-q'); self.git('config','user.email','test@example.invalid'); self.git('config','user.name','CES Test'); self.git('add','.'); self.git('commit','-qm','fixture base')
  self.sha=self.git('rev-parse','HEAD').stdout.strip(); self.session='test-session'; self.counter=0
 def tearDown(self): self.tmp.cleanup()
 def saveconf(self): (self.repo/'.claude/engineering-system/config.json').write_text(json.dumps(self.conf))
 def git(self,*args):
  r=run(['git',*args],self.repo,env=self.env); self.assertEqual(r.returncode,0,r.stderr); return r
 def php(self,body,data=None,lib='workflow'):
  code="require 'scripts/claude/lib/"+lib+".php'; $x=json_decode(stream_get_contents(STDIN),true); try { "+body+" } catch (Throwable $e) { echo json_encode(['exception'=>$e->getMessage()]); exit(2); }"
  return run([PHP,'-r',code],self.repo,data or {},self.env)
 def decode(self,r,rc=0):
  self.assertEqual(r.returncode,rc,r.stderr+'\n'+r.stdout)
  try: return json.loads(r.stdout)
  except json.JSONDecodeError: self.fail('Non-JSON output: '+r.stdout+' '+r.stderr)
 def open(self,workflow='feature',**extra):
  req={'task_id':'T-1','workflow':workflow,'prd_path':'docs/prd/T-1.md',**extra}
  if workflow in ['peer-review','tech-lead-review','engineering-manager-review','architecture','release']: req.pop('prd_path',None)
  return self.decode(self.php("CES\\output(CES\\openTask('test-session',$x));",req))
 def report(self,role,status,**extra):
  self.counter+=1
  obj={'task_id':'T-1','status':status,'summary':'Controlled evidence-backed report','evidence':['Inspected controlled fixture'],'findings':[],'handoff':'Next verified phase',**extra}
  return self.php("CES\\output(CES\\recordReport('test-session',$x['role'],$x['agent_id'],$x['report']));",{'role':role,'agent_id':str(self.counter),'report':obj})
 def ready(self):
  self.open(); self.decode(self.report('product-manager','READY_FOR_ENGINEERING',prd_path='docs/prd/T-1.md')); self.decode(self.report('prd-reviewer','PASS'))
 def hook(self,role,tool,args,session=None):
  return run([PHP,'scripts/claude/hooks/pre-tool.php'],self.repo,{'session_id':session or self.session,'agent_type':role,'agent_id':'agent-'+role,'cwd':str(self.repo),'tool_name':tool,'tool_input':args},self.env)
 def command(self,request): return "php scripts/claude/bin/ces.php <<'CES_REQUEST'\n"+json.dumps(request)+"\nCES_REQUEST"
 def broker(self,role,request):
  h=self.hook(role,'Bash',{'command':self.command(request),'timeout':10000})
  if h.returncode: return h
  updated=json.loads(h.stdout)['hookSpecificOutput']['updatedInput']; return run(shlex.split(updated['command']),self.repo,env=self.env)
 def implemented(self):
  return self.decode(self.report('developer','IMPLEMENTED',root_cause_or_requirement='Return the approved fixture behavior',ac_mapping={'AC-01':{'implementation':['app/Example.php:1'],'tests':['fixture assertion']}}))
 def checked(self,role='tester',name='pass'): return self.decode(self.broker(role,{'action':'run_check','name':name}),0 if name not in ['fail','timeout','mutate'] else 2)
 def submit_test_report(self,check,status='PASS'):
  return self.report('tester',status,ac_results=[{'id':'AC-01','status':'PASS','assertion':'Controlled fixture assertion','check_id':check}])
 def complete(self):
  self.ready(); self.implemented(); self.decode(self.report('peer-reviewer','PASS')); check=self.checked(); self.decode(self.submit_test_report(check['id'])); return check
 def validate(self,text):
  (self.repo/'docs/prd/T-1.md').write_text(text); return self.decode(self.php("CES\\output(CES\\validatePrd('docs/prd/T-1.md'));"))
 def mock(self,provider='github',**settings):
  self.state=self.outer/'mock.json'; self.state.write_text(json.dumps({'provider':provider,'sha':'a'*40,**settings})); binpath=self.outer/'bin'; binpath.mkdir(exist_ok=True)
  for name in ['gh','glab']:
   target=binpath/name; shutil.copyfile(P/'scripts/claude/tests/fixtures/mock_provider.py',target); target.chmod(0o755)
  self.env['PATH']=str(binpath)+os.pathsep+self.env['PATH']; self.env['CES_MOCK_STATE']=str(self.state)
  self.url='https://github.test/org/repo/pull/7' if provider=='github' else 'https://gitlab.test/group/project/-/merge_requests/7'
 def payload(self,**extra):
  return {'mr_url':self.url,'reviewed_head_sha':'a'*40,'review_status':'FAIL','review_summary':'Controlled review result','comments':[{'id':'PEER-001','severity':'BLOCKING','path':'app/Test.php','line':1,'side':'RIGHT','problem':'Controlled evidenced defect','impact':'Incorrect fixture outcome','evidence':'Fixture reproduction','recommended_direction':'Correct the fixture boundary'}],**extra}
 def publish(self,payload=None,dry=False):
  args=[PHP,'scripts/claude/mr/publish-review.php']+(['--dry-run'] if dry else [])
  return run(args,self.repo,payload or self.payload(),self.env)
 def state_value(self): return json.loads(self.state.read_text())

class GuardTests(Fixture):
 def test_shell_bypass_variants_denied(self):
  for role,cmd in [('peer-reviewer',"php -r 'file_put_contents(\"bad\",\"x\");'"),('peer-reviewer','git -C . reset --hard'),('mr-review-publisher','php scripts/claude/mr/publish-review.php --dry-run; echo injected'),('tester',self.command({'action':'context'})+'\nrm -rf x'),('developer','echo safe > .claude/rules/x.md')]:
   with self.subTest(role=role,cmd=cmd): self.assertEqual(self.hook(role,'Bash',{'command':cmd}).returncode,2)
 def test_unknown_role_untouched(self): self.assertEqual(self.hook('ordinary-helper','Bash',{'command':'echo untouched'}).returncode,0)
 def test_exact_envelope_preserves_fields_and_does_not_auto_allow(self):
  r=self.decode(self.hook('engineering-orchestrator','Bash',{'command':self.command({'action':'context','kind':'head'}),'timeout':1234,'description':'context'}))
  output=r['hookSpecificOutput']; self.assertNotIn('permissionDecision',output); self.assertEqual(output['updatedInput']['timeout'],1234); self.assertEqual(output['updatedInput']['description'],'context')
 def test_ticket_replay_denied(self):
  h=self.decode(self.hook('engineering-orchestrator','Bash',{'command':self.command({'action':'context','kind':'head'})})); cmd=shlex.split(h['hookSpecificOutput']['updatedInput']['command']); self.assertEqual(run(cmd,self.repo,env=self.env).returncode,0); self.assertEqual(run(cmd,self.repo,env=self.env).returncode,2)
 def test_configuration_change_invalidates_ticket(self):
  h=self.decode(self.hook('engineering-orchestrator','Bash',{'command':self.command({'action':'context','kind':'head'})})); self.conf['allowed_hosts']=[]; self.saveconf(); self.assertEqual(run(shlex.split(h['hookSpecificOutput']['updatedInput']['command']),self.repo,env=self.env).returncode,2)
 def test_role_spoof_and_unknown_action_rejected(self):
  for req in [{'action':'run_check','name':'pass','role':'tester'},{'action':'shell','command':'id'},{'action':'task_open','task_id':'T-1','workflow':'feature'}]:
   with self.subTest(req=req): self.assertEqual(self.broker('peer-reviewer',req).returncode,2)
 def test_readonly_roles_cannot_write(self):
  for role in ['tester','peer-reviewer','engineering-orchestrator','security-reviewer','incident-investigator']:
   with self.subTest(role=role): self.assertEqual(self.hook(role,'Write',{'file_path':'app/Test.php','content':'x'}).returncode,2)
 def test_governance_and_outside_paths_denied(self):
  self.ready()
  for path in ['.claude/rules/x.md','scripts/claude/hooks/pre-tool.php','docs/prd/T-1.md','CLAUDE.md','README.md','.gitignore','.env','../outside.php',str(self.outer/'outside.php')]:
   with self.subTest(path=path): self.assertEqual(self.hook('developer','Write',{'file_path':path}).returncode,2)
 def test_scoped_document_and_developer_writes(self):
  self.assertEqual(self.hook('product-manager','Write',{'file_path':'docs/prd/New.md'}).returncode,0); self.assertEqual(self.hook('product-manager','Write',{'file_path':'docs/prd/x.php'}).returncode,2)
  self.assertEqual(self.hook('architect','Write',{'file_path':'docs/adr/Decision.md'}).returncode,0); self.assertEqual(self.hook('architect','Write',{'file_path':'docs/prd/New.md'}).returncode,2)
  self.ready(); self.assertEqual(self.hook('developer','Edit',{'file_path':'app/New.php'}).returncode,0)
 def test_symlink_and_hardlink_write_denied(self):
  self.ready(); target=self.outer/'outside'; target.mkdir(); (self.repo/'linked').symlink_to(target,target_is_directory=True); self.assertEqual(self.hook('developer','Write',{'file_path':'linked/x.php'}).returncode,2)
  (self.repo/'real.php').write_text('safe'); os.link(self.repo/'real.php',self.repo/'linked.php'); self.assertEqual(self.hook('developer','Write',{'file_path':'linked.php'}).returncode,2)
 def test_secret_path_read_denied(self):
  for path in ['.env','nested/.env.production','credentials.json','../other']:
   with self.subTest(path=path): self.assertEqual(self.hook('tester','Read',{'file_path':path}).returncode,2)
 def session_output(self,session,name='big.txt',slug='-project-slug',sub='tool-results'):
  """Build a Claude Code persisted-tool-output path under a fake HOME."""
  home=self.outer/'fakehome'; d=home/'.claude/projects'/slug/session/sub; d.mkdir(parents=True,exist_ok=True)
  f=d/name; f.write_text('persisted broker output'); self.env['HOME']=str(home); return f
 def test_own_persisted_tool_output_is_readable(self):
  """Claude Code persists oversized tool output outside the repo and reads it back."""
  f=self.session_output(self.session)
  self.assertEqual(self.hook('engineering-orchestrator','Read',{'file_path':str(f)}).returncode,0)
  self.assertEqual(self.hook('peer-reviewer','Read',{'file_path':str(f)}).returncode,0)
 def test_other_sessions_and_sibling_paths_still_denied(self):
  self.session_output(self.session)
  for path,label in [
    (self.session_output('another-session-id'),'another session'),
    (self.session_output(self.session,sub='subagents'),'non tool-results sibling'),
    (self.outer/'fakehome/.claude/projects/-project-slug'/self.session,'the session directory itself'),
    (self.outer/'fakehome/.ssh/id_rsa','a home secret'),
  ]:
   with self.subTest(label=label):
    p=Path(str(path))
    if not p.exists():
     p.parent.mkdir(parents=True,exist_ok=True); p.write_text('x')
    self.assertEqual(self.hook('tester','Read',{'file_path':str(p)}).returncode,2,label)
 def test_persisted_output_symlink_cannot_escape(self):
  f=self.session_output(self.session)
  secret=self.outer/'fakehome/.ssh/id_rsa'; secret.parent.mkdir(parents=True,exist_ok=True); secret.write_text('KEY')
  link=f.parent/'escape.txt'; link.symlink_to(secret)
  self.assertEqual(self.hook('tester','Read',{'file_path':str(link)}).returncode,2)
 def test_signoz_allowlist_and_mutations(self):
  read='mcp__signoz__signoz_search_logs'; write='mcp__signoz__signoz_create_alert'; self.assertEqual(self.hook('tester',read,{}).returncode,2)
  self.conf['signoz_read_tools']=[read,write]; self.saveconf(); self.assertEqual(self.hook('tester',read,{}).returncode,0); self.assertEqual(self.hook('tester',write,{}).returncode,2)
 def test_nested_agent_denied(self):
  r=self.hook('tester','Agent',{'subagent_type':'developer'}); self.assertEqual(r.returncode,2); self.assertIn('CES roles do not delegate',r.stderr)
 def test_generic_helper_agent_denied_with_its_own_message(self):
  self.open()
  for helper in ['Explore','general-purpose','Plan','claude']:
   with self.subTest(helper=helper):
    r=self.hook('engineering-orchestrator','Agent',{'subagent_type':helper}); self.assertEqual(r.returncode,2)
    self.assertIn('Generic helper agents are not part of the role contract',r.stderr); self.assertNotIn('only the main orchestrator does',r.stderr)
  self.assertEqual(self.hook('engineering-orchestrator','Agent',{'subagent_type':'peer-reviewer'}).returncode,0)
 def test_pretask_specialist_delegation_denied_with_actionable_message(self):
  r=self.hook('engineering-orchestrator','Agent',{'subagent_type':'peer-reviewer'}); self.assertEqual(r.returncode,2); self.assertIn('Pre-task MR/config preflight',r.stderr)
 def test_developer_delegation_requires_product_gate(self):
  self.open(); self.assertEqual(self.hook('engineering-orchestrator','Agent',{'subagent_type':'developer'}).returncode,2)
 def self_check(self): return run([PHP,'scripts/claude/checks/self-check.php'],self.repo,env=self.env)
 def test_self_check_baseline_passes_and_reports_unreachable_telemetry(self):
  r=self.self_check(); self.assertEqual(r.returncode,0,r.stdout); d=json.loads(r.stdout); self.assertEqual(d['errors'],[])
  self.assertTrue(any('incident-investigator' in w and 'SigNoz' in w for w in d['warnings']),d['warnings'])
 def test_self_check_rejects_prompt_demonstrating_a_denied_broker_action(self):
  p=self.repo/'.claude/agents/security-reviewer.md'; p.write_text(p.read_text()+"\n```bash\nphp scripts/claude/bin/ces.php <<'CES_REQUEST'\n{\"action\":\"run_check\",\"name\":\"unit\"}\nCES_REQUEST\n```\n")
  r=self.self_check(); self.assertEqual(r.returncode,2); self.assertIn("security-reviewer demonstrates broker action 'run_check'",r.stdout)
 def test_self_check_binds_frontmatter_mcp_tools_to_the_human_allowlist(self):
  p=self.repo/'.claude/agents/qa-support.md'; original=p.read_text(); self.assertIn('tools: Read, Grep, Glob, Bash\n',original)
  p.write_text(original.replace('tools: Read, Grep, Glob, Bash\n','tools: Read, Grep, Glob, Bash, mcp__signoz__signoz_search_logs\n',1))
  r=self.self_check(); self.assertEqual(r.returncode,2); self.assertIn('not allowlisted in config signoz_read_tools',r.stdout)
  self.conf['signoz_read_tools']=['mcp__signoz__signoz_search_logs']; self.saveconf(); self.assertEqual(self.self_check().returncode,0)
  p.write_text(original.replace('tools: Read, Grep, Glob, Bash\n','tools: Read, Grep, Glob, Bash, mcp__signoz__*\n',1)); r=self.self_check(); self.assertEqual(r.returncode,0,r.stdout)
  self.assertFalse(any('qa-support may use SigNoz' in w for w in json.loads(r.stdout)['warnings']))
  p.write_text(original.replace('tools: Read, Grep, Glob, Bash\n','tools: Read, Grep, Glob, Bash, mcp__other__query\n',1)); r=self.self_check(); self.assertEqual(r.returncode,2); self.assertIn('only SigNoz read tools',r.stdout)
 def test_disabled_checks_fail_closed(self):
  self.open(); self.conf['execution_isolated']=False; self.saveconf(); self.assertEqual(self.broker('tester',{'action':'run_check','name':'pass'}).returncode,2)
 def test_broker_rejects_direct_cli(self): self.assertEqual(run([PHP,'scripts/claude/bin/ces.php'],self.repo,env=self.env).returncode,2)

class PrdTests(Fixture):
 def test_valid_prd(self): self.assertEqual(self.validate(valid_prd())['status'],'PASS')
 def test_draft_with_readiness_word_rejected(self): self.assertEqual(self.validate(valid_prd().replace('Status: READY_FOR_ENGINEERING','Status: DRAFT')+'\nREADY_FOR_ENGINEERING\n')['status'],'FAIL')
 def test_empty_sections_rejected(self): self.assertEqual(self.validate(valid_prd().replace('Concrete fixture content for Goals.',''))['status'],'FAIL')
 def test_ac_outside_section_rejected(self): self.assertEqual(self.validate(valid_prd().replace('## Acceptance Criteria','## Something Else'))['status'],'FAIL')
 def test_ac_fields_all_required(self):
  for field in ['Given','When','Then','Verification','Requirement']:
   with self.subTest(field=field): self.assertEqual(self.validate('\n'.join(x for x in valid_prd().splitlines() if not x.startswith(field+':')))['status'],'FAIL')
 def test_duplicate_status_rejected(self): self.assertEqual(self.validate(valid_prd()+'\nStatus: READY_FOR_ENGINEERING\n')['status'],'FAIL')
 def test_duplicate_ac_rejected(self): self.assertEqual(self.validate(valid_prd().replace('## Failure / Negative Behavior','### AC-01\nGiven: x\nWhen: x\nThen: x\nVerification: x\nRequirement: FR-01\n\n## Failure / Negative Behavior'))['status'],'FAIL')
 def test_orphan_fr_rejected(self): self.assertEqual(self.validate(valid_prd().replace('- FR-01:', '- FR-02: Second requirement.\n- FR-01:'))['status'],'FAIL')
 def test_unknown_fr_reference_rejected(self): self.assertEqual(self.validate(valid_prd().replace('Requirement: FR-01','Requirement: FR-99'))['status'],'FAIL')
 def test_unresolved_question_rejected(self): self.assertEqual(self.validate(valid_prd().replace('## Open Questions\nNone','## Open Questions\nWho owns this?'))['status'],'FAIL')
 def test_fenced_example_cannot_satisfy_readiness(self): self.assertEqual(self.validate('```markdown\n'+valid_prd()+'\n```\n')['status'],'FAIL')
 def test_placeholders_rejected(self): self.assertEqual(self.validate(valid_prd().replace('Owner: Test fixture','Owner: TODO'))['status'],'FAIL')

FA_EXPORT="""<h1>محدودیت نرخ درخواست</h1>
<h2>‏شرح مسئله</h2><p>یک تنانت می‌تواند سرویس را اشباع کند، با ۴۲۰۰۰ درخواست.</p>
<h2>زمینه و شواهد</h2><p>لاگ های پروداکشن.</p>
<h2>اهداف</h2><p>اعمال محدودیت.</p>
<h2>غیر اهداف</h2><p>محدودیت به ازای کاربر.</p>
<h2>کاربران و نقش ها</h2><p>یکپارچه سازی های API.</p>
<h2>نیازمندی‌های عملکردی</h2>
<ul><li>FR-۰۱: درخواست زیر سقف پاسخ می‌گیرد.</li>
<li>FR-۰۲: درخواست بیش از سقف رد می‌شود.</li></ul>
<h2>معیارهای پذیرش</h2>
<h3>AC-۰۱: پاسخ عادی</h3>
<p>‏فرض: تنانتی با سقف ۵ درخواست
در دقیقه</p>
<p>وقتی:&nbsp;درخواست دیگری می‌رسد</p>
<p>آنگاه: پاسخ ۲۰۱ است</p>
<p>تایید: tests/Feature/LimitTest.php - it_allows_under_limit</p>
<p>نیازمندی: FR-۰۱</p>
<h3>AC-۰۲: رد درخواست</h3>
<p>فرض: سقف تمام شده است</p>
<p>وقتی: درخواست دیگری می‌رسد</p>
<p>آنگاه: پاسخ ۴۲۹ است</p>
<p>الزام: FR-۰۲</p>
<h2>رفتار خطا</h2><p>بدون احراز هویت رد می‌شود.</p>
<h2>نیازمندی‌های غیرعملکردی</h2><p>یک رفت و برگشت.</p>
<h2>پایش</h2><p>فیلد tenant_id.</p>
<h2>وابستگی‌ها</h2><p>از composer.lock خوانده شود.</p>
<h2>برنامه انتشار</h2><p>ابتدا با سقف بالا.</p>
<h2>معیارهای موفقیت</h2><p>عبور نکردن از سقف.</p>
<h2>ریسک‌ها</h2><p>سقف پایین.</p>
<h2>یادداشت جلسه</h2><p>جایی در قالب PRD ندارد.</p>
<h2>خارج از محدوده</h2><p>نمایش سهمیه.</p>
"""

CONFLUENCE_EXPORT="""<h1>API Management برای پارتنرها</h1>
<h2>1. Executive Summary</h2><p>هدف این محصول، در دسترس قرار دادن API است.</p>
<h2>2. Market Requirements Document (MRD)</h2>
<h3>2.1 Customer Needs &amp; Insights</h3><ul><li>نیاز به درگیر شدن سرمایه</li><li>محدودیت انبارداری</li></ul>
<h3>2.2 Competitors</h3><ul><li>همراه تل</li><li>نامی نت</li></ul>
<h2>3. Business Goals</h2><ul><li>رشد فروش از طریق پارتنرشیپ</li></ul>
<h2>4. Product Requirements (PRD)</h2>
<h3>4.1 Personas</h3><ul><li>شرکت ها و فروشندگان B2B</li></ul>
<h3>4.2 Functional Requirements</h3>
<p><strong>Configs and Settings</strong></p><ul><li>امکان روشن کردن تاگل برای مشتریان</li><li>امکان مشخص کردن انبار برای هر مشتری</li></ul>
<p><strong>Place Order</strong></p><ul><li>ثبت سفارش مستقیم بر اساس اطلاعات محصول</li></ul>
<h3>4.3 Acceptance Criteria</h3>
<table><tbody><tr><th>سناریو</th><th>فرض</th><th>وقتی</th><th>آنگاه</th><th>تایید</th></tr>
<tr><td>تاگل روشن</td><td>مشتری با تاگل روشن</td><td>پروفایل باز می‌شود</td><td>API Management نمایش داده می‌شود</td><td>tests/Feature/ProfileTest.php - it_shows_api_management</td></tr>
<tr><td>ثبت سفارش بدون موجودی</td><td>کالا موجودی ندارد</td><td>سفارش ثبت می‌شود</td><td>خطای ۴۲۲ با کد OUT_OF_STOCK</td><td></td></tr></tbody></table>
<h3>4.4 NFRs</h3><ul><li>P95 latency &lt; 500ms</li></ul>
<h2>5. Timeline &amp; Milestones</h2>
<table><tbody><tr><td><p>Milestone</p></td><td><p>Duration</p></td><td><p>Responsible</p></td></tr><tr><td><p>Auth &amp; Token</p></td><td><p>10 days</p></td><td><p>Backend</p></td></tr></tbody></table>
<h2>6. اینتگریشن ایرانسل</h2>
<h2>7. Success Metrics</h2><ul><li>حداقل 2 پارتنر</li></ul>
<h2>8. Risks &amp; Mitigation Strategies</h2>
<table><tbody><tr><td>Risk</td><td>Mitigation</td></tr><tr><td>Overselling</td><td>Validation لحظه‌ای موجودی</td></tr></tbody></table>
"""

CROSS_EXPORT="""<h1>Cross-selling</h1>
<table><tbody><tr><th>نگارنده</th><td>تینا کهریزی</td></tr><tr><th>وضعیت</th><td><ac:structured-macro ac:name="status"><ac:parameter ac:name="colour">Green</ac:parameter><ac:parameter ac:name="title">COMPLETED</ac:parameter></ac:structured-macro></td></tr><tr><th>لینک</th><td><ac:link><ri:page ri:content-title="Algo"/><ac:plain-text-link-body><![CDATA[جزئیات الگوریتم]]></ac:plain-text-link-body></ac:link></td></tr></tbody></table>
<h2>1 لیست ذینفعان مرتبط (Stack holders)</h2><table><tbody><tr><th>نام</th><th>تیم</th></tr><tr><td>امیرحسین قاسمی</td><td>گروث</td></tr></tbody></table>
<h2>2 توصیف مساله (Problem Definition)</h2><ul><li>در حال حاضر فروش الکترونیک وابستگی بالایی به کتگوری موبایل دارد.</li></ul>
<h2>3 داده‌های پشتیبان (Supportive Data)</h2><ul><li>سهم موبایل از فروش: ٪۷۷</li></ul><table><tbody><tr><th>Category Mix</th><th>AOV</th></tr><tr><td>MO+AC</td><td>6,751,291,498</td></tr></tbody></table>
<h2>4 متریک ها و اهداف (Metrics &amp; Goals)</h2><ul><li>هدف اصلی این initiative افزایش نرخ attachment است.</li></ul>
<h2>5 راه حل های پیشنهادی (Suggested Solution)</h2><h3>5.4 راه حل نهایی (Final Solution)</h3><p>راه حل نهایی فاز اول، پیاده‌سازی <strong>Cart Inline Recommender</strong> است.</p>
<h2>6 طراحی اولیه و فلو کاربر (User Flow and Prototype)</h2><ul><li>کاربر وارد Cart میشود.</li></ul>
<h3>6.1 User Stories</h3><p><strong>فاز اول:</strong></p><p>1- به عنوان کاربر می خواهم با ورود به صفحه کارت، ریکامندور اکسسوری را مشاهده کنم.</p>
<ul><li>در صورتی که کاربر وارد صفحه کارت شد کروسل نمایش داده می شود.<ul><li>موبایل</li><li>هدفون</li></ul></li><li>در این کروسل حداقل 4 محصول و حداکثر 16 محصول نمایش داده می شود.</li></ul>
<h3>6.2 Rule های الگوریتم:</h3><h3>6.3 ورودیهای اصلی سیستم</h3><p>برای تولید کروسل، سیستم باید ورودیهای زیر را دریافت یا محاسبه کند:</p><h4>6.3.1 برند کالای اصلی</h4><ul><li>سامسونگ</li></ul>
<h2>8 رودمپ و ایتریشن ها (Roadmap and Iteration)</h2><h3>Phase 1: Cart Recommender</h3><p>پیاده‌سازی recommender در صفحه Cart.</p>
<h2>9 محدودیتها و ریسکها (Constraints and Risks)</h2><h3>9.1 ریسک افزایش friction در funnel</h3><p>هرگونه touchpoint مزاحم میتواند ریسک ریزش را بیشتر کند.</p>
<h2>10 توضیحات فنی (Technical Requirements)</h2><h3>10.1 نیازمندیهای تکنیکال اولیه</h3><ul><li>تشخیص وجود کالای MO و AC در cart</li></ul><h3>10.2 Eventهای پیشنهادی</h3><ul><li>لاگ نمایش recommender ها cart-recommender-attachment-view</li></ul>
<h2>11 نیازمندی ها از سایر تیمها ( Requirements from Other teams)</h2><table><tbody><tr><th>نیازمندی</th><th>ددلاین</th></tr><tr><td>تعریف Must DKPC ها</td><td>done</td></tr></tbody></table>
<h2>12 سوالات پرتکرار (FAQ)</h2><h3>12.1 چرا؟</h3><p>هدف از نمایش Recommender افزایش فروش اکسسوری است.</p>
<h2>13 تاییدکنندگان (Approvers)</h2><table><tbody><tr><th>نام</th><th>وضعیت</th></tr><tr><td>یوسف محمدجانی</td><td>بررسی نشده</td></tr></tbody></table>
"""

class PrdImportTests(Fixture):
 def importer(self,*args):
  return run([PHP,'scripts/claude/tools/import-prd.php',*args],self.repo,env=self.env)
 def imported(self,source=None,*args):
  (self.repo/'export.xhtml').write_text(source or FA_EXPORT)
  r=self.importer('--in=export.xhtml','--id=FA-1','--owner=مالک واقعی',*args)
  self.assertEqual(r.returncode,0,r.stderr); return r.stdout,json.loads(r.stderr)
 def test_persian_headings_map_to_canonical_sections(self):
  out,report=self.imported()
  for section in PRD_SECTIONS: self.assertIn('## '+section+'\n',out)
  self.assertEqual(report['functional_requirements'],2); self.assertEqual(report['acceptance_criteria'],2)
  self.assertEqual([u['heading'] for u in report['unmapped_headings']],['یادداشت جلسه'])
 def test_identifiers_become_ascii_but_body_digits_stay_persian(self):
  out,report=self.imported()
  self.assertIn('- FR-01:',out); self.assertIn('- FR-02:',out); self.assertIn('### AC-01:',out)
  self.assertNotIn('FR-۰۱',out); self.assertIn('پاسخ ۲۰۱ است',out)
  self.assertGreater(report['normalized']['persian_digits_folded'],0)
 def test_persian_labels_become_ascii_given_when_then(self):
  out,unused=self.imported()
  for label in ['Given:','When:','Then:','Verification:','Requirement: FR-01']: self.assertIn(label,out)
 def test_wrapped_label_value_is_joined_into_one_line(self):
  out,report=self.imported()
  self.assertGreaterEqual(report['normalized']['label_lines_joined'],1)
  self.assertIn('در دقیقه',[l for l in out.splitlines() if l.startswith('Given:')][0])
 def test_import_can_never_claim_readiness(self):
  out,unused=self.imported(FA_EXPORT+'<p>Status: READY_FOR_ENGINEERING</p>')
  self.assertEqual([l for l in out.splitlines() if l.startswith('Status:')],['Status: DRAFT'])
 def test_imported_draft_fails_until_a_human_completes_it(self):
  out,report=self.imported()
  self.assertIn('AC-02: the source states no Verification value. The accountable human must supply it; do not infer one.',report['unresolved'])
  first=self.validate(out)
  self.assertEqual(first['status'],'FAIL'); self.assertIn('AC-02 requires non-empty Verification:',first['errors'])
  completed=out.replace('Status: DRAFT','Status: READY_FOR_ENGINEERING').replace('Requirement: FR-02','Verification: tests/Feature/LimitTest.php - it_rejects_over_limit\nRequirement: FR-02')
  completed=re.sub(r'## Open Questions\n.*?\n\n## Out of Scope','## Open Questions\nNone\n\n## Out of Scope',completed,flags=re.S)
  self.assertIn('## Unmapped Source Sections',completed); self.assertIn('Unmapped Source Sections is still present: imported content has not been categorised into the canonical sections.',self.validate(completed)['errors'])
  completed=re.sub(r'\n## Unmapped Source Sections\n.*\Z','\n',completed,flags=re.S)
  second=self.validate(completed)
  self.assertEqual(second['status'],'PASS',second['errors']); self.assertEqual(second['ac_ids'],['AC-01','AC-02'])
 def test_out_refuses_paths_outside_product_documents(self):
  (self.repo/'export.xhtml').write_text(FA_EXPORT)
  for target in ['app/Imported.md','.claude/agents/x.md','docs/prd/../../escape.md','docs/prd/FA-1.txt']:
   with self.subTest(target=target): self.assertEqual(self.importer('--in=export.xhtml','--id=FA-1','--out='+target).returncode,2)
 def test_out_writes_under_docs_prd(self):
  (self.repo/'export.xhtml').write_text(FA_EXPORT)
  r=self.importer('--in=export.xhtml','--id=FA-1','--out=docs/prd/FA-1.md')
  self.assertEqual(r.returncode,0,r.stderr); self.assertIn('## Acceptance Criteria',(self.repo/'docs/prd/FA-1.md').read_text())
 def test_invalid_input_is_rejected(self):
  (self.repo/'export.xhtml').write_text(FA_EXPORT); (self.repo/'bad.xhtml').write_bytes(b'\xff\xfe not utf8')
  self.assertEqual(self.importer('--in=bad.xhtml','--id=FA-1').returncode,2)
  self.assertEqual(self.importer('--in=missing.xhtml','--id=FA-1').returncode,2)
  self.assertEqual(self.importer('--in=export.xhtml','--id=../escape').returncode,2)
  self.assertEqual(self.importer('--in=export.xhtml').returncode,2)
 def test_print_map_exposes_every_canonical_section(self):
  r=self.importer('--print-map'); self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual(sorted(json.loads(r.stdout)['sections'].keys()),sorted(PRD_SECTIONS))
 def test_confluence_shape_numbered_headings_tables_and_container_chapters(self):
  out,report=self.imported(CONFLUENCE_EXPORT)
  self.assertTrue(out.startswith('# FA-1 - API Management برای پارتنرها\n'),out.splitlines()[0])
  self.assertEqual(report['title'],'API Management برای پارتنرها')
  self.assertIn('| Milestone | Duration | Responsible |\n|---|---|---|\n| Auth & Token | 10 days | Backend |',out)
  self.assertIn('| Risk | Mitigation |\n|---|---|\n| Overselling | Validation لحظه‌ای موجودی |',out)
  self.assertNotIn('**4. Product Requirements (PRD)**',out); self.assertNotIn('**6. اینتگریشن ایرانسل**',out)
  for empty in ['4. Product Requirements (PRD)','6. اینتگریشن ایرانسل']:
   self.assertIn("Source section '"+empty+"' is empty in the source - it has a heading and no content, so nothing was imported from it. Confirm with the accountable human whether it was left unwritten.",report['unresolved'])
  self.assertIn('**2.2 Competitors**\n- همراه تل\n- نامی نت',out)
  self.assertEqual(sorted(u['heading'] for u in report['unmapped_headings']),sorted(['1. Executive Summary','2. Market Requirements Document (MRD)','2.1 Customer Needs & Insights','2.2 Competitors','4. Product Requirements (PRD)','6. اینتگریشن ایرانسل']))
  # "Executive Summary" and "MRD" name whole chapters, not one canonical section, so they are handed to the
  # product-manager verbatim rather than filed under Problem Statement and Context / Evidence by guesswork.
  self.assertEqual(report['unmapped_sections_kept'],['1. Executive Summary','2. Market Requirements Document (MRD)'])
  self.assertIn('**Configs and Settings**\n- FR-01: امکان روشن کردن تاگل برای مشتریان\n- FR-02: امکان مشخص کردن انبار برای هر مشتری\n\n**Place Order**\n- FR-03:',out)
  self.assertIn('P95 latency < 500ms',out)
 def test_persian_acceptance_table_becomes_ac_blocks_without_inventing_fields(self):
  out,report=self.imported(CONFLUENCE_EXPORT)
  self.assertEqual(report['acceptance_criteria'],2)
  self.assertIn('### AC-01: تاگل روشن\nGiven: مشتری با تاگل روشن\nWhen: پروفایل باز می‌شود\nThen: API Management نمایش داده می‌شود\nVerification: tests/Feature/ProfileTest.php - it_shows_api_management\n',out)
  self.assertIn('### AC-02: ثبت سفارش بدون موجودی\nGiven: کالا موجودی ندارد\nWhen: سفارش ثبت می‌شود\nThen: خطای ۴۲۲ با کد OUT_OF_STOCK\n\n',out)
  self.assertIn('AC-02: the source states no Verification value. The accountable human must supply it; do not infer one.',report['unresolved'])
  self.assertTrue(any(u.startswith("Section 'Non-Goals' is empty in the source") for u in report['unresolved']),report['unresolved'])
  self.assertTrue(all('product-manager must' not in u for u in report['unresolved']),report['unresolved'])
 def test_requirements_table_takes_the_requirement_column(self):
  src='<h1>T</h1><h2>Problem</h2><p>x</p><h2>Functional Requirements</h2><table><tr><th>ID</th><th>شرح نیازمندی</th><th>Priority</th></tr><tr><td>FR-۰۵</td><td>دریافت لیست کالاها</td><td>High</td></tr><tr><td>FR-۰۶</td><td>دریافت ورینت ها</td><td>Low</td></tr></table><h2>Acceptance Criteria</h2><h3>AC-1</h3><p>Given: a</p><p>When: b</p><p>Then: c</p><p>Verification: d</p><p>Requirement: FR-۰۶</p>'
  out,report=self.imported(src)
  self.assertIn('- FR-01: دریافت لیست کالاها\n- FR-02: دریافت ورینت ها\n',out); self.assertNotIn('High',out.split('## Functional Requirements')[1].split('## Acceptance')[0])
  self.assertIn('Requirement: FR-02',out); self.assertEqual(report['functional_requirements'],2)
 def test_bilingual_numbered_headings_map_and_unknown_sections_are_kept_not_misfiled(self):
  out,report=self.imported(CROSS_EXPORT)
  self.assertTrue(out.startswith('# FA-1 - Cross-selling\n'))
  by={m['heading']:m['section'] for m in report['heading_matches']}
  self.assertEqual(by['2 توصیف مساله (Problem Definition)'],'Problem Statement'); self.assertEqual(by['3 داده\u200cهای پشتیبان (Supportive Data)'],'Context / Evidence')
  self.assertEqual(by['6.1 User Stories'],'Functional Requirements')
  # A chapter that names two canonical sections is never filed under one of them by the alias table.
  self.assertNotIn('4 متریک ها و اهداف (Metrics & Goals)',by); self.assertIn('4 متریک ها و اهداف (Metrics & Goals)',report['unmapped_sections_kept'])
  self.assertEqual(by['8 رودمپ و ایتریشن ها (Roadmap and Iteration)'],'Rollout / Migration Expectations'); self.assertEqual(by['9 محدودیتها و ریسکها (Constraints and Risks)'],'Risks')
  self.assertEqual(by['10.2 Eventهای پیشنهادی'],'Observability Requirements'); self.assertEqual(by['11 نیازمندی ها از سایر تیمها ( Requirements from Other teams)'],'Dependencies')
  section=lambda name: out.split('## '+name+'\n',1)[1].split('\n## ',1)[0]
  self.assertIn('| Category Mix | AOV |',section('Context / Evidence')); self.assertIn('cart-recommender-attachment-view',section('Observability Requirements'))
  self.assertIn('| تعریف Must DKPC ها | done |',section('Dependencies')); self.assertIn('**Phase 1: Cart Recommender**\nپیاده‌سازی recommender در صفحه Cart.',section('Rollout / Migration Expectations'))
  self.assertNotIn('Recommender افزایش فروش',section('Risks')); self.assertEqual(section('Goals').strip(),'')
  kept=section('Unmapped Source Sections')
  for heading in ['(document preamble)','1 لیست ذینفعان مرتبط (Stack holders)','4 متریک ها و اهداف (Metrics & Goals)','5 راه حل های پیشنهادی (Suggested Solution)','6 طراحی اولیه و فلو کاربر (User Flow and Prototype)','6.3 ورودیهای اصلی سیستم','10 توضیحات فنی (Technical Requirements)','12 سوالات پرتکرار (FAQ)','13 تاییدکنندگان (Approvers)']:
   self.assertIn('**'+heading+'**',kept,heading); self.assertIn(heading,report['unmapped_sections_kept'])
  self.assertIn('| وضعیت | COMPLETED |',kept); self.assertIn('جزئیات الگوریتم',kept); self.assertIn('| یوسف محمدجانی | بررسی نشده |',kept)
  self.assertIn('Cart Inline Recommender',kept); self.assertIn('کاربر وارد Cart میشود.',kept); self.assertIn('تشخیص وجود کالای MO و AC در cart',kept)
  self.assertNotIn('6.2 Rule های الگوریتم:',kept)
  self.assertEqual([u['kept_as'] for u in report['unmapped_headings'] if u['heading']=='6.2 Rule های الگوریتم:'],['empty in the source; nothing was imported from it'])
  self.assertTrue(any(u.startswith("Source section '13 تاییدکنندگان (Approvers)' was not recognised") for u in report['unresolved']))
  self.assertIn('Unmapped Source Sections is still present: imported content has not been categorised into the canonical sections.',self.validate(out)['errors'])
 def test_user_stories_become_requirements_and_sub_bullets_stay_under_their_parent(self):
  out,report=self.imported(CROSS_EXPORT)
  fr=out.split('## Functional Requirements\n',1)[1].split('\n## ',1)[0]
  self.assertEqual(report['functional_requirements'],3)
  self.assertEqual(fr.strip(),'**فاز اول:**\n- FR-01: به عنوان کاربر می خواهم با ورود به صفحه کارت، ریکامندور اکسسوری را مشاهده کنم.\n- FR-02: در صورتی که کاربر وارد صفحه کارت شد کروسل نمایش داده می شود.\n  - موبایل\n  - هدفون\n- FR-03: در این کروسل حداقل 4 محصول و حداکثر 16 محصول نمایش داده می شود.')
  self.assertEqual(self.validate(out.replace('Status: DRAFT','Status: READY_FOR_ENGINEERING'))['requirements'],{'FR-01':'به عنوان کاربر می خواهم با ورود به صفحه کارت، ریکامندور اکسسوری را مشاهده کنم.','FR-02':'در صورتی که کاربر وارد صفحه کارت شد کروسل نمایش داده می شود.','FR-03':'در این کروسل حداقل 4 محصول و حداکثر 16 محصول نمایش داده می شود.'})
 def test_pdf_export_is_refused_with_guidance(self):
  (self.repo/'export.pdf').write_bytes(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj<<>>endobj\n')
  r=self.importer('--in=export.pdf','--id=FA-1'); self.assertEqual(r.returncode,2); self.assertIn('PDF',r.stderr); self.assertIn('.docx',r.stderr)
 def confluence(self,**state):
  self.state_c=self.outer/'confluence.json'; self.state_c.write_text(json.dumps({'pages':{'180753756':{'title':'Cross-selling','storage':CROSS_EXPORT.split('\n',1)[1],'version':10,'space':'B2BTP'}},**state}))
  binpath=self.outer/'cbin'; binpath.mkdir(exist_ok=True); target=binpath/'curl'; shutil.copyfile(P/'scripts/claude/tests/fixtures/mock_confluence.py',target); target.chmod(0o755)
  self.env['PATH']=str(binpath)+os.pathsep+self.env['PATH']; self.env['CES_CONFLUENCE_MOCK']=str(self.state_c); self.env['CONFLUENCE_TOKEN']='s3cr3t-token'
  self.conf['confluence_hosts']=['docs.test']; self.saveconf()
  return 'https://docs.test/spaces/B2BTP/pages/180753756/Cross-selling'
 def test_confluence_url_import_fetches_storage_format_and_hides_the_token(self):
  url=self.confluence(); r=self.importer('--url='+url,'--id=CROSS-1','--save-source=docs/prd/sources/CROSS-1.xhtml')
  self.assertEqual(r.returncode,0,r.stderr); report=json.loads(r.stderr)
  self.assertEqual(report['source_format'],'confluence-rest/storage'); self.assertEqual(report['confluence']['title'],'Cross-selling'); self.assertEqual(report['confluence']['version'],10); self.assertEqual(report['confluence']['saved_to'],'docs/prd/sources/CROSS-1.xhtml')
  self.assertTrue(r.stdout.startswith('# CROSS-1 - Cross-selling\n')); self.assertIn('| وضعیت | COMPLETED |',r.stdout)
  calls=json.loads(self.state_c.read_text())['calls']; self.assertEqual(len(calls),1); self.assertIn('/rest/api/content/180753756?expand=body.storage',calls[0]['url'])
  self.assertIn('header = "Authorization: Bearer s3cr3t-token"',calls[0]['header_config']); self.assertNotIn('s3cr3t',' '.join(calls[0]['argv'])); self.assertNotIn('s3cr3t',r.stdout+r.stderr)
  self.assertNotIn('-L',calls[0]['argv']); self.assertIn('=https',calls[0]['argv'])
 def test_confluence_cloud_prefix_fallback_and_failure_modes(self):
  url=self.confluence(prefix='/wiki/rest/api/content/'); r=self.importer('--url='+url,'--id=CROSS-1'); self.assertEqual(r.returncode,0,r.stderr)
  calls=json.loads(self.state_c.read_text())['calls']; self.assertEqual(len(calls),2); self.assertIn('/wiki/rest/api/content/',calls[1]['url'])
  self.confluence(deny=True); r=self.importer('--url='+url,'--id=CROSS-1'); self.assertEqual(r.returncode,2); self.assertIn('denied access (HTTP 403)',r.stderr)
  self.confluence(unreachable=True); r=self.importer('--url='+url,'--id=CROSS-1'); self.assertEqual(r.returncode,2); self.assertIn('company network',r.stderr)
  self.confluence(); r=self.importer('--url=https://other.test/spaces/X/pages/1/T','--id=CROSS-1'); self.assertEqual(r.returncode,2); self.assertIn("not allowlisted",r.stderr); self.assertEqual(json.loads(self.state_c.read_text()).get('calls',[]),[])
  r=self.importer('--url=https://docs.test/spaces/B2BTP/overview','--id=CROSS-1'); self.assertEqual(r.returncode,2); self.assertIn('page id',r.stderr)
  self.env.pop('CONFLUENCE_TOKEN'); r=self.importer('--url='+url,'--id=CROSS-1'); self.assertEqual(r.returncode,2); self.assertIn('CONFLUENCE_TOKEN',r.stderr)
  self.env['CONFLUENCE_USER']='me'; self.env['CONFLUENCE_API_TOKEN']='pw'; r=self.importer('--url='+url,'--id=CROSS-1'); self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('Authorization: Basic '+__import__('base64').b64encode(b'me:pw').decode(),json.loads(self.state_c.read_text())['calls'][-1]['header_config'])
  (self.repo/'e.xhtml').write_text(CROSS_EXPORT); self.assertEqual(self.importer('--in=e.xhtml','--url='+url,'--id=CROSS-1').returncode,2); self.assertEqual(self.importer('--id=CROSS-1').returncode,2)
 def test_sub_heading_naming_the_current_section_stays_inside_it_and_roadmap_phases_stay_in_rollout(self):
  src='<h1>Buy again</h1><h2>اهداف</h2><h3>Goal</h3><p>افزایش سهم خرید تکراری.</p><h3>Key Results</h3><table><tr><th>KR</th><th>Target</th></tr><tr><td>Repeat rate</td><td>10%</td></tr></table><h3>Guardrail Metrics</h3><ul><li>Checkout success rate ثابت بماند.</li></ul><h2>رودمپ و ایتریشن‌ها</h2><h3>Phase 1</h3><p>سکشن در PLP.</p><h3>Phase 2</h3><p>صفحه مستقل.</p><h2>Out of Scope</h2><p>Reorder کامل سفارش.</p>'
  out,report=self.imported(src)
  section=lambda name: out.split('## '+name+'\n',1)[1].split('\n## ',1)[0]
  self.assertEqual(section('Goals').strip(),'**Goal**\nافزایش سهم خرید تکراری.')
  self.assertIn('| Repeat rate | 10% |',section('Success Metrics')); self.assertIn('**Guardrail Metrics**\n- Checkout success rate ثابت بماند.',section('Success Metrics'))
  self.assertEqual(section('Rollout / Migration Expectations').strip(),'**Phase 1**\nسکشن در PLP.\n\n**Phase 2**\nصفحه مستقل.')
  self.assertEqual(section('Out of Scope').strip(),'Reorder کامل سفارش.'); self.assertNotIn('## Unmapped Source Sections',out)
  self.assertEqual([m['section'] for m in report['heading_matches']],['Goals','Goals','Success Metrics','Success Metrics','Rollout / Migration Expectations','Out of Scope'])
 def test_images_links_and_structure_only_sections_are_never_silently_dropped(self):
  src=('<h1>نمایش خریدهای قبلی</h1><h2>توصیف مسئله (Problem Definition)</h2>'
   '<p>کاربران کالای تکراری را دوباره پیدا نمی‌کنند. <ac:image ac:width="600"><ri:attachment ri:filename="chart.png"/></ac:image></p>'
   '<h2>طراحی اولیه و فلو کاربر</h2><p><ac:link><ri:page ri:content-title="Buy Again Flow"/></ac:link></p>'
   '<p><ac:image><ri:attachment ri:filename="wireframe.png"/></ac:image></p>'
   '<h3>Phase 1</h3><p><ac:image><ri:url ri:value="https://figma.com/proto/abc"/></ac:image></p><h3>Phase 2</h3>'
   '<h2>نیازمندی‌های فنی</h2><h3>Backend</h3><p>اندپوینت جدید. <ac:link><ri:attachment ri:filename="api.yaml"/><ac:plain-text-link-body><![CDATA[قرارداد API]]></ac:plain-text-link-body></ac:link></p>')
  out,report=self.imported(src)
  self.assertIn('کاربران کالای تکراری را دوباره پیدا نمی‌کنند. [image - attachment: chart.png]',out)
  kept=out.split('## Unmapped Source Sections\n',1)[1]
  self.assertIn('طراحی اولیه و فلو کاربر',report['unmapped_sections_kept'])
  for fragment in ['**طراحی اولیه و فلو کاربر**','[link - page: Buy Again Flow]','[image - attachment: wireframe.png]','**Phase 1**','[image - https://figma.com/proto/abc]','**Phase 2**','قرارداد API [link - attachment: api.yaml]']:
   self.assertIn(fragment,kept,fragment)
  self.assertNotIn('\n [image',out)
 def test_a_person_reference_says_the_export_carries_no_name(self):
  out,unused=self.imported('<h1>T</h1><h2>شرح مسئله</h2><p>نگارنده: <ac:link><ri:user ri:userkey="2c9280829c46827c"/></ac:link></p>')
  self.assertIn('نگارنده: [link - user mention - Confluence exports no display name; key 2c9280829c46827c]',out)
 def test_report_says_where_every_unrecognised_heading_went(self):
  src=('<h1>T</h1><h2>توصیف مسئله (Problem Definition)</h2><p>متن مسئله.</p><h3>جزئیات بررسی</h3><p>جزئیات.</p>'
   '<h2>راه‌حل نهایی</h2><p>راهکار.</p><h3>شرایط نمایش</h3><p>شرط.</p>'
   '<h2>طراحی اولیه و فلو کاربر</h2><p><br/></p><hr/>'
   '<h2>ریسک‌ها</h2><p>ریسک اول.</p>')
  out,report=self.imported(src)
  where={u['heading']:u['kept_as'] for u in report['unmapped_headings']}
  self.assertEqual(where['جزئیات بررسی'],'sub-heading kept inside Problem Statement')
  self.assertEqual(where['راه‌حل نهایی'],'its own entry under Unmapped Source Sections')
  self.assertEqual(where['شرایط نمایش'],'sub-heading of the unmapped source section "راه‌حل نهایی"')
  self.assertEqual(where['طراحی اولیه و فلو کاربر'],'empty in the source; nothing was imported from it')
  self.assertEqual(report['unmapped_sections_kept'],['راه‌حل نهایی'])
  self.assertIn("Source section 'طراحی اولیه و فلو کاربر' is empty in the source - it has a heading and no content, so nothing was imported from it. Confirm with the accountable human whether it was left unwritten.",report['unresolved'])
  self.assertTrue(all("Source section 'طراحی اولیه و فلو کاربر' was not recognised" not in u for u in report['unresolved']))
  self.assertIn('**جزئیات بررسی**\nجزئیات.',out); self.assertIn('**شرایط نمایش**\nشرط.',out.split('## Unmapped Source Sections')[1])
 def test_sub_headings_of_a_mapped_section_survive_even_with_an_empty_body(self):
  src=('<h1>T</h1><h2>توصیف مساله (Problem Definition)</h2><h3>دسته‌بندی مسائل اصلی</h3>'
   '<p><strong>۱. تغییر نماینده مشتریان حقوقی</strong></p><p>نماینده شرکت نقش کلیدی دارد.</p>'
   '<p><strong>۲. تغییر شماره موبایل</strong></p><p>کاربر شماره خود را از دست می‌دهد.</p>'
   '<h2>رودمپ و ایتریشن ها (Roadmap and Iteration)</h2>'
   '<h3>Iteration 1: تغییر نماینده</h3><ul><li><p><br/></p></li></ul>'
   '<h3>Iteration 2: تغییر شماره</h3><ul><li><p><br/></p></li></ul>')
  out,report=self.imported(src)
  section=lambda name: out.split('## '+name+'\n',1)[1].split('\n## ',1)[0].strip()
  self.assertEqual(section('Rollout / Migration Expectations'),'**Iteration 1: تغییر نماینده**\n**Iteration 2: تغییر شماره**')
  self.assertNotIn('Rollout / Migration Expectations',report['sections_empty'])
  self.assertTrue(all("Section 'Rollout / Migration Expectations' is empty" not in u for u in report['unresolved']))
  self.assertEqual(section('Problem Statement'),'**دسته‌بندی مسائل اصلی**\n**۱. تغییر نماینده مشتریان حقوقی**\nنماینده شرکت نقش کلیدی دارد.\n\n**۲. تغییر شماره موبایل**\nکاربر شماره خود را از دست می‌دهد.')
  where={u['heading']:u['kept_as'] for u in report['unmapped_headings']}
  self.assertEqual(where['دسته‌بندی مسائل اصلی'],'sub-heading kept inside Problem Statement')
  self.assertEqual(where['Iteration 1: تغییر نماینده'],'sub-heading kept inside Rollout / Migration Expectations')
  self.assertNotIn('## Unmapped Source Sections',out)
 def test_no_source_text_is_lost_and_only_mapped_headings_are_renamed(self):
  """The whole promise of the importer: every statement of the source survives into the draft."""
  out,report=self.imported(CROSS_EXPORT)
  renamed={h for hs in report['sections_mapped'].values() for h in hs}
  norm=lambda t: re.sub(r'\s+',' ',t).strip()
  body=re.sub(r'<!\[CDATA\[(.*?)\]\]>',r'\1',CROSS_EXPORT,flags=re.S)
  body=re.sub(r'<ac:parameter\b(?![^>]*ac:name="title")[^>]*>.*?</ac:parameter>','',body,flags=re.S|re.I)
  fragments=[f for f in (norm(html.unescape(re.sub(r'<[^>]+>',' ',c))) for c in re.split(r'(?=<)',body)) if len(f)>=12]
  self.assertGreater(len(fragments),25,'the fixture must exercise a real page')
  rendered=norm(out)
  # A source fragment may be absent only because it is a chapter heading replaced by its canonical section
  # name - and then the report must say so. Anything else is content the conversion dropped.
  unnumbered=lambda f: re.sub(r'\A\s*(?:[-*•]|[0-9\u06f0-\u06f9]{1,3}[-.)])\s*','',f)
  for fragment in fragments:
   # A numbered story keeps its text and exchanges its own "1-" for the FR-01 identifier.
   if fragment in rendered or unnumbered(fragment) in rendered: continue
   self.assertIn(fragment,renamed,'source text lost: '+fragment)
  for heading in renamed:
   self.assertIn(heading,[u for u in sum(report['sections_mapped'].values(),[])])
 def test_title_missing_is_reported_not_taken_from_a_section_heading(self):
  out,report=self.imported('<h2>شرح مسئله</h2><p>متن</p>')
  self.assertTrue(out.startswith('# FA-1 - imported product contract\n')); self.assertTrue(any(u.startswith('Title was not found') for u in report['unresolved']))

class WorkflowTests(Fixture):
 def test_no_task_blocks_check(self): self.assertEqual(self.broker('tester',{'action':'run_check','name':'pass'}).returncode,2)
 def test_pm_alone_not_enough(self):
  self.open(); self.decode(self.report('product-manager','READY_FOR_ENGINEERING',prd_path='docs/prd/T-1.md')); self.assertEqual(self.hook('developer','Write',{'file_path':'app/A.php'}).returncode,2)
 def test_changed_prd_invalidates_gate(self):
  self.ready(); f=self.repo/'docs/prd/T-1.md'; f.write_text(f.read_text()+'\nA new scope condition.\n'); self.assertEqual(self.hook('developer','Write',{'file_path':'app/A.php'}).returncode,2)
 def test_code_flows_require_prd(self):
  for flow in ['feature','production-bug','development-bug','incident','performance','security','refactor','upgrade','ci-failure']:
   with self.subTest(flow=flow): self.assertEqual(self.php("CES\\output(CES\\openTask('different-'.$x['workflow'],$x));",{'task_id':'T-1','workflow':flow}).returncode,2)
 def test_review_flow_denies_implementation(self):
  self.open('peer-review'); self.assertEqual(self.hook('developer','Write',{'file_path':'app/A.php'}).returncode,2)
 def test_mr_task_base_sha_restores_diff_scope_and_risk_gates(self):
  """On an MR checkout the local HEAD IS the reviewed head, so the default base sees nothing."""
  d=self.repo/'database/migrations'; d.mkdir(parents=True); (d/'2026_add_index.php').write_text('<?php // migration')
  self.git('add','-A'); self.git('commit','-qm','add migration')
  head=self.git('rev-parse','HEAD').stdout.strip()
  req={'task_id':'T-1','workflow':'peer-review','mr_url':'https://github.test/org/repo/pull/7','reviewed_head_sha':head}
  default=self.decode(self.php("CES\\output(CES\\openTask('sess-default',$x));",req))
  self.assertEqual(default['base_sha'],head)
  self.assertEqual(self.decode(self.php("CES\\output(['g'=>CES\\derivedRiskGates(CES\\loadTask('sess-default'))]);"))['g'],[])
  scoped=self.decode(self.php("CES\\output(CES\\openTask('sess-base',$x));",{**req,'base_sha':self.sha}))
  self.assertEqual(scoped['base_sha'],self.sha)
  self.assertIn('database-reviewer',self.decode(self.php("CES\\output(['g'=>CES\\derivedRiskGates(CES\\loadTask('sess-base'))]);"))['g'])
 def test_base_sha_is_accepted_by_the_broker_and_visible_to_every_role(self):
  h=self.hook('engineering-orchestrator','Bash',{'command':self.command({'action':'task_open','task_id':'T-1','workflow':'peer-review','mr_url':'https://github.test/org/repo/pull/7','reviewed_head_sha':self.sha,'base_sha':self.sha})})
  self.assertEqual(h.returncode,0,h.stderr)
  self.open('peer-review',mr_url='https://github.test/org/repo/pull/7',reviewed_head_sha=self.sha,base_sha=self.sha)
  # task_status is permitted to ALL roles, so a specialist without fetch_mr can still scope its diff.
  for role in ['database-reviewer','security-reviewer','performance-reviewer']:
   with self.subTest(role=role):
    self.assertEqual(self.decode(self.broker(role,{'action':'task_status'}))['task']['base_sha'],self.sha)
 def test_unusable_base_sha_rejected(self):
  for bad in ['b'*40,'not-a-sha','']:
   with self.subTest(base=bad):
    self.assertEqual(self.php("CES\\output(CES\\openTask('sess-bad',$x));",{'task_id':'T-1','workflow':'peer-review','base_sha':bad}).returncode,2)
 def test_diagnosis_roles_may_reproduce_but_pure_reviewers_never_execute(self):
  self.open('incident'); self.assertEqual(self.checked('incident-investigator')['status'],'PASS'); self.assertEqual(self.checked('qa-support')['status'],'PASS')
  for role in ['security-reviewer','database-reviewer','release-reviewer','tech-lead-reviewer','engineering-manager-reviewer','peer-reviewer','rca-analyzer','prd-reviewer','architect','product-manager','mr-review-publisher','engineering-orchestrator']:
   with self.subTest(role=role): r=self.broker(role,{'action':'run_check','name':'pass'}); self.assertEqual(r.returncode,2); self.assertIn('Action not allowed',r.stderr+r.stdout)
 def test_import_prd_is_a_product_manager_action_bound_to_the_task_prd(self):
  self.open(); src=self.repo/'docs/prd/sources'; src.mkdir(); (src/'T-1.xhtml').write_text(CONFLUENCE_EXPORT)
  for role in ['engineering-orchestrator','developer','prd-reviewer','architect']:
   with self.subTest(role=role): self.assertEqual(self.broker(role,{'action':'import_prd','source':'docs/prd/sources/T-1.xhtml'}).returncode,2)
  r=self.broker('product-manager',{'action':'import_prd','source':'docs/prd/sources/T-1.xhtml'}); self.assertEqual(r.returncode,2); self.assertIn('already exists',r.stdout)
  d=self.decode(self.broker('product-manager',{'action':'import_prd','source':'docs/prd/sources/T-1.xhtml','overwrite':True,'owner':'Named human'}))
  self.assertEqual(d['status'],'IMPORTED'); self.assertEqual(d['prd_path'],'docs/prd/T-1.md'); self.assertEqual(d['report']['acceptance_criteria'],2)
  text=(self.repo/'docs/prd/T-1.md').read_text(); self.assertIn('Status: DRAFT',text); self.assertIn('Owner: Named human',text); self.assertIn('| Auth & Token | 10 days | Backend |',text)
  self.assertEqual(self.report('product-manager','READY_FOR_ENGINEERING',prd_path='docs/prd/T-1.md').returncode,2)
  for bad in [{'source':'README.md'},{'source':'docs/prd/missing.xhtml'},{'source':'docs/prd/sources/T-1.xhtml','overwrite':'yes'},{'source':'docs/prd/sources/T-1.xhtml','overwrite':True,'owner':'a\nb'},{'source':'../outside.xhtml'}]:
   with self.subTest(bad=bad): self.assertEqual(self.broker('product-manager',{'action':'import_prd',**bad}).returncode,2)
 def test_import_prd_from_confluence_url_saves_the_source_for_review(self):
  self.open(); url=PrdImportTests.confluence(self)
  self.assertEqual(self.broker('product-manager',{'action':'import_prd','url':url,'source':'docs/prd/T-1.md'}).returncode,2)
  d=self.decode(self.broker('product-manager',{'action':'import_prd','url':url,'overwrite':True}))
  self.assertEqual(d['status'],'IMPORTED'); self.assertEqual(d['source'],'docs/prd/sources/T-1.xhtml'); self.assertEqual(d['fetched']['title'],'Cross-selling'); self.assertEqual(d['fetched']['page_id'],'180753756')
  self.assertTrue((self.repo/'docs/prd/sources/T-1.xhtml').read_text().startswith('<h1>Cross-selling</h1>')); self.assertIn('Status: DRAFT',(self.repo/'docs/prd/T-1.md').read_text())
  self.assertNotIn('s3cr3t',json.dumps(d))
  self.conf['confluence_hosts']=[]; self.saveconf(); r=self.broker('product-manager',{'action':'import_prd','url':url,'overwrite':True}); self.assertEqual(r.returncode,2); self.assertIn('not allowlisted',r.stdout)
 def test_task_scope_is_immutable(self):
  self.open(); self.assertEqual(self.php("CES\\output(CES\\openTask('test-session',$x));",{'task_id':'T-1','workflow':'feature','prd_path':'docs/prd/Other.md'}).returncode,2)
 def test_implicit_specialists_and_idempotent_task(self):
  task=self.open('upgrade'); self.assertIn('release-reviewer',task['risk_gates']); self.assertEqual(self.open('upgrade'),task)
 def test_end_to_end_feature_gate(self):
  self.complete(); result=self.decode(self.php("CES\\output(CES\\finalizeTask('test-session'));")); self.assertEqual(result['status'],'READY_FOR_HUMAN_REVIEW'); self.assertFalse(result['merge_authorized']); self.assertFalse(result['deploy_authorized'])
 def test_claimed_pass_without_check_rejected(self):
  self.ready(); self.assertEqual(self.submit_test_report('0'*32).returncode,2)
 def test_developer_test_receipt_cannot_replace_tester(self):
  self.ready(); check=self.checked('developer'); self.assertEqual(self.submit_test_report(check['id']).returncode,2)
 def test_missing_ac_result_rejected(self):
  self.ready(); self.assertEqual(self.report('tester','PASS',ac_results=[]).returncode,2)
 def test_duplicate_ac_result_rejected(self):
  self.ready(); c=self.checked(); row={'id':'AC-01','status':'PASS','assertion':'asserted','check_id':c['id']}; self.assertEqual(self.report('tester','PASS',ac_results=[row,row]).returncode,2)
 def test_stale_test_receipt_rejected(self):
  self.ready(); c=self.checked(); (self.repo/'app-changed.php').write_text('changed'); self.assertEqual(self.submit_test_report(c['id']).returncode,2)
 def test_stale_review_blocks_finalization(self):
  self.complete(); (self.repo/'app-changed.php').write_text('changed'); self.assertEqual(self.php("CES\\output(CES\\finalizeTask('test-session')); ").returncode,2)
 def test_check_failure_and_timeout_receipts(self):
  self.open()
  for name in ['fail','timeout']:
   with self.subTest(name=name): r=self.checked(name=name); self.assertEqual(r['status'],'FAIL'); self.assertNotEqual(r['exit_code'],0)
 def test_check_workspace_mutation_fails(self):
  self.open(); r=self.checked(name='mutate'); self.assertTrue(r['workspace_mutated']); self.assertEqual(r['status'],'FAIL')
 def test_check_environment_not_inherited(self):
  self.open(); self.env['CES_TEST_SECRET']='never-pass-this'; r=self.checked(name='env'); self.assertIn('"APP_ENV":"testing"',r['output']); self.assertIn('"SECRET":false',r['output'])
 def test_dual_pipe_output_no_deadlock(self):
  r=self.decode(self.php("CES\\output(CES\\process([PHP_BINARY,'scripts/claude/tests/fixtures/check.php','noisy'],'',10,1000000));")); self.assertEqual(r['exit_code'],0); self.assertGreater(len(r['stderr']),200000)
 def test_large_output_is_fully_drained_not_truncated(self):
  """A single bounded read after child exit could silently truncate a large response."""
  r=self.decode(self.php("CES\\output(CES\\process([PHP_BINARY,'scripts/claude/tests/fixtures/check.php','noisy'],'',20,8000000));"))
  self.assertEqual(r['exit_code'],0); self.assertFalse(r['truncated'])
  self.assertEqual(len(r['stderr']),300000)
  # the fixture writes 3000x100 bytes per pipe, then a trailing line on stdout only
  self.assertEqual(len(r['stdout']),300038); self.assertIn('assertion executed',r['stdout'][-60:])
 def test_output_bound(self):
  r=self.decode(self.php("CES\\output(CES\\process([PHP_BINARY,'scripts/claude/tests/fixtures/check.php','noisy'],'',10,1000));")); self.assertTrue(r['truncated']); self.assertNotEqual(r['exit_code'],0)
 def test_blocking_finding_cannot_pass(self):
  self.open('peer-review'); r=self.report('peer-reviewer','PASS',findings=[{'severity':'BLOCKING','location':'app/A.php:1','problem':'bug','impact':'wrong','evidence':'repro'}]); self.assertEqual(r.returncode,2)
 def test_report_unknown_status_and_malformed_findings(self):
  self.open('peer-review'); self.assertEqual(self.report('peer-reviewer','LOOKS_GOOD').returncode,2); self.assertEqual(self.report('peer-reviewer','PASS',findings='not an array').returncode,2)
 def test_readonly_fail_delivers_review_not_acceptance(self):
  self.open('peer-review'); self.decode(self.report('peer-reviewer','FAIL')); r=self.decode(self.php("CES\\output(CES\\finalizeTask('test-session'));")); self.assertEqual(r['status'],'REVIEW_DELIVERED')
 def test_attempt_budget_and_idempotent_receipt(self):
  self.ready(); self.implemented(); self.implemented(); self.implemented(); self.assertEqual(self.hook('developer','Write',{'file_path':'app/A.php'}).returncode,2)
 def test_blocked_report_does_not_consume_attempt(self):
  self.ready(); self.decode(self.report('developer','BLOCKED')); t=self.decode(self.php("CES\\output(CES\\loadTask('test-session'));")); self.assertEqual(t['repair_attempts'],0)
 def test_receipt_replay_does_not_consume_attempt(self):
  self.ready(); r=self.implemented(); replay=self.decode(self.php("CES\\output(CES\\recordReport('test-session','developer',$x['agent_id'],$x['report']));",r)); self.assertEqual(replay,r); t=self.decode(self.php("CES\\output(CES\\loadTask('test-session'));")); self.assertEqual(t['repair_attempts'],1)
 def test_stop_retry_is_bounded_and_invalid_gate_persists(self):
  self.open('peer-review'); payload={'agent_type':'peer-reviewer','session_id':self.session,'agent_id':'p1','last_assistant_message':'looks good'}
  first=self.decode(run([PHP,'scripts/claude/hooks/output-gate.php'],self.repo,payload,self.env)); self.assertEqual(first['decision'],'block')
  second=self.decode(run([PHP,'scripts/claude/hooks/output-gate.php'],self.repo,{**payload,'stop_hook_active':True},self.env)); self.assertNotIn('decision',second); self.assertEqual(self.php("CES\\output(CES\\finalizeTask('test-session')); ").returncode,2)
 def test_invalid_report_invalidates_prior_finalization(self):
  self.complete(); self.decode(self.php("CES\\output(CES\\finalizeTask('test-session'));")); self.php("CES\\markInvalid('test-session','tester','bad later report'); CES\\output(['ok'=>true]);")
  r=self.decode(run([PHP,'scripts/claude/hooks/final-gate.php'],self.repo,{'session_id':self.session,'last_assistant_message':'Summary\n```ces-result\n{"task_id":"T-1","status":"READY_FOR_HUMAN_REVIEW"}\n```'},self.env)); self.assertEqual(r['decision'],'block')
 def test_final_gate_allows_pause_while_background_tasks_are_in_flight(self):
  self.open('peer-review')
  payload={'session_id':self.session,'last_assistant_message':'Waiting for specialist reviews.','background_tasks':[{'id':'agent-1','type':'subagent','status':'running','description':'Peer review','agent_type':'peer-reviewer'}]}
  r=run([PHP,'scripts/claude/hooks/final-gate.php'],self.repo,payload,self.env)
  self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(r.stdout,'')

 def test_existing_mr_publication_is_required_for_completion(self):
  self.mock(sha=self.sha); self.open('peer-review',mr_url=self.url,reviewed_head_sha=self.sha)
  self.decode(self.report('peer-reviewer','FAIL',reviewed_head_sha=self.sha,publishable_comments=self.payload()['comments']))
  self.assertEqual(self.php("CES\\output(CES\\finalizeTask('test-session')); ").returncode,2)
  published=self.decode(self.broker('mr-review-publisher',{'action':'publish_review'})); self.assertEqual(published['status'],'PUBLISHED')
  final=self.decode(self.broker('engineering-orchestrator',{'action':'finalize'})); self.assertEqual(final['status'],'REVIEW_DELIVERED')
 def test_publication_dry_run_does_not_satisfy_workflow(self):
  self.mock(sha=self.sha); self.open('peer-review',mr_url=self.url,reviewed_head_sha=self.sha)
  self.decode(self.report('peer-reviewer','PASS',reviewed_head_sha=self.sha,publishable_comments=[]))
  self.decode(self.broker('mr-review-publisher',{'action':'publish_review','dry_run':True}))
  self.assertEqual(self.php("CES\\output(CES\\finalizeTask('test-session')); ").returncode,2)
 def test_local_dirty_mr_checkout_rejected(self):
  self.open('peer-review',mr_url='https://github.test/org/repo/pull/7',reviewed_head_sha=self.sha)
  f=self.repo/'docs/prd/T-1.md'; f.write_text(f.read_text()+'changed')
  self.assertEqual(self.report('peer-reviewer','PASS',reviewed_head_sha=self.sha,publishable_comments=[]).returncode,2)
 def test_local_wrong_head_rejected(self):
  self.open('peer-review',mr_url='https://github.test/org/repo/pull/7',reviewed_head_sha='a'*40)
  self.assertEqual(self.report('peer-reviewer','PASS',reviewed_head_sha='a'*40,publishable_comments=[]).returncode,2)
 def test_missing_specialist_gate_blocks(self):
  self.ready(); d=self.repo/'database/migrations'; d.mkdir(parents=True); (d/'test.php').write_text('<?php // fixture')
  self.implemented(); self.decode(self.report('peer-reviewer','PASS')); c=self.checked(); self.decode(self.submit_test_report(c['id']))
  r=self.php("CES\\output(CES\\finalizeTask('test-session')); "); self.assertEqual(r.returncode,2); self.assertIn('database-reviewer',r.stdout)
 def test_risk_patterns_cover_package_based_layout(self):
  """Stock-Laravel path anchors miss packages/<Vendor>/<Package>/src/ layouts entirely."""
  self.open()
  for path,expected in [
    ('packages/Vendor/RestApi/src/Http/Controllers/V1/Shop/Nested/CheckoutController.php','security-reviewer'),
    ('packages/Vendor/Storefront/src/Http/Middleware/Theme.php','security-reviewer'),
    ('app/Builders/DeliveryAddressBuilder.php','security-reviewer'),
    ('packages/Vendor/Sales/src/Database/Migrations/2026_add_col.php','database-reviewer'),
    ('packages/Vendor/Sales/src/Repositories/OrderRepository.php','database-reviewer'),
    ('packages/Vendor/Queueing/src/Jobs/DispatchBatch.php','performance-reviewer'),
    ('packages/Vendor/Core/src/Providers/CoreServiceProvider.php','tech-lead-reviewer'),
   ]:
   with self.subTest(path=path):
    f=self.repo/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('<?php // fixture')
    gates=self.decode(self.php("CES\\output(['g'=>CES\\derivedRiskGates(CES\\loadTask('test-session'))]);"))['g']
    f.unlink()
    self.assertIn(expected,gates,path)
 def test_generic_package_code_adds_no_risk_gate(self):
  self.open()
  for path in ['packages/Vendor/Storefront/src/Http/Controllers/HomeController.php','app/Support/StringHelper.php']:
   with self.subTest(path=path):
    f=self.repo/path; f.parent.mkdir(parents=True,exist_ok=True); f.write_text('<?php // fixture')
    gates=self.decode(self.php("CES\\output(['g'=>CES\\derivedRiskGates(CES\\loadTask('test-session'))]);"))['g']
    f.unlink()
    self.assertEqual(gates,[],path)
 def test_untracked_governance_not_application_risk(self):
  self.open(); f=self.repo/'.claude/rules/custom-security.md'; f.write_text('Custom policy'); r=self.decode(self.php("CES\\output(['gates'=>CES\\derivedRiskGates(CES\\loadTask('test-session'))]);")); self.assertEqual(r['gates'],[])

class PublisherTests(Fixture):
 def test_github_inline_and_summary(self):
  self.mock(); r=self.decode(self.publish()); self.assertEqual(r['status'],'PUBLISHED'); s=self.state_value(); self.assertEqual(len(s['posted']),2); self.assertEqual(s['posted'][0]['payload']['commit_id'],'a'*40)
 def test_gitlab_positions(self):
  self.mock('gitlab'); p=self.payload(); p['comments'][0].update(old_path='app/Old.php',old_line=3); r=self.decode(self.publish(p)); self.assertEqual(r['status'],'PUBLISHED'); pos=self.state_value()['posted'][0]['payload']['position']; self.assertEqual(pos['head_sha'],'a'*40); self.assertEqual(pos['old_path'],'app/Old.php'); self.assertEqual(pos['old_line'],3)
 def test_exact_head_required_no_writes(self):
  self.mock(sha='b'*40); r=self.decode(self.publish(),2); self.assertEqual(r['status'],'BLOCKED'); self.assertNotIn('posted',self.state_value())
 def test_head_changes_mid_publication(self):
  self.mock(stale_after=2); r=self.decode(self.publish(),2); self.assertTrue(r['partial_publication']); self.assertEqual(r['inline_comments_posted'],1); self.assertFalse(r['summary_comment_posted'])
 def test_closed_mr_no_writes(self):
  self.mock(state='closed'); self.decode(self.publish(),2); self.assertNotIn('posted',self.state_value())
 def test_dry_run_has_zero_actual_writes(self):
  self.mock(); r=self.decode(self.publish(dry=True)); self.assertEqual(r['status'],'DRY_RUN'); self.assertEqual(r['inline_comments_posted'],0); self.assertFalse(r['summary_comment_posted']); self.assertNotIn('posted',self.state_value())
 def test_rerun_deduplicates(self):
  self.mock(); self.decode(self.publish()); r=self.decode(self.publish()); self.assertEqual(r['status'],'ALREADY_PUBLISHED'); self.assertEqual(len(self.state_value()['posted']),2)
 def test_fallback_is_persistently_deduplicated(self):
  self.mock(inline_error=422); r=self.decode(self.publish()); self.assertEqual(r['status'],'PUBLISHED_WITH_FALLBACK'); self.assertIn('Controlled evidenced defect',self.state_value()['posted'][0]['payload']['body']); r=self.decode(self.publish()); self.assertEqual(r['status'],'ALREADY_PUBLISHED'); self.assertEqual(len(self.state_value()['posted']),1)
 def test_summary_only_findings_preserved(self):
  self.mock(); p=self.payload(); p['comments'][0]['line']=None; r=self.decode(self.publish(p)); self.assertEqual(r['fallback_comments'],1); self.assertEqual(r['inline_comments_posted'],0)
 def test_nits_console_only(self):
  self.mock(); p=self.payload(); p['comments'][0]['severity']='NIT'; r=self.decode(self.publish(p)); self.assertEqual(r['inline_comments_posted'],0); self.assertNotIn('Controlled evidenced defect',self.state_value()['posted'][0]['payload']['body'])
 def test_pagination_github(self):
  self.mock(); self.decode(self.publish()); s=self.state_value(); s['notes']=[{'id':i,'body':'older','user':{'id':11}} for i in range(100)]+s['notes']; self.state.write_text(json.dumps(s)); r=self.decode(self.publish()); self.assertEqual(r['status'],'ALREADY_PUBLISHED'); self.assertTrue(any('page=2' in c['endpoint'] for c in self.state_value()['calls']))
 def test_pagination_gitlab(self):
  self.mock('gitlab'); self.decode(self.publish()); s=self.state_value(); s['inline']=[{'id':str(i),'notes':[{'body':'older','author':{'id':11}}]} for i in range(100)]+s['inline']; self.state.write_text(json.dumps(s)); r=self.decode(self.publish()); self.assertEqual(r['status'],'ALREADY_PUBLISHED'); self.assertTrue(any('/discussions?per_page=100&page=2' in c['endpoint'] for c in self.state_value()['calls']))
 def test_foreign_actor_markers_do_not_suppress_our_review(self):
  self.mock(); self.decode(self.publish()); s=self.state_value()
  for item in s['notes']+s['inline']: item['user']['id']=99; item['author']['id']=99
  self.state.write_text(json.dumps(s)); r=self.decode(self.publish()); self.assertEqual(r['status'],'PUBLISHED'); self.assertEqual(len(self.state_value()['posted']),4)
 def test_dedup_read_failure_blocks_without_writes(self):
  self.mock(fail_reads=True); r=self.decode(self.publish(),2); self.assertEqual(r['status'],'BLOCKED'); self.assertNotIn('posted',self.state_value())
 def test_auth_and_rate_errors_do_not_fallback(self):
  for err in [401,403,429,503]:
   with self.subTest(error=err):
    self.mock(inline_error=err); r=self.decode(self.publish(),2); self.assertEqual(r['status'],'BLOCKED'); self.assertNotIn('posted',self.state_value())
 def test_summary_failure_reports_partial(self):
  self.mock(summary_error=503); r=self.decode(self.publish(),2); self.assertTrue(r['partial_publication']); self.assertEqual(r['inline_comments_posted'],1)
 def test_gitlab_version_mismatch(self):
  self.mock('gitlab',version_sha='b'*40); self.decode(self.publish(),2); self.assertNotIn('posted',self.state_value())
 def test_invalid_publication_contracts(self):
  self.mock()
  for change in [{'reviewed_head_sha':''},{'review_status':'APPROVE'},{'mr_url':'https://evil.example/org/repo/pull/7'},{'mr_url':'https://user@github.test/org/repo/pull/7'},{'comments':'bad'}]:
   with self.subTest(change=change): self.assertEqual(self.publish(self.payload(**change)).returncode,2)
 def test_invalid_lines_and_duplicate_ids(self):
  self.mock(); p=self.payload(); p['comments'][0]['line']=0; self.assertEqual(self.publish(p).returncode,2); p=self.payload(); p['comments']*=2; self.assertEqual(self.publish(p).returncode,2)
 def test_fetch_returns_bounded_summary_without_diff_bodies(self):
  """The raw provider object and diff bodies must not be returned; a large MR outgrew the transcript."""
  for provider in ['github','gitlab']:
   with self.subTest(provider=provider):
    self.setUp(); self.mock(provider)
    r=self.decode(self.php("CES\\output(CES\\fetchMr($x['url']));",{'url':self.url},lib='mr'))
    self.assertEqual(r['reviewed_head_sha'],'a'*40); self.assertTrue(r['open']); self.assertFalse(r['diff_incomplete'])
    blob=json.dumps(r)
    for leaked in ['@@ -1 +1 @@','+new','-old','avatar_url','time_stats']:
     self.assertNotIn(leaked,blob,'fetch_mr leaked '+leaked)
    self.assertEqual([f['new_path'] for f in r['files']],['app/Test.php'])
    self.assertTrue(r['files'][0]['diff_available'])
    for key in ['diff','patch']: self.assertNotIn(key,r['files'][0])
    m=r['metadata']
    self.assertEqual(m['files_listed'],1); self.assertEqual(m['state'],'open' if provider=='github' else 'opened')
    self.assertFalse(m['description_truncated']); self.assertEqual(len(m['description_sha256']),64)
    self.tearDown()
 def test_fetch_bounds_a_huge_description(self):
  self.mock('gitlab')
  s=self.state_value(); s['description']='x'*50000; self.state.write_text(json.dumps(s))
  r=self.decode(self.php("CES\\output(CES\\fetchMr($x['url']));",{'url':self.url},lib='mr'))
  m=r['metadata']
  self.assertTrue(m['description_truncated']); self.assertEqual(len(m['description_excerpt']),8000)
  self.assertLess(len(json.dumps(r)),20000)
 def test_incomplete_files_are_individually_marked(self):
  self.mock(missing_patch=True)
  r=self.decode(self.php("CES\\output(CES\\fetchMr($x['url']));",{'url':self.url},lib='mr'))
  self.assertTrue(r['diff_incomplete']); self.assertFalse(r['files'][0]['diff_available'])
 def test_missing_diff_flagged(self):
  self.mock(missing_patch=True); r=self.decode(self.php("CES\\output(CES\\fetchMr($x['url']));",{'url':self.url},lib='mr')); self.assertTrue(r['diff_incomplete'])
 def test_local_lock_blocks_second_publisher(self):
  import fcntl
  self.mock(); lock=self.repo/'.claude/engineering-system/runtime/locks'/ (hashlib.sha256(self.url.encode()).hexdigest()+'.lock'); lock.parent.mkdir(parents=True)
  with lock.open('w') as fh:
   fcntl.flock(fh,fcntl.LOCK_EX|fcntl.LOCK_NB); self.assertEqual(self.publish().returncode,2)

class InstallerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='ces-install-'); self.target=Path(self.tmp.name)/'project'; self.target.mkdir(); (self.target/'.git').mkdir(); self.orig={'CLAUDE.md':'Existing Laravel conventions\n','README.md':'Real project README\n','.gitignore':'vendor/\n'}
  for name,body in self.orig.items(): (self.target/name).write_text(body)
 def tearDown(self): self.tmp.cleanup()
 def install(self,*args): return run([PHP,P/'install.php',*args],self.target,timeout=30)
 def setsettings(self,obj):
  (self.target/'.claude').mkdir(exist_ok=True); (self.target/'.claude/settings.json').write_text(json.dumps(obj))
 def snapshot(self): return {str(f.relative_to(self.target)):f.read_bytes() for f in self.target.rglob('*') if f.is_file()}
 def test_dry_run_writes_nothing(self):
  before=self.snapshot(); r=self.install(); self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(before,self.snapshot())
 def test_invalid_settings_preflight_no_partial_install(self):
  self.setsettings({}); (self.target/'.claude/settings.json').write_text('{not-json'); before=self.snapshot(); r=self.install('--apply'); self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_preserve_roots_unknown_settings_and_user_hooks(self):
  hook={'matcher':'Write','hooks':[{'type':'command','command':'echo user-hook'}]}; self.setsettings({'env':{},'agent':'my-existing-agent','hooks':{'PreToolUse':[hook]},'permissions':{'deny':['Read(.env)']}})
  r=self.install('--apply','--set-default-agent'); self.assertEqual(r.returncode,0,r.stderr)
  for name,body in self.orig.items(): self.assertEqual((self.target/name).read_text(),body)
  s=json.loads((self.target/'.claude/settings.json').read_text()); self.assertEqual(s['env'],{}); self.assertEqual(s['agent'],'my-existing-agent'); self.assertIn(hook,s['hooks']['PreToolUse']); self.assertEqual(s['permissions']['deny'],['Read(.env)'])
 def test_install_idempotent(self):
  self.assertEqual(self.install('--apply').returncode,0); before=self.snapshot(); r=self.install('--apply'); self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(before,self.snapshot()); self.assertIn('0 file changes',r.stdout)
 def test_unowned_conflict_blocks_before_any_writes(self):
  p=self.target/'.claude/agents/developer.md'; p.parent.mkdir(parents=True); p.write_text('Custom agent'); before=self.snapshot(); r=self.install('--apply'); self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_replace_backups_customized_agent(self):
  p=self.target/'.claude/agents/developer.md'; p.parent.mkdir(parents=True); p.write_text('Custom agent'); r=self.install('--apply','--replace-existing'); self.assertEqual(r.returncode,0,r.stderr); backups=list((self.target/'.claude/engineering-system/backups').glob('*/.claude/agents/developer.md')); self.assertEqual(len(backups),1); self.assertEqual(backups[0].read_text(),'Custom agent')
 def test_customized_managed_asset_requires_explicit_replace(self):
  self.assertEqual(self.install('--apply').returncode,0); p=self.target/'.claude/agents/developer.md'; p.write_text(p.read_text()+'\nCustom edit\n'); before=self.snapshot(); r=self.install('--apply'); self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_symlink_target_rejected(self):
  other=Path(self.tmp.name)/'other'; other.mkdir(); (self.target/'.claude').symlink_to(other,target_is_directory=True); r=self.install('--apply'); self.assertEqual(r.returncode,2); self.assertEqual(list(other.iterdir()),[])
 def test_hardlinked_settings_preflight_no_mutation(self):
  self.setsettings({}); os.link(self.target/'.claude/settings.json',Path(self.tmp.name)/'settings-link.json'); before=self.snapshot(); r=self.install('--apply'); self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_array_settings_rejected(self):
  self.setsettings([]); r=self.install('--apply'); self.assertEqual(r.returncode,2); self.assertFalse((self.target/'scripts').exists())
 def test_git_worktree_file_supported(self):
  (self.target/'.git').rmdir(); (self.target/'.git').write_text('gitdir: /dummy/test-only\n'); r=self.install('--apply'); self.assertEqual(r.returncode,0,r.stderr)
 def test_force_default_agent_explicit(self):
  self.setsettings({'agent':'custom'}); r=self.install('--apply','--force-default-agent','--set-default-agent'); self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(json.loads((self.target/'.claude/settings.json').read_text())['agent'],'engineering-orchestrator')
 def test_human_configuration_preserved_on_upgrade(self):
  self.assertEqual(self.install('--apply').returncode,0); f=self.target/'.claude/engineering-system/config.json'; c=json.loads(f.read_text()); c['allowed_hosts']=['gitlab.company.test']; f.write_text(json.dumps(c)); self.assertEqual(self.install('--apply').returncode,0); self.assertEqual(json.loads(f.read_text()),c)
 def test_explicit_allow_host_on_new_install(self):
  r=self.install('--apply','--allow-host=git.internal.example'); self.assertEqual(r.returncode,0,r.stderr); c=json.loads((self.target/'.claude/engineering-system/config.json').read_text()); self.assertEqual(c['allowed_hosts'],['git.internal.example'])
 def test_explicit_allow_host_merges_existing_human_config(self):
  self.assertEqual(self.install('--apply','--allow-host=gitlab.company.test').returncode,0); f=self.target/'.claude/engineering-system/config.json'; c=json.loads(f.read_text()); c['allow_publish_nits']=True; f.write_text(json.dumps(c)); r=self.install('--apply','--allow-host=git.internal.example'); self.assertEqual(r.returncode,0,r.stderr); c2=json.loads(f.read_text()); self.assertTrue(c2['allow_publish_nits']); self.assertEqual(c2['allowed_hosts'],['git.internal.example','gitlab.company.test'])
 def test_upgrade_adds_new_policy_keys_but_never_changes_human_values(self):
  self.assertEqual(self.install('--apply').returncode,0); f=self.target/'.claude/engineering-system/config.json'
  human={'version':3,'allowed_hosts':['git.company.test','docs.company.test'],'allow_publish_nits':False,'signoz_read_tools':[],'execution_isolated':False,'checks':{},'risk_patterns':{'security-reviewer':'~(?:auth|policy)~i'}}
  f.write_text(json.dumps(human,indent=4)); r=self.install('--apply'); self.assertEqual(r.returncode,0,r.stderr); self.assertIn('added missing policy keys: confluence_hosts, notes',r.stdout)
  c=json.loads(f.read_text()); self.assertEqual(c['confluence_hosts'],[]); self.assertIn('notes',c)
  for key in human: self.assertEqual(c[key],human[key],key)
  self.assertEqual(len(list((self.target/'.claude/engineering-system/backups').glob('*/.claude/engineering-system/config.json'))),1)
  before=self.snapshot(); r=self.install('--apply'); self.assertEqual(r.returncode,0); self.assertIn('0 file changes',r.stdout); self.assertEqual(before,self.snapshot())
 def test_explicit_allow_confluence_host(self):
  r=self.install('--apply','--allow-confluence-host=docs.company.test'); self.assertEqual(r.returncode,0,r.stderr); f=self.target/'.claude/engineering-system/config.json'
  self.assertEqual(json.loads(f.read_text())['confluence_hosts'],['docs.company.test']); self.assertEqual(json.loads(f.read_text())['allowed_hosts'],[])
  c=json.loads(f.read_text()); c['allow_publish_nits']=True; f.write_text(json.dumps(c))
  r=self.install('--apply','--allow-confluence-host=wiki.company.test','--allow-host=git.company.test'); self.assertEqual(r.returncode,0,r.stderr); c2=json.loads(f.read_text())
  self.assertEqual(c2['confluence_hosts'],['docs.company.test','wiki.company.test']); self.assertEqual(c2['allowed_hosts'],['git.company.test']); self.assertTrue(c2['allow_publish_nits'])
  r=self.install('--apply','--allow-confluence-host=docs.company.test'); self.assertEqual(r.returncode,0); self.assertIn('0 file changes',r.stdout); self.assertIn('host already trusted',r.stdout)
  before=self.snapshot(); r=self.install('--apply','--allow-confluence-host=https://docs.company.test/x'); self.assertEqual(r.returncode,2); self.assertIn('--allow-confluence-host',r.stderr); self.assertEqual(before,self.snapshot())
 def test_invalid_allow_host_rejected_without_writes(self):
  before=self.snapshot(); r=self.install('--apply','--allow-host=https://git.example.com/path'); self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_gitignore_untouched_by_default_and_opt_in_append(self):
  self.assertEqual(self.install('--apply').returncode,0); self.assertEqual((self.target/'.gitignore').read_text(),self.orig['.gitignore']); r=self.install('--apply','--add-gitignore'); self.assertEqual(r.returncode,0,r.stderr); text=(self.target/'.gitignore').read_text(); self.assertIn('vendor/\n',text); self.assertEqual(text.count('.claude/engineering-system/runtime/'),1); self.assertEqual(text.count('.claude/engineering-system/backups/'),1); self.assertEqual(text.count('.claude/engineering-system/installed-files.json'),1)
 def test_gitignore_opt_in_is_idempotent(self):
  self.assertEqual(self.install('--apply','--add-gitignore').returncode,0); before=(self.target/'.gitignore').read_text(); self.assertEqual(self.install('--apply','--add-gitignore').returncode,0); self.assertEqual((self.target/'.gitignore').read_text(),before)
 def test_git_exclude_opt_in_keeps_tracked_tree_clean(self):
  """.gitignore is tracked; appending to it dirties the tree and blocks commit-bound MR review."""
  r=self.install('--apply','--add-git-exclude'); self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual((self.target/'.gitignore').read_text(),self.orig['.gitignore'])
  text=(self.target/'.git/info/exclude').read_text()
  for pattern in ['.claude/engineering-system/runtime/','.claude/engineering-system/backups/','.claude/engineering-system/installed-files.json']:
   self.assertEqual(text.count(pattern),1,pattern)
 def test_git_exclude_preserves_existing_local_patterns_and_is_idempotent(self):
  info=self.target/'.git/info'; info.mkdir(parents=True); (info/'exclude').write_text('# local\nmy-scratch/\n')
  self.assertEqual(self.install('--apply','--add-git-exclude').returncode,0)
  first=(info/'exclude').read_text(); self.assertIn('my-scratch/',first); self.assertIn('.claude/engineering-system/runtime/',first)
  self.assertEqual(self.install('--apply','--add-git-exclude').returncode,0)
  self.assertEqual((info/'exclude').read_text(),first)
 def test_gitignore_and_git_exclude_are_mutually_exclusive(self):
  before=self.snapshot(); r=self.install('--apply','--add-gitignore','--add-git-exclude')
  self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_git_exclude_rejected_in_linked_worktree_without_writes(self):
  (self.target/'.git').rmdir(); (self.target/'.git').write_text('gitdir: /dummy/test-only\n')
  before=self.snapshot(); r=self.install('--apply','--add-git-exclude')
  self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_legacy_publisher_autoallow_removed_only_explicit_migration(self):
  self.setsettings({'permissions':{'allow':['Bash(php scripts/claude/mr/publish-review.php *)','Read']}}); r=self.install('--apply','--replace-existing'); self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(json.loads((self.target/'.claude/settings.json').read_text())['permissions']['allow'],['Read'])

class RecordingResult(unittest.TextTestResult):
 def __init__(self,*a,**kw): super().__init__(*a,**kw); self.records=[]; self.start_times={}
 def startTest(self,test): self.start_times[test.id()]=time.monotonic(); super().startTest(test)
 def addSuccess(self,test): self.records.append({'test':test.id(),'status':'PASS','seconds':round(time.monotonic()-self.start_times[test.id()],3)}); super().addSuccess(test)
 def addFailure(self,test,err): self.records.append({'test':test.id(),'status':'FAIL','detail':self._exc_info_to_string(err,test)}); super().addFailure(test,err)
 def addError(self,test,err): self.records.append({'test':test.id(),'status':'ERROR','detail':self._exc_info_to_string(err,test)}); super().addError(test,err)

if __name__=='__main__':
 parser=argparse.ArgumentParser(); parser.add_argument('--json',type=Path); parser.add_argument('--package',type=Path); parser.add_argument('--group'); ns,remaining=parser.parse_known_args()
 if ns.package: P=ns.package.resolve()
 if not PHP: raise SystemExit('PHP 8.2+ must be installed')
 suite=unittest.defaultTestLoader.loadTestsFromName(ns.group,sys.modules[__name__]) if ns.group else unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]); result=unittest.TextTestRunner(verbosity=2,resultclass=RecordingResult).run(suite)
 if ns.json:
  ns.json.parent.mkdir(parents=True,exist_ok=True); ns.json.write_text(json.dumps({'status':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'records':result.records,'scope':'Offline PHP/fixture/installer and mocked gh/glab API tests. No live Claude Code, SigNoz or real MR endpoints.'},indent=2)+'\n')
 raise SystemExit(0 if result.wasSuccessful() else 1)
