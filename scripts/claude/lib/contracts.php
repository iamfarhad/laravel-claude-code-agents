<?php

declare(strict_types=1);
namespace CES;
require_once __DIR__ . '/common.php';

const PRD_SECTIONS = ['Problem Statement','Context / Evidence','Goals','Non-Goals','Users / Actors','Functional Requirements','Acceptance Criteria','Failure / Negative Behavior','Non-Functional Requirements','Observability Requirements','Dependencies','Rollout / Migration Expectations','Success Metrics','Risks','Open Questions','Out of Scope'];

function validatePrd(string $path): array {
    $path=safePath($path,true); $text=(string)file_get_contents($path); $errors=[];
    if (strlen($text)>1048576) throw new \RuntimeException('PRD exceeds 1 MiB.');
    // Examples in fenced blocks are not definitions or metadata.
    $plain=preg_replace('/^(`{3,}|~{3,})[^\r\n]*\R[\s\S]*?^\1[ \t]*$/m','',$text) ?? $text;
    preg_match_all('/^Status:[ \t]*([^\r\n]+)[ \t]*$/mi',$plain,$m);
    if (count($m[1])!==1 || strtoupper(trim($m[1][0] ?? ''))!=='READY_FOR_ENGINEERING') $errors[]='Exactly one Status: READY_FOR_ENGINEERING metadata line is required.';
    if (!preg_match('/^Owner:[ \t]*\S[^\r\n]*$/mi',$plain)) $errors[]='Owner metadata is required; do not invent an approver.';
    $sections=[];
    preg_match_all('/^##[ \t]+([^\r\n]+)\R([\s\S]*?)(?=^##[ \t]+|\z)/m',$plain,$matches,PREG_SET_ORDER);
    foreach ($matches as $s) {
        $heading=trim($s[1]);
        if (isset($sections[$heading])) $errors[]='Duplicate section: '.$heading;
        $sections[$heading]=trim($s[2]);
    }
    foreach (PRD_SECTIONS as $h) if (trim($sections[$h] ?? '')==='') $errors[]='Missing or empty section: '.$h;
    if (!in_array(strtolower(trim($sections['Open Questions'] ?? '')),['none','none.'],true)) $errors[]='Open Questions must explicitly be None before readiness.';
    if (preg_match('/\b(TBD|TODO|PLACEHOLDER|FILL ME|UNKNOWN_PRODUCT_DECISION)\b/i',$plain)) $errors[]='Unresolved placeholder in PRD.';
    $requirements=[];
    preg_match_all('/^[-*][ \t]+(FR-\d{2,}):[ \t]*(\S[^\r\n]*)$/mi',$sections['Functional Requirements'] ?? '',$frs,PREG_SET_ORDER);
    foreach ($frs as $fr) { $id=strtoupper($fr[1]); if (isset($requirements[$id])) $errors[]='Duplicate requirement '.$id; $requirements[$id]=trim($fr[2]); }
    if (!$requirements) $errors[]='Functional Requirements need - FR-01: ... definitions.';
    $acs=[]; $covered=[];
    preg_match_all('/^###[ \t]+(AC-\d{2,})(?:[ \t]*:[^\r\n]*)?[ \t]*\R([\s\S]*?)(?=^###[ \t]+|\z)/mi',$sections['Acceptance Criteria'] ?? '',$blocks,PREG_SET_ORDER);
    foreach ($blocks as $b) {
        $id=strtoupper($b[1]); $body=$b[2];
        if (isset($acs[$id])) $errors[]='Duplicate AC definition: '.$id;
        $acs[$id]=[];
        foreach (['Given','When','Then','Verification'] as $field) {
            if (!preg_match('/^'.preg_quote($field,'/').':[ \t]*(\S[^\r\n]*)$/mi',$body,$value)) $errors[]="{$id} requires non-empty {$field}:";
            else $acs[$id][strtolower($field)]=trim($value[1]);
        }
        if (!preg_match('/^Requirement:[ \t]*(FR-\d{2,}(?:[ \t]*,[ \t]*FR-\d{2,})*)[ \t]*$/mi',$body,$rm)) $errors[]=$id.' needs Requirement: FR-01 mapping.';
        else {
            $refs=preg_split('/[ \t]*,[ \t]*/',strtoupper($rm[1]));
            $acs[$id]['requirements']=$refs;
            foreach ($refs as $ref) { if (!isset($requirements[$ref])) $errors[]="{$id} references undefined {$ref}."; $covered[$ref]=true; }
        }
    }
    if (!$acs) $errors[]='No AC definitions inside Acceptance Criteria (expected ### AC-01).';
    foreach ($requirements as $id=>$unused) if (!isset($covered[$id])) $errors[]='Requirement has no AC: '.$id;
    return ['status'=>$errors ? 'FAIL':'PASS','path'=>relative($path),'sha256'=>hash('sha256',$text),'ac_ids'=>array_keys($acs),'acceptance_criteria'=>$acs,'requirements'=>$requirements,'errors'=>$errors,'limitations'=>['Structural validation does not establish product correctness, stakeholder approval, or executed acceptance tests.']];
}
function decodeReport(string $message): array {
    $message=trim($message);
    if (preg_match('/\A```(?:json)?\s*\R([\s\S]*?)\R```\z/',$message,$m)) $message=$m[1];
    return jsonObject($message);
}
function allowedStatuses(string $role): array {
    return match($role) {
        'product-manager'=>['READY_FOR_ENGINEERING','DRAFT','BLOCKED','NEEDS_INFORMATION'],
        'architect'=>['PROPOSED','BLOCKED'],
        'qa-support'=>['VALID_BUG','NOT_A_BUG','INCONCLUSIVE','BLOCKED','NEEDS_INFORMATION'],
        'developer','hotfix-developer','upgrade-developer'=>['IMPLEMENTED','FAIL','BLOCKED'],
        'incident-investigator'=>['INVESTIGATED','BLOCKED'],
        'mr-review-publisher'=>['PUBLISHED','PUBLISHED_WITH_FALLBACK','ALREADY_PUBLISHED','DRY_RUN','BLOCKED'],
        'engineering-orchestrator'=>['READY_FOR_HUMAN_REVIEW','REVIEW_DELIVERED','BLOCKED','HUMAN_ESCALATION_REQUIRED'],
        default=>['PASS','FAIL','BLOCKED'],
    };
}
function validateReportShape(array $report, string $role): void {
    if (!in_array($report['status'] ?? null, allowedStatuses($role),true)) throw new \RuntimeException('Unknown status for '.$role);
    requireText($report['task_id'] ?? null,'task_id',100);
    requireText($report['summary'] ?? null,'summary');
    if (!isset($report['evidence']) || !is_array($report['evidence']) || !array_is_list($report['evidence'])) throw new \RuntimeException('evidence must be an array.');
    foreach ($report['evidence'] as $e) requireText($e,'evidence entry');
    if (in_array($report['status'],['PASS','IMPLEMENTED','PROPOSED','INVESTIGATED','READY_FOR_ENGINEERING','VALID_BUG'],true) && !$report['evidence']) throw new \RuntimeException('Success requires explicit evidence.');
    requireText($report['handoff'] ?? null,'handoff');
    $findings=$report['findings'] ?? [];
    if (!is_array($findings) || !array_is_list($findings)) throw new \RuntimeException('findings must be an array.');
    foreach ($findings as $f) {
        if (!is_array($f) || !in_array($f['severity'] ?? '',['BLOCKING','WARNING','SUGGESTION','NIT'],true)) throw new \RuntimeException('Invalid finding.');
        foreach (['problem','impact','evidence','location'] as $field) requireText($f[$field] ?? null,'finding.'.$field);
        if (($f['severity'] ?? '')==='BLOCKING' && in_array($report['status'],['PASS','IMPLEMENTED'],true)) throw new \RuntimeException('PASS cannot contain a blocking finding.');
    }
}
