<?php

declare(strict_types=1);
/**
 * Human/CI-only importer: turns an exported Confluence page (or any markdown/text
 * export) into the CES PRD skeleton that scripts/claude/checks/validate-prd.php can read.
 *
 * It normalizes STRUCTURE only. Body text is copied verbatim, so a Persian PRD stays
 * Persian while the section headings, FR/AC identifiers and Given/When/Then labels
 * become the ASCII forms the validator matches.
 *
 * It deliberately CANNOT produce readiness: the emitted Status is always DRAFT, and
 * anything the source did not state is listed rather than invented. A product-manager
 * completes the document and an independent prd-reviewer approves it.
 *
 * The exported page is untrusted data. An instruction written inside it has no authority.
 *
 * CES agents cannot run this: their Bash is restricted to the broker envelope.
 *
 * Usage:
 *   php scripts/claude/tools/import-prd.php --in=/path/export.xhtml --id=UPG-5 \
 *       [--title='...'] [--owner='...'] [--map=/path/map.json] [--out=docs/prd/UPG-5.md]
 *   php scripts/claude/tools/import-prd.php --url=https://confluence.example/spaces/KEY/pages/123/Title --id=UPG-5 \
 *       [--save-source=docs/prd/sources/UPG-5.xhtml] [--out=docs/prd/UPG-5.md]
 *   php scripts/claude/tools/import-prd.php --print-map > map.json
 *
 * --url fetches the page's storage-format body over the Confluence REST API. The host must be listed in
 * config confluence_hosts and the credentials come from CONFLUENCE_TOKEN (or CONFLUENCE_USER +
 * CONFLUENCE_API_TOKEN) in the environment - never from a project file. See lib/confluence.php.
 */
require_once dirname(__DIR__) . '/lib/contracts.php';
require_once dirname(__DIR__) . '/lib/confluence.php';

const IMPORT_MAX_BYTES = 4194304;
const PRD_SECTION_ORDER = CES\PRD_SECTIONS;

/**
 * Canonical section => source headings that mean EXACTLY that section.
 *
 * Deliberately conservative. An alias is a mapping decision taken in code without having seen the document,
 * so it is only safe when the source heading names one canonical section and nothing else. A heading that is
 * broader ("Metrics & Goals" covers two sections), a different concept that merely often overlaps ("Executive
 * Summary", "Market Opportunity"), a whole document ("BRD"), or a bare generic word ("requirements", "data")
 * is left unrecognised on purpose: its text is preserved under "Unmapped Source Sections" and a product-manager,
 * who can read it, decides where it belongs. A missed mapping costs a manual move; a wrong one silently files
 * the source's meaning under the wrong contract. Teams add their own exact wording with --print-map / --map.
 */
function defaultSectionMap(): array {
    return [
        'Problem Statement'=>['problem statement','problem definition','problem','شرح مسئله','بیان مسئله','صورت مسئله','مسئله','مشکل','تعریف مسئله','توصیف مسئله','توصیف مساله','شرح مساله','بیان مساله','تعریف مساله','مساله'],
        'Context / Evidence'=>['context / evidence','context','evidence','background','supportive data','supporting data','زمینه','شواهد','زمینه و شواهد','پیش زمینه','سابقه','داده های پشتیبان','شواهد و داده ها'],
        'Goals'=>['goals','goal','objectives','business goals','business objectives','اهداف','هدف','اهداف کلی'],
        'Non-Goals'=>['non-goals','non goals','غیر اهداف','اهداف غیر','خارج از اهداف','غیر هدف'],
        'Users / Actors'=>['users / actors','users','actors','personas','user personas','کاربران','بازیگران','نقش ها','کاربران و نقش ها','پرسونا','پرسوناها','کاربران هدف'],
        'Functional Requirements'=>['functional requirements','user stories','user story','نیازمندی های عملکردی','الزامات عملکردی','نیازمندی های کارکردی','یوزر استوری','یوزر استوری ها','داستان کاربر','داستان های کاربر'],
        'Acceptance Criteria'=>['acceptance criteria','acceptance','معیارهای پذیرش','معیار پذیرش','شرایط پذیرش','ضوابط پذیرش'],
        'Failure / Negative Behavior'=>['failure / negative behavior','failure behavior','negative behavior','error handling','رفتار خطا','سناریوهای خطا','حالت های خطا','رفتار منفی','خطاها','مدیریت خطا'],
        'Non-Functional Requirements'=>['non-functional requirements','nfr','nfrs','non functional requirements','quality attributes','نیازمندی های غیرعملکردی','الزامات غیرعملکردی','نیازمندی های غیر کارکردی'],
        'Observability Requirements'=>['observability requirements','observability','monitoring','logging','analytics events','suggested events','event tracking','eventهای پیشنهادی','event های پیشنهادی','events پیشنهادی','پایش','مانیتورینگ','رصدپذیری','نیازمندی های پایش','لاگ ها','ایونت های پیشنهادی'],
        'Dependencies'=>['dependencies','dependency','technical dependencies','requirements from other teams','cross-team requirements','dependencies on other teams','وابستگی ها','پیش نیازها','پیش نیاز','نیازمندی ها از سایر تیم ها','نیازمندی از سایر تیم ها','نیازمندی های بین تیمی','وابستگی به تیم ها'],
        'Rollout / Migration Expectations'=>['rollout / migration expectations','rollout','migration','deployment','timeline & milestones','timeline and milestones','timeline','milestones','phasing','release plan','roadmap','roadmap and iteration','roadmap and iterations','iterations','انتشار','مهاجرت','برنامه انتشار','رول اوت','استقرار','رودمپ','رودمپ و ایتریشن ها','نقشه راه','فازبندی'],
        'Success Metrics'=>['success metrics','metrics','kpi','kpis','key metrics','success criteria','key results','key result','krs','guardrail metrics','guardrails','health metrics','معیارهای موفقیت','شاخص های موفقیت','شاخص ها','نتایج کلیدی','متریک های نگهبان'],
        'Risks'=>['risks','risk','risks and mitigation strategies','risks & mitigation strategies','risks and mitigation','constraints and risks','risks and constraints','constraints & risks','ریسک ها','ریسک','مخاطرات','محدودیت ها و ریسک ها','ریسک ها و محدودیت ها'],
        'Open Questions'=>['open questions','questions','سوالات باز','پرسش های باز','سوالات','ابهامات'],
        'Out of Scope'=>['out of scope','scope exclusions','not in scope','خارج از محدوده','خارج از دامنه','بیرون از محدوده'],
    ];
}

/** Acceptance-criterion label => recognised source labels. */
function defaultLabelMap(): array {
    return [
        'Given'=>['given','فرض','با فرض','فرض کنید','مفروضات','پیش شرط','پیش فرض'],
        'When'=>['when','وقتی','هنگامی که','زمانی که','اقدام','عمل'],
        'Then'=>['then','آنگاه','نتیجه','سپس','انتظار','خروجی مورد انتظار','نتیجه مورد انتظار'],
        'Verification'=>['verification','verify','تایید','روش تایید','اعتبارسنجی','آزمون','تست','روش آزمون'],
        'Requirement'=>['requirement','requirements','نیازمندی','الزام','ملزومات','مرجع نیازمندی'],
    ];
}

