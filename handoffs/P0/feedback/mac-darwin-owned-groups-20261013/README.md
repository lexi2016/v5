# One finite Mac process-group diagnostic

Requested after Mac 5eddebf acceptance failure bdef77. One run only, existing HK02 Python, 2026-10-13T04:18:32–04:18:33Z, exit0. No product change, suite rerun, model, collection, service or old-PID signal. Each synthetic role has a maximum five-second lifetime; all three sessions were newly spawned by this script.

Actual results after waitid(P_PID, leader, WEXITED|WNOWAIT|WNOHANG), before final wait:

| Scenario | waitid | getpgid / getsid | ps group | killpg(group,SIGTERM) | final wait |
|---|---|---|---|---|---|
| live leader | no exited child | both return owned group/session | leader Ss + child S + grandchild S | succeeds | -15 |
| exited leader + live descendants | exited status0 | both ProcessLookupError errno3 ESRCH | leader Z + child S + grandchild S in same original group | succeeds | 0 |
| zombie only | exited status0 | both ProcessLookupError errno3 ESRCH | owned leader Z in original group | PermissionError errno1 EPERM | 0 |

Every group was empty after final wait. Ownership gate used the current invocation's new-session Popen PID, pre-exit role identity records (PID/PPID/PGID/SID), unreaped waitid identity, and ps members restricted to those known role PIDs. No signal when the gate is unconfirmed. No poll/wait reaped the leader before these observations. Detailed script/log attached, with private roots/interpreter path replaced in logged commands.

This reproduces zombie ESRCH despite ps membership and distinguishes a still-live owned group (signal succeeds) from a zombie-only group (EPERM in this run). It does not authorize treating every EPERM as harmless, signal arbitrary groups, or claim SIGKILL behaved identically: this diagnostic deliberately used SIGTERM. The original guard should preserve uncertainty and always perform safe bounded wait/reaping; correction remains with its author.
