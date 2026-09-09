#!/usr/bin/env python3
"""CES offline regression suite. No network or real provider credentials required.
Run: python3 scripts/claude/tests/test_system.py
Optional: --json /absolute/path/report.json --package /path/to/package
"""
from __future__ import annotations
import argparse, copy, hashlib, json, os, shlex, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path
P=Path(__file__).resolve().parents[3]
PHP=shutil.which('php')
REPORT=None

def run(argv,cwd=None,data=None,env=None,timeout=25):
 return subprocess.run([str(x) for x in argv],cwd=cwd,input=None if data is None else (data if isinstance(data,str) else json.dumps(data)),text=True,capture_output=True,env=env,timeout=timeout)
def valid_prd():
 sections=['Problem Statement','Context / Evidence','Goals','Non-Goals','Users / Actors','Functional Requirements','Acceptance Criteria','Failure / Negative Behavior','Non-Functional Requirements','Observability Requirements','Dependencies','Rollout / Migration Expectations','Success Metrics','Risks','Open Questions','Out of Scope']
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
  self.conf.update({'allowed_hosts':['github.test','gitlab.test'],'execution_isolated':True,'checks':{m:{'trusted':True,'kind':'test','roles':['tester','regression-tester','developer','qa-support','performance-reviewer'],'argv':[PHP,'scripts/claude/tests/fixtures/check.php',m],'timeout_seconds':1 if m=='timeout' else 10,'env':{'APP_ENV':'testing'}} for m in ['pass','fail','timeout','mutate','noisy','env']}})
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
 def test_signoz_allowlist_and_mutations(self):
  read='mcp__signoz__signoz_search_logs'; write='mcp__signoz__signoz_create_alert'; self.assertEqual(self.hook('tester',read,{}).returncode,2)
  self.conf['signoz_read_tools']=[read,write]; self.saveconf(); self.assertEqual(self.hook('tester',read,{}).returncode,0); self.assertEqual(self.hook('tester',write,{}).returncode,2)
 def test_nested_agent_denied(self): self.assertEqual(self.hook('tester','Agent',{'subagent_type':'developer'}).returncode,2)
 def test_pretask_specialist_delegation_denied_with_actionable_message(self):
  r=self.hook('engineering-orchestrator','Agent',{'subagent_type':'peer-reviewer'}); self.assertEqual(r.returncode,2); self.assertIn('Pre-task MR/config preflight',r.stderr)
 def test_developer_delegation_requires_product_gate(self):
  self.open(); self.assertEqual(self.hook('engineering-orchestrator','Agent',{'subagent_type':'developer'}).returncode,2)
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
 def test_invalid_allow_host_rejected_without_writes(self):
  before=self.snapshot(); r=self.install('--apply','--allow-host=https://git.example.com/path'); self.assertEqual(r.returncode,2); self.assertEqual(before,self.snapshot())
 def test_gitignore_untouched_by_default_and_opt_in_append(self):
  self.assertEqual(self.install('--apply').returncode,0); self.assertEqual((self.target/'.gitignore').read_text(),self.orig['.gitignore']); r=self.install('--apply','--add-gitignore'); self.assertEqual(r.returncode,0,r.stderr); text=(self.target/'.gitignore').read_text(); self.assertIn('vendor/\n',text); self.assertEqual(text.count('.claude/engineering-system/runtime/'),1); self.assertEqual(text.count('.claude/engineering-system/backups/'),1); self.assertEqual(text.count('.claude/engineering-system/installed-files.json'),1)
 def test_gitignore_opt_in_is_idempotent(self):
  self.assertEqual(self.install('--apply','--add-gitignore').returncode,0); before=(self.target/'.gitignore').read_text(); self.assertEqual(self.install('--apply','--add-gitignore').returncode,0); self.assertEqual((self.target/'.gitignore').read_text(),before)
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