$stats=['persian_digits_folded'=>0,'bidi_marks_removed'=>0,'nbsp_normalized'=>0,'label_lines_joined'=>0,'metadata_lines_neutralized'=>0];

function fold(string $s): string {
    global $stats;
    $bidi=["\u{200E}","\u{200F}","\u{061C}","\u{202A}","\u{202B}","\u{202C}","\u{202D}","\u{202E}","\u{2066}","\u{2067}","\u{2068}","\u{2069}","\u{FEFF}"];
    $before=$s; $s=str_replace($bidi,'',$s);
    if ($s!==$before) $stats['bidi_marks_removed']++;
    $before=$s; $s=str_replace(["\u{00A0}","\u{202F}","\u{2007}","\u{2009}"],' ',$s);
    if ($s!==$before) $stats['nbsp_normalized']++;
    // Nothing else: rewriting a Persian comma or dash here would corrupt the body text.
    return str_replace(["\r\n","\r"],["\n","\n"],$s);
}

function foldDigits(string $s): string {
    $fa=["\u{06F0}","\u{06F1}","\u{06F2}","\u{06F3}","\u{06F4}","\u{06F5}","\u{06F6}","\u{06F7}","\u{06F8}","\u{06F9}"];
    $ar=["\u{0660}","\u{0661}","\u{0662}","\u{0663}","\u{0664}","\u{0665}","\u{0666}","\u{0667}","\u{0668}","\u{0669}"];
    $ascii=['0','1','2','3','4','5','6','7','8','9'];
    return str_replace(array_merge($fa,$ar),array_merge($ascii,$ascii),$s);
}

/** ASCII-ify the identifiers only: FR-۰۱ becomes FR-01, body digits stay Persian. */
function foldIdentifiers(string $s): string {
    global $stats;
    return (string)preg_replace_callback('/\b(FR|AC)\s*[-_\x{2013}\x{2014}]?\s*([0-9\x{06F0}-\x{06F9}\x{0660}-\x{0669}]{1,4})/ui',function($m) use (&$stats) {
        $digits=foldDigits($m[2]);
        if ($digits!==$m[2]) $stats['persian_digits_folded']++;
        return strtoupper($m[1]).'-'.str_pad(ltrim($digits,'0')===''?'0':ltrim($digits,'0'),2,'0',STR_PAD_LEFT);
    },$s);
}

/** Normalize a heading or label for lookup: case, Arabic letter forms, ZWNJ, punctuation, numbering. */
function matchKey(string $s): string {
    $s=fold($s);
    $s=str_replace(["\u{200C}","\u{0640}","\u{064B}","\u{064C}","\u{064D}","\u{064E}","\u{064F}","\u{0650}","\u{0651}","\u{0652}"],['',''," "," "," "," "," "," "," "," "],$s);
    $s=str_replace(["\u{064A}","\u{0649}","\u{0643}","\u{06C0}","\u{0629}"],["\u{06CC}","\u{06CC}","\u{06A9}","\u{0647}","\u{0647}"],$s);
    $s=foldDigits($s);
    $s=(string)preg_replace('/^\s*[0-9]+(?:[.\-][0-9]+)*\s*[.):\-]?\s*/u','',$s);
    $s=(string)preg_replace('/[:：.،,;!?؟*_#\x{0640}]+$/u','',$s);
    // Persian spacing varies: ZWNJ, a plain space or nothing between the same two words.
    // Compare with all whitespace removed so the three forms are one key.
    $s=(string)preg_replace('/\s+/u','',$s);
    return mb_strtolower(trim($s),'UTF-8');
}

/** Heading marker: level (1 = top, 7 = a bold-only paragraph) plus the heading text. */
function headingMarker(int $level, string $text): string { return "\x01".$level."\x02".$text."\x01"; }
function headingOf(string $line): ?array { return preg_match('/\A\x01(\d)\x02(.*)\x01\z/us',$line,$m)?[(int)$m[1],trim($m[2])]:null; }

function fail(string $message): never {
    fwrite(STDERR,'import-prd: '.$message."\n");
    exit(2);
}

function options(array $argv): array {
    $out=[];
    foreach (array_slice($argv,1) as $arg) {
        if (!preg_match('/\A--([a-z-]+)(?:=(.*))?\z/s',$arg,$m)) fail('unsupported argument: '.$arg);
        $out[$m[1]]=$m[2] ?? true;
    }
    return $out;
}

/** Read one entry out of a ZIP container without ext-zip. The export is untrusted: bound everything. */
function zipEntry(string $bytes, string $wanted): ?string {
    $eocd=strrpos($bytes,"PK\x05\x06");
    if ($eocd===false) return null;
    $header=unpack('vdisk/vcddisk/ventries/vtotal/Vsize/Voffset',substr($bytes,$eocd+4,16));
    if (!$header || $header['total']>4096) return null;
    $cursor=$header['offset'];
    for ($i=0;$i<$header['total'];$i++) {
        if (substr($bytes,$cursor,4)!=="PK\x01\x02") return null;
        $entry=unpack('vversion/vneeded/vflags/vmethod/vtime/vdate/Vcrc/Vcsize/Vusize/vnamelen/vextralen/vcommentlen/vdisk/vinternal/Vexternal/Vlocal',substr($bytes,$cursor+4,42));
        $name=substr($bytes,$cursor+46,$entry['namelen']);
        $cursor+=46+$entry['namelen']+$entry['extralen']+$entry['commentlen'];
        if ($name!==$wanted) continue;
        if ($entry['usize']>IMPORT_MAX_BYTES*8) return null;
        $local=$entry['local'];
        if (substr($bytes,$local,4)!=="PK\x03\x04") return null;
        $localHeader=unpack('vneeded/vflags/vmethod/vtime/vdate/Vcrc/Vcsize/Vusize/vnamelen/vextralen',substr($bytes,$local+4,26));
        $data=substr($bytes,$local+30+$localHeader['namelen']+$localHeader['extralen'],$entry['csize']);
        if ($entry['method']===0) return $data;
        if ($entry['method']!==8) return null;
        $inflated=@gzinflate($data);
        return $inflated===false?null:$inflated;
    }
    return null;
}

/**
 * Word document.xml to text. Word marks a heading with a Heading/Title style, but plenty of
 * real documents just bold the paragraph, so a short bold non-list paragraph counts too.
 * Table cells become one line each.
 */
