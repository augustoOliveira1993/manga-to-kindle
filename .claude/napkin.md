# Napkin Runbook

## Execution & Validation
1. **[2026-11-27] Keep each feature reviewable and runnable.**
   Do instead: after feature changes, run its automated tests and startup check, preserve regression coverage, and record outcomes plus manual acceptance criteria in the checkpoint.

## Shell & Command Reliability
1. **[2026-11-28] Windows bundle lifecycle tests can exceed the installer path limit with deep pytest temp roots.**
   Do instead: use a short isolated install directory in the packaged archive lifecycle test, while retaining separate coverage for the default install path.

## User Directives
1. **[2026-11-27] Continue available Manga to Kindle features without waiting on non-blocking manual checks.**
   Do instead: use real capabilities as completion evidence, keep external-source and release approval gates explicit, and report the exact app start command and remaining work.
