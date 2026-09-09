<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/mr.php';
// Human/CI entry point. Agents must use the constrained broker instead.
try {
    $args=array_slice($argv,1);
    if (array_diff($args,['--dry-run'])) throw new RuntimeException('Usage: publish-review.php [--dry-run] < review.json');
    $r=CES\publishReview(CES\jsonObject((string)stream_get_contents(STDIN)),in_array('--dry-run',$args,true));
    CES\output($r); exit($r['status']==='BLOCKED'?2:0);
} catch (Throwable $e) { CES\output(['status'=>'BLOCKED','errors'=>[$e->getMessage()]]); exit(2); }