function docxRunsText(string $node): string {
    $text='';
    if (preg_match_all('~<w:t\b[^>]*>(.*?)</w:t>~s',$node,$runs,PREG_SET_ORDER)) foreach ($runs as $run) $text.=$run[1];
    return html_entity_decode(str_replace('\t',"\t",$text),ENT_QUOTES|ENT_HTML5,'UTF-8');
}
function docxToText(string $container): string {
    $xml=zipEntry($container,'word/document.xml');
    if ($xml===null) fail('cannot read word/document.xml from this .docx. Re-save it, or export the page as HTML.');
    $xml=(string)preg_replace('~<w:tab\b[^>]*/>~','\t',$xml);
    $xml=(string)preg_replace('~<w:br\b[^>]*/>~',' ',$xml);
    // Tables become markdown rows at the table's own position; their paragraphs are not headings, however
    // bold a header row is, and they are not emitted a second time as loose lines.
    $tables=[]; $segments=[];
    if (preg_match_all('~<w:tbl\b.*?</w:tbl>~s',$xml,$found,PREG_OFFSET_CAPTURE)) foreach ($found[0] as $table) {
        $tables[]=[$table[1],$table[1]+strlen($table[0])];
        $rows=[];
        if (preg_match_all('~<w:tr\b.*?</w:tr>~s',$table[0],$trs)) foreach ($trs[0] as $tr) {
            $cells=[];
            if (preg_match_all('~<w:tc\b.*?</w:tc>~s',$tr,$tcs)) foreach ($tcs[0] as $tc) $cells[]=docxRunsText($tc);
            array_push($rows,...tableRow($cells,$rows===[]));
        }
        if ($rows) $segments[$table[1]]=implode("\n",$rows);
    }
    preg_match_all('~<w:p\b[^>]*>(.*?)</w:p>~s',$xml,$paragraphs,PREG_SET_ORDER|PREG_OFFSET_CAPTURE);
    foreach ($paragraphs as $paragraph) {
        $offset=$paragraph[0][1]; $node=$paragraph[1][0];
        foreach ($tables as $range) if ($offset>=$range[0] && $offset<$range[1]) continue 2;
        $text=trim(docxRunsText($node));
        if ($text==='') continue;
        $isList=str_contains($node,'<w:numPr');
        $style=preg_match('~<w:pStyle w:val="([^"]+)"~',$node,$s)?$s[1]:'';
        $styledHeading=(bool)preg_match('/\A(?:Heading[1-9]|Title|Subtitle)/i',$style);
        $boldHeading=!$isList && mb_strlen($text,'UTF-8')<=90 && (str_contains($node,'<w:b/>') || str_contains($node,'<w:b '));
        if ($styledHeading || $boldHeading) {
            $level=$styledHeading && preg_match('/([1-9])/',$style,$d)?(int)$d[1]:($styledHeading?1:7);
            $segments[$offset]=headingMarker($level,$text);
        } else {
            $indent=$isList && preg_match('~<w:ilvl w:val="(\d+)"~',$node,$lv)?str_repeat('  ',min(6,(int)$lv[1])):'';
            $segments[$offset]=$indent.($isList?'- ':'').$text;
        }
    }
    ksort($segments);
    return implode("\n",$segments);
}

/** One markdown table row from already-plain cell texts; the first row is followed by a separator. */
function tableRow(array $cells, bool $first): array {
    $cells=array_map(fn($c)=>str_replace('|','\\|',trim((string)preg_replace('/\s+/u',' ',$c))),$cells);
    if (array_filter($cells,fn($c)=>$c!=='')===[]) return [];
    $rows=['| '.implode(' | ',$cells).' |'];
    if ($first) $rows[]='|'.str_repeat('---|',count($cells));
    return $rows;
}
/** Cells of a markdown table row (unescaping \| inside a cell). */
function tableCells(string $row): array {
    $inner=trim(trim($row)); $inner=(string)preg_replace('/\A\||\|\z/u','',$inner);
    return array_map(fn($c)=>str_replace('\\|','|',trim($c)),preg_split('/(?<!\\\\)\|/u',$inner) ?: []);
}
function isTableRow(string $line): bool { return (bool)preg_match('/\A\s*\|.*\|\s*\z/u',$line); }
function isTableSeparator(string $line): bool { return (bool)preg_match('/\A\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*\z/u',$line); }

/**
 * An HTML table becomes markdown rows instead of one cell per line. A flattened milestone or risk table
 * is unreadable and, worse, its cells look like stray requirement lines to a reader of the draft.
 * Cell text is re-escaped so the later strip_tags/entity-decode pass restores it byte for byte.
 */
function htmlTableToRows(string $table): string {
    $rows=[];
    if (!preg_match_all('~<tr\b[^>]*>(.*?)</tr>~is',$table,$trs,PREG_SET_ORDER)) return '';
    foreach ($trs as $tr) {
        if (!preg_match_all('~<t([dh])\b[^>]*>(.*?)</t\1>~is',$tr[1],$tds,PREG_SET_ORDER)) continue;
        $cells=[];
        foreach ($tds as $td) {
            $cell=(string)preg_replace('~<br\s*/?>|</p>|</div>|</li>|</h[1-6]>~i',' ',$td[2]);
            $cells[]=htmlspecialchars(html_entity_decode(strip_tags($cell),ENT_QUOTES|ENT_HTML5,'UTF-8'),ENT_NOQUOTES,'UTF-8');
        }
        array_push($rows,...tableRow($cells,$rows===[]));
    }
    return $rows?"\n".implode("\n",$rows)."\n":'';
}

/**
 * Nested HTML lists become indented "- " lines, innermost first, so a sub-bullet keeps its depth instead
 * of being flattened next to its parent. Paragraph tags inside an item are folded into the item's line.
 */
function htmlListsToLines(string $html): string {
    $pattern='~<(ul|ol)\b[^>]*>((?:(?!<(?:ul|ol)\b).)*?)</\1>~is';
    for ($round=0;$round<100 && preg_match($pattern,$html);$round++) {
        $html=(string)preg_replace_callback($pattern,function($m) {
            $items=preg_split('~<li\b[^>]*>~i',$m[2]) ?: []; array_shift($items); $out='';
            foreach ($items as $item) {
                $item=(string)preg_replace('~</li>~i','',$item); $nested='';
                if (preg_match('/\n[ ]*- /',$item,$mm,PREG_OFFSET_CAPTURE)) { $nested=substr($item,$mm[0][1]); $item=substr($item,0,$mm[0][1]); }
                $own=trim((string)preg_replace('/\s+/u',' ',(string)preg_replace('~<br\s*/?>|</?p\b[^>]*>|</?div\b[^>]*>~i',' ',$item)));
                $nested=(string)preg_replace('/\n([ ]*)- /',"\n  $1- ",$nested);
                if ($own==='' && $nested==='') continue;
                $out.="\n- ".$own.$nested;
            }
            return "\n".$out."\n";
        },$html);
    }
    return $html;
}

