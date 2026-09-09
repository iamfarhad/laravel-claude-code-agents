<?php
// Controlled offline runner fixture, not a Laravel/application test suite.
$mode=$argv[1] ?? 'pass';
if ($mode==='fail') { fwrite(STDERR,"Assertion fixture failed\n"); exit(1); }
if ($mode==='timeout') { sleep(3); exit(0); }
if ($mode==='mutate') file_put_contents('fixture-mutated.txt','Changed by controlled fixture');
if ($mode==='noisy') { for ($i=0;$i<3000;$i++) { fwrite(STDOUT,str_repeat('o',100)); fwrite(STDERR,str_repeat('e',100)); } }
if ($mode==='env') { echo json_encode(['APP_ENV'=>getenv('APP_ENV'),'SECRET'=>getenv('CES_TEST_SECRET')]); exit(0); }
echo "Controlled fixture assertion executed\n";
