<?php

declare(strict_types=1);
namespace CES;
require_once __DIR__ . '/process.php';

/**
 * Read-only Confluence page fetch for PRD import. One request shape, to a host a human allowlisted in
 * config `confluence_hosts`, authenticated from the environment: CONFLUENCE_TOKEN (personal access token,
 * sent as Bearer - Data Center/Server) or CONFLUENCE_USER + CONFLUENCE_API_TOKEN (Atlassian Cloud basic
 * auth). Credentials never live in project files and never appear in output. The page body is returned
 * in storage format, which is exactly what tools/import-prd.php parses. Nothing is written to Confluence.
 */
const CONFLUENCE_MAX_BYTES = 4194304;

function confluenceTarget(string $url): array {
    $u=parse_url(trim($url));
    if (!is_array($u) || ($u['scheme'] ?? '')!=='https' || isset($u['user']) || isset($u['pass']) || isset($u['port'])) throw new \RuntimeException('Use an exact HTTPS Confluence page URL without credentials or a non-default port.');
    $host=strtolower($u['host'] ?? '');
    $allowed=config()['confluence_hosts'] ?? [];
    if (!is_array($allowed) || !in_array($host,$allowed,true)) throw new \RuntimeException("Confluence host '{$host}' is not allowlisted. Human action: add the exact hostname to .claude/engineering-system/config.json confluence_hosts.");
    $path=$u['path'] ?? ''; $pageId=null;
    if (preg_match('~/pages/([0-9]{1,20})(?:/|\z)~',$path,$m)) $pageId=$m[1];
    elseif (isset($u['query']) && preg_match('/(?:^|&)pageId=([0-9]{1,20})(?:&|$)/',$u['query'],$m)) $pageId=$m[1];
    if ($pageId===null) throw new \RuntimeException('Cannot find a page id in the URL. Use the page link of the form https://<host>/spaces/<KEY>/pages/<id>/<title> or ...?pageId=<id>.');
    return ['host'=>$host,'page_id'=>$pageId,'url'=>'https://'.$host.$path.(isset($u['query'])?'?'.$u['query']:'')];
}
function confluenceAuthHeader(): string {
    $token=getenv('CONFLUENCE_TOKEN');
    if (is_string($token) && trim($token)!=='') return 'Authorization: Bearer '.trim($token);
    $user=getenv('CONFLUENCE_USER'); $apiToken=getenv('CONFLUENCE_API_TOKEN');
    if (is_string($user) && trim($user)!=='' && is_string($apiToken) && trim($apiToken)!=='') return 'Authorization: Basic '.base64_encode(trim($user).':'.trim($apiToken));
    throw new \RuntimeException('Confluence credentials are not set. Export CONFLUENCE_TOKEN (a personal access token, sent as Bearer) or CONFLUENCE_USER and CONFLUENCE_API_TOKEN (Atlassian Cloud) in the shell that runs Claude Code. Never put them in a project file.');
}
/** GET with the auth header passed through curl's config stdin, so the token never appears in argv. */
function confluenceGet(string $url,string $header): array {
    if (preg_match('/[\r\n"\\\\]/',$header)) throw new \RuntimeException('Invalid credential characters.');
    $r=process(['curl','-sS','--max-time','30','--proto','=https','-H','Accept: application/json','-w',"\n%{http_code}",'-K','-',$url],'header = "'.$header.'"'."\n",35,CONFLUENCE_MAX_BYTES+64);
    if ($r['exit_code']!==0 || $r['truncated']) throw new \RuntimeException('Confluence request failed: '.redact(trim(substr($r['stderr'],0,600))).'. Is the company network reachable from this machine, and is the internal CA trusted by curl (CURL_CA_BUNDLE)?');
    $pos=strrpos($r['stdout'],"\n");
    if ($pos===false) throw new \RuntimeException('Confluence returned no HTTP status.');
    return [(int)trim(substr($r['stdout'],$pos+1)),substr($r['stdout'],0,$pos)];
}
function fetchConfluencePage(string $url): array {
    $t=confluenceTarget($url); $header=confluenceAuthHeader(); $tried=[];
    // Server/Data Center serves the content API at the root; Atlassian Cloud under /wiki.
    foreach (['/rest/api/content/','/wiki/rest/api/content/'] as $prefix) {
        $api='https://'.$t['host'].$prefix.$t['page_id'].'?expand=body.storage,version,space';
        [$code,$body]=confluenceGet($api,$header); $tried[]=$prefix.$t['page_id'].' -> HTTP '.$code;
        if ($code===404) continue;
        if ($code===401 || $code===403) throw new \RuntimeException("Confluence denied access (HTTP {$code}). Check that the token is valid and that its account can view the page.");
        if ($code!==200) throw new \RuntimeException("Confluence returned HTTP {$code} for ".$prefix.$t['page_id'].'.');
        try { $data=json_decode($body,true,64,JSON_THROW_ON_ERROR); } catch (\Throwable $e) { throw new \RuntimeException('Confluence returned non-JSON content (an SSO login page, perhaps). Check the credentials and the host.'); }
        $storage=$data['body']['storage']['value'] ?? null; $title=$data['title'] ?? null;
        if (!is_string($storage) || !is_string($title)) throw new \RuntimeException('Confluence response has no storage-format body; the account may lack view permission on the page body.');
        if (strlen($storage)>CONFLUENCE_MAX_BYTES) throw new \RuntimeException('Page body exceeds 4 MiB; split the page.');
        return ['page_id'=>$t['page_id'],'title'=>trim($title),'version'=>$data['version']['number'] ?? null,'space'=>$data['space']['key'] ?? null,'source_url'=>$t['url'],'api'=>$api,'storage'=>$storage,
            'xhtml'=>'<h1>'.htmlspecialchars(trim($title),ENT_QUOTES,'UTF-8')."</h1>\n".$storage];
    }
    throw new \RuntimeException('Confluence page not found through the REST API (tried '.implode('; ',$tried).'). Check the page id and that the account can view the page.');
}