/**
 * Confluence images, attachments and links carry information - a wireframe's filename, a Figma URL, a linked
 * page's title - that strip_tags deletes without trace. A design or flow section is frequently nothing but
 * these, so they become explicit bracketed references: the fact that the source points at that artefact is
 * preserved, and nothing is invented about what it contains.
 */
function confluenceReferences(string $html): string {
    $target=function(string $node): ?string {
        if (preg_match('~<ri:attachment\b[^>]*ri:filename="([^"]*)"~i',$node,$m)) return 'attachment: '.$m[1];
        if (preg_match('~<ri:url\b[^>]*ri:value="([^"]*)"~i',$node,$m)) return $m[1];
        if (preg_match('~<ri:page\b[^>]*ri:content-title="([^"]*)"~i',$node,$m)) return 'page: '.$m[1];
        if (preg_match('~<ri:space\b[^>]*ri:space-key="([^"]*)"~i',$node,$m)) return 'space: '.$m[1];
        // Confluence stores only an opaque key for a person and resolves the display name when it renders,
        // so the name is genuinely absent from the export. Say that, rather than leaving a bare marker that
        // reads as if a name had been dropped.
        if (preg_match('~<ri:user\b[^>]*ri:(?:userkey|account-id)="([^"]*)"~i',$node,$m)) return 'user mention - Confluence exports no display name; key '.$m[1];
        if (preg_match('~<ri:user\b~i',$node)) return 'user mention - Confluence exports no display name';
        return null;
    };
    $html=(string)preg_replace_callback('~<ac:image\b[^>]*(?:/>|>.*?</ac:image>)~is',function($m) use ($target) {
        $t=$target($m[0]); return ' ['.($t===null?'image':'image - '.$t).'] ';
    },$html);
    $html=(string)preg_replace_callback('~<ac:link\b[^>]*(?:/>|>(.*?)</ac:link>)~is',function($m) use ($target) {
        $body=trim((string)preg_replace('/\s+/u',' ',html_entity_decode(strip_tags($m[1] ?? ''),ENT_QUOTES|ENT_HTML5,'UTF-8')));
        $t=$target($m[0]);
        if ($body!=='' && $t!==null) return ' '.$body.' [link - '.$t.'] ';
        if ($body!=='') return ' '.$body.' ';
        return ' ['.($t===null?'link':'link - '.$t).'] ';
    },$html);
    // A bare resource reference left outside an image or link macro.
    return (string)preg_replace_callback('~<ri:(?:attachment|url|page)\b[^>]*/?>~i',function($m) use ($target) {
        $t=$target($m[0]); return $t===null?'':' ['.$t.'] ';
    },$html);
}

/** Confluence storage format / HTML to text, keeping heading boundaries as \x01 markers. */
function htmlToText(string $html): string {
    $html=(string)preg_replace('~<!--.*?-->~s','',$html);
    $html=(string)preg_replace('~<(script|style)\b[^>]*>.*?</\1>~is','',$html);
    // Confluence storage format: link bodies are CDATA, and a status macro's visible text is its "title"
    // parameter. Every other macro parameter is configuration, not content.
    $html=(string)preg_replace('~<!\[CDATA\[(.*?)\]\]>~s','$1',$html);
    $html=(string)preg_replace('~<ac:parameter\b[^>]*ac:name="title"[^>]*>(.*?)</ac:parameter>~is',' $1 ',$html);
    $html=(string)preg_replace('~<ac:parameter\b[^>]*>.*?</ac:parameter>~is','',$html);
    $html=confluenceReferences($html);
    $html=(string)preg_replace_callback('~<table\b[^>]*>.*?</table>~is',fn($m)=>"\n".htmlTableToRows($m[0])."\n",$html);
    $html=htmlListsToLines($html);
    // A short paragraph that is nothing but bold text is a heading the author did not style as one -
    // typically a requirement group label. Long bold paragraphs are emphasis, not structure.
    $html=(string)preg_replace_callback('~<p\b[^>]*>\s*<(strong|b)\b[^>]*>(.*?)</\1>\s*:?\s*</p>~is',function($m) {
        $text=trim(html_entity_decode(strip_tags($m[2]),ENT_QUOTES|ENT_HTML5,'UTF-8'));
        return $text!=='' && mb_strlen($text,'UTF-8')<=90 && !preg_match('/\A\s*[-*•]\s/u',$text) ? "\n".headingMarker(7,htmlspecialchars($text,ENT_NOQUOTES,'UTF-8'))."\n" : $m[0];
    },$html);
    $html=(string)preg_replace('~<(h[1-6]|ac:rich-text-body|p|div|tr|table|ul|ol)\b[^>]*>~i',"\n<$1>",$html);
    $html=(string)preg_replace_callback('~<h([1-6])\b[^>]*>(.*?)</h\1>~is',fn($m)=>"\n".headingMarker((int)$m[1],strip_tags($m[2]))."\n",$html);
    $html=(string)preg_replace('~<li\b[^>]*>~i',"\n- ",$html);
    $html=(string)preg_replace('~</li>~i','',$html);
    $html=(string)preg_replace('~<br\s*/?>|</p>|</div>|</tr>|</ul>|</ol>|</table>~i',"\n",$html);
    $html=(string)preg_replace('~</t[dh]>~i',"\t",$html);
    $html=strip_tags($html);
    return html_entity_decode($html,ENT_QUOTES|ENT_HTML5,'UTF-8');
}

/** Markdown/plain text: ATX headings and underlined headings become \x01 markers. */
function textToLines(string $text): array {
    // Collapse runs of spaces that extraction leaves between elements, while keeping leading indentation,
    // which is the only whitespace that carries meaning (a nested list item).
    $lines=array_map(fn($l)=>(string)preg_replace('/(?<=\S)[ \t]{2,}/u',' ',$l),explode("\n",$text));
    $out=[];
    foreach ($lines as $i=>$line) {
        $next=$lines[$i+1] ?? '';
        if (preg_match('/\A\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*\z/u',$line,$m)) { $out[]=headingMarker(strlen($m[1]),trim($m[2])); continue; }
        if (trim($line)!=='' && preg_match('/\A\s{0,3}(=|-){3,}\s*\z/',$next) && !str_starts_with(ltrim($line),'- ') && !isTableRow($line)) { $out[]=headingMarker($next[0]==='='?1:2,trim($line)); continue; }
        if (preg_match('/\A\s{0,3}(=|-){3,}\s*\z/',$line) && trim($lines[$i-1] ?? '')!=='' ) continue;
        $out[]=rtrim($line);
    }
    return $out;
}

function lookup(array $map, string $heading): ?string {
    $k=matchKey($heading);
    if ($k==='') return null;
    foreach ($map as $canonical=>$aliases) foreach ($aliases as $alias) if ($k===matchKey($alias)) return $canonical;
    return null;
}
/**
 * Bilingual headings - "توصیف مساله (Problem Definition)" - match on the whole text first, then on the part
 * outside the parentheses, then on each parenthesised part. Exact alias matches only: a heading that
 * merely contains a familiar word is not categorised by guesswork, it is left for the product-manager.
 */
