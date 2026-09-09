<?php

declare(strict_types=1);
// Compatibility path only. The v3 installer replaces legacy hook registrations.
// Fail closed rather than retaining any of the v2 regex guards.
fwrite(STDERR, "Legacy CES hook detected. Run the v3 installer with --replace-existing and restart Claude Code.\n");
exit(2);
