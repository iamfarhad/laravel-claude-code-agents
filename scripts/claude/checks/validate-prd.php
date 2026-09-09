<?php

declare(strict_types=1);
require_once dirname(__DIR__) . '/lib/contracts.php';
try { $r=CES\validatePrd($argv[1] ?? ''); CES\output($r); exit($r['status']==='PASS'?0:2); }
catch (Throwable $e) { CES\output(['status'=>'FAIL','errors'=>[$e->getMessage()]]); exit(2); }