function lookupHeading(array $map, string $heading): ?array {
    $full=lookup($map,$heading);
    if ($full!==null) return [$full,'exact'];
    if (preg_match_all('/[(（]([^()（）]{1,120})[)）]/u',$heading,$inner)) {
        $outside=trim((string)preg_replace('/[(（][^()（）]{1,120}[)）]/u',' ',$heading));
        $o=lookup($map,$outside);
        if ($o!==null) return [$o,'outside parentheses'];
        foreach ($inner[1] as $part) { $i=lookup($map,$part); if ($i!==null) return [$i,'parenthesised "'.trim($part).'"']; }
    }
    return null;
}

/** Collect "Label: value" lines, joining wrapped continuation lines into one line. */
function labelledFields(array $lines, array $labelMap): array {
    global $stats;
    $fields=[]; $current=null;
    foreach ($lines as $line) {
        $h=headingOf($line); $trimmed=trim($h!==null?$h[1]:$line);
        if ($trimmed==='') { $current=null; continue; }
        $matched=null;
        if (preg_match('/\A\s*[-*]?\s*\**\s*([^:：]{1,60})\s*[:：]\s*(.*)\z/u',$trimmed,$m)) {
            $matched=lookup($labelMap,$m[1]);
            if ($matched!==null) { $fields[$matched]=trim($m[2]); $current=$matched; continue; }
        }
        if ($current!==null && $matched===null) {
            $fields[$current]=trim($fields[$current].' '.$trimmed);
            $stats['label_lines_joined']++;
        }
    }
    return $fields;
}

$opt=options($argv);
if (isset($opt['print-map'])) {
    CES\output(['sections'=>defaultSectionMap(),'labels'=>defaultLabelMap()]);
    exit(0);
}
if (!isset($opt['id']) || !is_string($opt['id']) || trim($opt['id'])==='') fail('--id is required. See the header of this file for usage.');
$id=trim($opt['id']);
if (!preg_match('/\A[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\z/',$id)) fail('--id must be a ticket key such as UPG-5 (the CES task_id).');
$hasIn=isset($opt['in']) && is_string($opt['in']) && trim($opt['in'])!==''; $hasUrl=isset($opt['url']) && is_string($opt['url']) && trim($opt['url'])!=='';
if ($hasIn===$hasUrl) fail('pass exactly one of --in=<export file> or --url=<Confluence page URL>.');
$fetched=null;
if ($hasUrl) {
    try { $fetched=CES\fetchConfluencePage(trim($opt['url'])); } catch (Throwable $e) { fail($e->getMessage()); }
    $source=$fetched['source_url']; $raw=$fetched['xhtml'];
    if (isset($opt['save-source'])) {
        if (!is_string($opt['save-source'])) fail('--save-source needs a path.');
        try { $savePath=CES\safePath($opt['save-source']); } catch (Throwable $e) { fail('--save-source rejected: '.$e->getMessage()); }
        if (!preg_match('/\.(?:xhtml|html)\z/i',$savePath) || (!CES\within($savePath,CES\root().'/docs/prd') && !CES\within($savePath,CES\root().'/docs/product'))) fail('--save-source must be an .xhtml/.html path under docs/prd/ or docs/product/.');
        if (!is_dir(dirname($savePath)) && !mkdir(dirname($savePath),0755,true) && !is_dir(dirname($savePath))) fail('cannot create '.dirname($savePath));
        if (file_put_contents($savePath,$raw)===false) fail('cannot write '.$savePath);
    }
} else {
    $source=$opt['in'];
    if (!is_file($source) || !is_readable($source)) fail('cannot read '.$source);
    if (filesize($source)>IMPORT_MAX_BYTES) fail('export exceeds '.IMPORT_MAX_BYTES.' bytes; split it.');
    $raw=(string)file_get_contents($source);
}

$sectionMap=defaultSectionMap(); $labelMap=defaultLabelMap();
if (isset($opt['map'])) {
    if (!is_string($opt['map']) || !is_file($opt['map'])) fail('--map must be a readable JSON file. Start from --print-map.');
    $extra=json_decode((string)file_get_contents($opt['map']),true,64,JSON_THROW_ON_ERROR);
    if (!is_array($extra)) fail('--map must contain a JSON object.');
    foreach (['sections'=>&$sectionMap,'labels'=>&$labelMap] as $group=>&$target) {
        foreach ((array)($extra[$group] ?? []) as $canonical=>$aliases) {
            if (!isset($target[$canonical])) fail('unknown '.$group.' key in --map: '.(string)$canonical);
            if (!is_array($aliases)) fail('--map aliases must be arrays of strings.');
            foreach ($aliases as $alias) { if (!is_string($alias)) fail('--map aliases must be arrays of strings.'); $target[$canonical][]=$alias; }
        }
    }
    unset($target);
}

if (str_starts_with($raw,'%PDF-')) fail('PDF exports scramble right-to-left text in their text layer, so a Persian PRD cannot be recovered from one. Export the page as Word (.docx) or Confluence storage XHTML/HTML instead.');
$isDocx=str_starts_with($raw,"PK\x03\x04") && str_contains($raw,'word/document.xml');
if (!$isDocx && !mb_check_encoding($raw,'UTF-8')) fail('export is not valid UTF-8; re-export it as UTF-8.');
$isHtml=!$isDocx && (bool)preg_match('~<(?:p|div|h[1-6]|li|table|span|ac:)\b~i',$raw);
$format=$isDocx?'docx':($isHtml?'html/confluence-storage':'markdown/text');
$text=$isDocx?docxToText($raw):($isHtml?htmlToText($raw):$raw);
if (!mb_check_encoding($text,'UTF-8')) fail('extracted text is not valid UTF-8.');
$lines=textToLines(fold($text));

function stripNumbering(string $s): string { return trim((string)preg_replace('/^\s*[0-9]+(?:[.\-][0-9]+)*\s*[.):\-]?\s*/u','',$s)); }

// Section collection. A recognised heading (at any depth) opens its canonical section. An unrecognised
// heading that is deeper than the current section's heading is a sub-heading inside it. An unrecognised
// heading at the same depth or shallower starts a source section this importer cannot categorise: its
// text is kept verbatim in a separate bucket for the product-manager to place, never merged into the
// previous section where it would read as that section's content. Text before the first recognised
// section (author, status and link tables) goes to the same bucket as the document preamble.
const PREAMBLE_LABEL='(document preamble)';
$sections=[]; $unmapped=[]; $matches=[]; $bucket=[]; $current=null; $currentLevel=0; $inBucket=false; $bucketLevel=0; $docTitle=null;
// Every unrecognised heading records where its content ended up, so a reader never has to guess whether a
// missing heading means lost text or an empty source section.
$note=function(string $heading,int $level,string $keptAs) use (&$unmapped): int { $unmapped[]=['heading'=>$heading,'level'=>$level,'kept_as'=>$keptAs]; return array_key_last($unmapped); };
$openBucket=function(string $heading,int $level,int $entry) use (&$bucket,&$inBucket,&$bucketLevel) { $bucket[]=['heading'=>$heading,'lines'=>[],'entry'=>$entry]; $inBucket=true; $bucketLevel=$level; };
foreach ($lines as $line) {
    $h=headingOf($line);
    if ($h!==null) {
        [$level,$heading]=$h;
        $found=lookupHeading($sectionMap,$heading);
        if ($found!==null) {
            [$canonical,$via]=$found;
            // A heading that names the section we are already in ("Goal" under "Metrics & Goals") is a
            // sub-heading of it: keep its label, keep the section's depth, so its siblings stay inside too.
            if ($canonical===$current && !$inBucket) {
                $sections[$current]['lines'][]=$line; $sections[$current]['headings'][]=$heading;
                $matches[]=['heading'=>$heading,'section'=>$canonical,'via'=>$via.' (sub-heading kept inside the section)'];
                continue;
            }
            $current=$canonical; $currentLevel=$level; $inBucket=false;
            $sections[$canonical]['headings'][]=$heading;
            $sections[$canonical]['lines'] ??= [];
            $matches[]=['heading'=>$heading,'section'=>$canonical,'via'=>$via];
            continue;
        }
        if ($heading==='') continue;
        // The first heading before any recognised section is the document's own title.
        if ($current===null && $docTitle===null && !$inBucket) { $docTitle=$heading; continue; }
        if ($inBucket && $level>$bucketLevel) { $note($heading,$level,'sub-heading of the unmapped source section "'.$bucket[array_key_last($bucket)]['heading'].'"'); $bucket[array_key_last($bucket)]['lines'][]=$line; continue; }
        if ($current===null || $level<=$currentLevel || $inBucket) { $openBucket($heading,$level,$note($heading,$level,'its own entry under Unmapped Source Sections')); continue; }
        // Each AC block's own heading is consumed by the AC parser, and a heading inside the requirements
        // section is a group label kept above its requirements; neither is an unmapped heading.
        if (in_array($current,['Acceptance Criteria','Functional Requirements'],true)) { $sections[$current]['lines'][]=$line; continue; }
        // A sub-heading of a recognised section belongs to that section, so it is written even when the
        // source left its body empty. Dropping it silently lost real content - the names of the roadmap's
        // iterations, or the label grouping a list of problems - and reported the section as empty instead.
        $note($heading,$level,'sub-heading kept inside '.$current);
        $sections[$current]['lines'][]=$line;
        continue;
    }
    if ($inBucket) { $bucket[array_key_last($bucket)]['lines'][]=$line; continue; }
    if ($current===null) { if (trim($line)==='') continue; if (!$bucket || $bucket[array_key_last($bucket)]['heading']!==PREAMBLE_LABEL) $bucket[]=['heading'=>PREAMBLE_LABEL,'lines'=>[]]; $bucket[array_key_last($bucket)]['lines'][]=$line; continue; }
    $sections[$current]['lines'][]=$line;
}
// Keep every unrecognised section that carries anything at all - sub-headings included, since a design or
// flow chapter is often only structure plus image references. A heading with literally nothing under it is
// an empty source section, not lost text: the report and Open Questions both say so.
$emptySections=[];
foreach ($bucket as $index=>$entry) {
    if (array_filter($entry['lines'],fn($l)=>trim($l)!=='')!==[]) continue;
    $unmapped[$entry['entry']]['kept_as']='empty in the source; nothing was imported from it';
    $emptySections[]=$entry['heading']; unset($bucket[$index]);
}
$bucket=array_values($bucket);

$unresolved=[];
$body=function(string $canonical) use ($sections): array { return $sections[$canonical]['lines'] ?? []; };
$plain=function(array $lines) use (&$stats): string {
    $rendered=[]; $afterLabel=false;
    foreach ($lines as $line) {
        // A label is followed directly by its content; the blank line a converter left between them is noise.
        if ($afterLabel && trim($line)==='') continue;
        $afterLabel=false;
        if (($h=headingOf($line))!==null) { $line='**'.$h[1].'**'; $afterLabel=true; }
        // Indentation is meaningful only on a list item (a nested sub-bullet); elsewhere it is extraction noise.
        elseif (!preg_match('/\A\s*[-*•]\s/u',$line)) $line=ltrim($line);
        // A Status:/Owner: line copied from the source would be parsed as this PRD's own
        // metadata. Quote it so only the metadata this script emits can be read as metadata.
        if (preg_match('/\A\s*(?:Status|Owner)\s*[:：]/ui',$line)) { $line='> '.ltrim($line); $stats['metadata_lines_neutralized']++; }
        $rendered[]=$line;
    }
    $text=trim(implode("\n",$rendered));
    return (string)preg_replace("/\n{3,}/","\n\n",$text);
};

// Functional requirements: keep the source wording, force ASCII FR-NN identifiers.
$requirements=[]; $idAliases=[]; $groups=[];
$frLines=$body('Functional Requirements');
// A grouped list ("Authentication", then its bullets) is common. Bullets and numbered items are
// requirements - a nested sub-bullet becomes its own requirement, in order, under the same group -
// while a group label or an introductory sentence is kept as context above them, never dropped.
$isItem=fn(string $l)=>preg_match('/\A\s*(?:[-*•]|[0-9]{1,3}[-.)])\s/u',$l)===1;
$isNested=fn(string $l)=>preg_match('/\A[ \t]+(?:[-*•]|[0-9]{1,3}[-.)])\s/u',$l)===1;
$bulleted=array_filter($frLines,$isItem);
$addContext=function(string $text,bool $heading) use (&$groups,&$requirements) { $groups[count($requirements)][]=['text'=>$text,'heading'=>$heading]; };
// A sub-bullet is detail of the requirement above it, not a requirement of its own. It is kept verbatim,
// indented, under that FR line; the validator reads only the top-level - FR-xx lines.
$subLines=[];
$frColumn=null; $frHeaderKeys=['requirement','requirements','functional requirement','description','feature','title','شرح','توضیح','توضیحات','نیازمندی','الزام','قابلیت','عنوان','شرح نیازمندی'];
foreach ($frLines as $line) {
    if (($h=headingOf($line))!==null) { $addContext($h[1],true); $frColumn=null; continue; }
    if (isTableRow($line)) {
        // A requirements table: one requirement per data row, taken from the column whose header names the
        // requirement (or the longest cell when no header does). Priority/owner columns are not requirements.
        if (isTableSeparator($line)) continue;
        $cells=tableCells($line);
        if ($frColumn===null) {
            $frColumn=-1;
            foreach ($cells as $i=>$cell) if (in_array(matchKey($cell),array_map('matchKey',$frHeaderKeys),true)) { $frColumn=$i; break; }
            if ($frColumn>=0) continue; // header row consumed
        }
        $text=$frColumn>=0?($cells[$frColumn] ?? ''):'';
        if ($text==='') { foreach ($cells as $cell) if (mb_strlen($cell,'UTF-8')>mb_strlen($text,'UTF-8')) $text=$cell; }
        $idCell=null; foreach ($cells as $cell) if (preg_match('/\A\**\s*FR\s*[-_]?\s*[0-9\x{06F0}-\x{06F9}\x{0660}-\x{0669}]{1,4}\s*\**\z/ui',$cell)) { $idCell=foldIdentifiers($cell); break; }
        $text=trim(foldIdentifiers($text));
        if ($text==='' || $text===$idCell) continue;
        $canonicalId=sprintf('FR-%02d',count($requirements)+1);
        if ($idCell!==null && preg_match('/(FR-[0-9]{2,})/',$idCell,$im)) $idAliases[strtoupper($im[1])]=$canonicalId;
        $requirements[$canonicalId]=$text;
        continue;
    }
    if ($bulleted && !$isItem($line)) { if (trim($line)!=='') $addContext(trim($line),false); continue; }
    if ($isNested($line) && $requirements) { $subLines[array_key_last($requirements)][]=rtrim($line); continue; }
    $text=trim(preg_replace('/\A\s*(?:[-*•]|[0-9]{1,3}[-.)])\s*/u','',$line) ?? '');
    if ($text==='') continue;
    $text=foldIdentifiers($text);
    if (preg_match('/\A\**\s*(FR-[0-9]{2,})\s*\**\s*[:：-]\s*(.+)\z/u',$text,$m)) {
        $canonicalId=sprintf('FR-%02d',count($requirements)+1);
        $idAliases[strtoupper($m[1])]=$canonicalId;
        $requirements[$canonicalId]=trim($m[2]);
        continue;
    }
    $requirements[sprintf('FR-%02d',count($requirements)+1)]=$text;
}

// Acceptance criteria: one block per source heading or per AC-xx line.
$criteria=[]; $blocks=[]; $open=-1; $acTableHeader=null;
foreach ($body('Acceptance Criteria') as $line) {
    if (isTableRow($line)) {
        // Product managers often write acceptance criteria as a table whose columns are Given/When/Then
        // (or their Persian equivalents). Each data row is then one criterion; a column that matches no
        // label is its title. A table whose header matches fewer than two labels is kept verbatim.
        if (isTableSeparator($line)) continue;
        $cells=tableCells($line);
        if ($acTableHeader===null) {
            $labels=[]; $titleColumn=null;
            foreach ($cells as $i=>$cell) { $l=lookup($labelMap,$cell); if ($l!==null) $labels[$i]=$l; elseif ($titleColumn===null) $titleColumn=$i; }
            $acTableHeader=count($labels)>=2?['labels'=>$labels,'title'=>$titleColumn]:false;
            if ($acTableHeader!==false) continue;
        }
        if ($acTableHeader!==false) {
            $fields=[]; foreach ($acTableHeader['labels'] as $i=>$label) if (trim($cells[$i] ?? '')!=='') $fields[$label]=trim($cells[$i]);
            $title=$acTableHeader['title']!==null?trim($cells[$acTableHeader['title']] ?? ''):'';
            if ($fields) $blocks[]=['title'=>$title,'lines'=>[],'fields'=>$fields];
            $open=-1; continue;
        }
    } else $acTableHeader=null;
    $h=headingOf($line); $isHeading=$h!==null; $bare=trim($isHeading?$h[1]:$line);
    $looksLikeId=(bool)preg_match('/\A\**\s*(?:AC|ac)\s*[-_]?\s*[0-9\x{06F0}-\x{06F9}\x{0660}-\x{0669}]{1,4}\b/u',$bare);
    if (($isHeading || $looksLikeId) && $bare!=='') { $blocks[]=['title'=>$bare,'lines'=>[]]; $open=count($blocks)-1; continue; }
    if ($open>=0) $blocks[$open]['lines'][]=$line;
}
foreach ($blocks as $index=>$block) {
    $acId=sprintf('AC-%02d',$index+1);
    $title=trim(preg_replace('/\A\**\s*(?:AC|ac)\s*[-_]?\s*[0-9\x{06F0}-\x{06F9}\x{0660}-\x{0669}]{1,4}\s*[:：.\-]?\s*/u','',foldIdentifiers($block['title'])) ?? '');
    $fields=$block['fields'] ?? labelledFields($block['lines'],$labelMap);
    $entry=['title'=>$title!==''?$title:$acId];
    foreach (['Given','When','Then','Verification'] as $label) {
        if (isset($fields[$label]) && $fields[$label]!=='') $entry[$label]=$fields[$label];
        else $unresolved[]=$acId.': the source states no '.$label.' value. The accountable human must supply it; do not infer one.';
    }
    if (isset($fields['Requirement'])) {
        $refs=[];
        foreach (preg_split('/\s*[,\x{060C}\x{061B};]\s*/u',foldIdentifiers($fields['Requirement'])) as $ref) {
            if (!preg_match('/(FR-[0-9]{2,})/u',$ref,$m)) continue;
            $refId=strtoupper($m[1]);
            $refs[]=$idAliases[$refId] ?? $refId;
        }
        $refs=array_values(array_unique(array_filter($refs,fn($r)=>isset($requirements[$r]))));
        if ($refs) $entry['Requirement']=implode(', ',$refs);
        else $unresolved[]=$acId.': its requirement reference does not match any imported FR. Map it to the FR the source text refers to, or ask the accountable human.';
    } else $unresolved[]=$acId.': the source maps it to no requirement. Map it to the FR its own wording refers to when that is evident; otherwise the accountable human decides.';
    $criteria[$acId]=$entry;
}

$missing=[];
foreach (PRD_SECTION_ORDER as $canonical) if (trim($plain($body($canonical)))==='' ) $missing[]=$canonical;
// Each empty section is a decision the source did not record. Listing it here, not only in the stderr
// report, makes the draft itself the complete worklist for the product-manager.
foreach ($missing as $canonical) if (!in_array($canonical,['Functional Requirements','Acceptance Criteria','Open Questions'],true)) $unresolved[]="Section '{$canonical}' is empty in the source. The accountable human must supply it or state that it does not apply; it is not to be filled in on their behalf.";
foreach ($emptySections as $heading) $unresolved[]="Source section '{$heading}' is empty in the source - it has a heading and no content, so nothing was imported from it. Confirm with the accountable human whether it was left unwritten.";
foreach ($bucket as $entry) $unresolved[]="Source section '{$entry['heading']}' was not recognised. Its text is kept verbatim under 'Unmapped Source Sections': move it, unchanged, into the section it belongs to (or extend --map), then delete that section. Readiness is refused while it exists.";
if (!$requirements) $unresolved[]='No functional requirements were recognised in the source. If the source states requirements elsewhere, move them here as - FR-01: ... lines in their own words; otherwise the accountable human must write them.';
if (!$criteria) $unresolved[]='No acceptance criteria were recognised in the source. If the source states them elsewhere, move them here as ### AC-01 blocks; otherwise the accountable human must write them - they are not to be inferred from the requirements.';
if ($criteria) {
    foreach ($requirements as $frId=>$unusedText) {
        $covered=false;
        foreach ($criteria as $entry) if (isset($entry['Requirement']) && in_array($frId,array_map('trim',explode(',',$entry['Requirement'])),true)) $covered=true;
        if (!$covered) $unresolved[]=$frId.' has no acceptance criterion in the source. The accountable human must state one; it is not to be inferred.';
    }
} elseif ($requirements) {
    $unresolved[]='None of the '.count($requirements).' imported requirements has an acceptance criterion in the source. The accountable human must state one observable outcome with a named automated verification for each; they are not to be inferred.';
}

$title=isset($opt['title']) && is_string($opt['title']) && trim($opt['title'])!=='' ? trim($opt['title']) : ($docTitle!==null?stripNumbering($docTitle):'');
if ($title==='') { $title='imported product contract'; $unresolved[]='Title was not found in the source (it began directly with a section heading). Pass --title or edit the first line.'; }
$owner=isset($opt['owner']) && is_string($opt['owner']) ? trim($opt['owner']) : '';
if ($owner==='') $unresolved[]='Owner is not set. The accountable human must be named with --owner or by editing the Owner line; never invent one.';

$md='# '.$id.' - '.$title."\n\n";
$md.="Status: DRAFT\n";
$md.='Owner: '.$owner."\n\n";
$md.="<!--\nImported by scripts/claude/tools/import-prd.php from an exported page. Structure only: the body text is\nthe source's own wording. Status is DRAFT by design - a product-manager completes this document and an\nindependent prd-reviewer approves it. Nothing here establishes product correctness or stakeholder approval.\n-->\n\n";
foreach (PRD_SECTION_ORDER as $canonical) {
    $md.='## '.$canonical."\n";
    if ($canonical==='Functional Requirements') {
        $position=0;
        $renderContext=function(int $at) use (&$md,$groups) {
            foreach ($groups[$at] ?? [] as $entry) $md.=($entry['heading']?'**'.$entry['text'].'**':$entry['text'])."\n";
        };
        foreach ($requirements as $frId=>$text) {
            if (isset($groups[$position])) { if ($position) $md.="\n"; $renderContext($position); }
            $md.='- '.$frId.': '.$text."\n";
            foreach ($subLines[$frId] ?? [] as $sub) $md.=$sub."\n";
            $position++;
        }
        if (isset($groups[$position])) { $md.="\n"; $renderContext($position); }
        if (!$requirements) $md.="\n";
        $md.="\n"; continue;
    }
    if ($canonical==='Acceptance Criteria') {
        foreach ($criteria as $acId=>$entry) {
            $md.='### '.$acId.': '.$entry['title']."\n";
            foreach (['Given','When','Then','Verification','Requirement'] as $label) if (isset($entry[$label])) $md.=$label.': '.$entry[$label]."\n";
            $md.="\n";
        }
        if (!$criteria) $md.="\n";
        continue;
    }
    if ($canonical==='Open Questions') {
        $sourceQuestions=$plain($body($canonical));
        if ($unresolved || $sourceQuestions!=='') {
            if ($sourceQuestions!=='') $md.=$sourceQuestions."\n";
            foreach ($unresolved as $item) $md.='- '.$item."\n";
            $md.="\nEvery line above is a gap in the source, not a task for the converter: resolve each with the accountable human, then set Status: READY_FOR_ENGINEERING.\n";
        } else $md.="None\n";
        $md.="\n"; continue;
    }
    $text=$plain($body($canonical));
    $md.=($text===''?'':$text."\n")."\n";
}
if ($bucket) {
    $md.="## Unmapped Source Sections\n";
    $md.="<!--\nThe importer could not categorise these source sections. Their text is verbatim. A product-manager moves each one,\nunchanged, into the section it belongs to (or teaches the mapping with --map), then deletes this section.\nvalidate-prd.php refuses readiness while it exists.\n-->\n";
    foreach ($bucket as $entry) {
        $md.="\n**".$entry['heading']."**\n";
        $text=$plain($entry['lines']);
        if ($text!=='') $md.=$text."\n";
    }
    $md.="\n";
}

$destination='stdout';
if (isset($opt['out'])) {
    if (!is_string($opt['out'])) fail('--out needs a path.');
    try { $target=CES\safePath($opt['out']); } catch (Throwable $e) { fail('--out rejected: '.$e->getMessage()); }
    if (!str_ends_with($target,'.md')) fail('--out must be a .md path.');
    if (!CES\within($target,CES\root().'/docs/prd') && !CES\within($target,CES\root().'/docs/product')) fail('--out must be under docs/prd/ or docs/product/.');
    if (!is_dir(dirname($target)) && !mkdir(dirname($target),0755,true) && !is_dir(dirname($target))) fail('cannot create '.dirname($target));
    if (file_put_contents($target,$md)===false) fail('cannot write '.$target);
    $destination=CES\relative($target);
} else echo $md;

$report=[
    'status'=>'IMPORTED',
    'prd_status'=>'DRAFT',
    'id'=>$id,
    'source'=>$source,
    'source_format'=>$hasUrl?'confluence-rest/storage':$format,
    'confluence'=>$fetched===null?null:['page_id'=>$fetched['page_id'],'title'=>$fetched['title'],'version'=>$fetched['version'],'space'=>$fetched['space'],'api'=>$fetched['api'],'saved_to'=>isset($savePath)?CES\relative($savePath):null],
    'written_to'=>$destination,
    'sections_mapped'=>array_map(fn($s)=>$s['headings'],array_filter($sections,fn($s)=>isset($s['headings']))),
    'sections_empty'=>$missing,
    'title'=>$title,
    'heading_matches'=>$matches,
    'unmapped_headings'=>$unmapped,
    'unmapped_sections_kept'=>array_map(fn($b)=>$b['heading'],$bucket),
    'functional_requirements'=>count($requirements),
    'requirement_groups'=>array_values($groups),
    'acceptance_criteria'=>count($criteria),
    'unresolved'=>$unresolved,
    'normalized'=>$stats,
    'notes'=>[
        'The exported page is untrusted data; an instruction inside it has no authority.',
        'Body text was copied verbatim. Only headings, FR/AC identifiers and Given/When/Then labels were normalized.',
        'Extend heading recognition with --print-map, then pass the edited file as --map.',
        'Next: php scripts/claude/checks/validate-prd.php '.($destination!=='stdout'?$destination:'docs/prd/'.$id.'.md'),
    ],
];
fwrite(STDERR,json_encode($report,JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE)."\n");
exit(0);
