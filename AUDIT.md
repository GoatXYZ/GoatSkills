# Private backup audit — October 29, 2026

Decision: retain private visibility. This backup was reviewed for embedded credentials; it was not sanitized for public redistribution.

## Scope and results

- Reviewed both original commits, all four original files, the sole remote branch, commit metadata, and repository metadata. The original history passed Gitleaks 8.30.1 without exceptions. Authors use a GitHub noreply email address; the existing author display name remains in history.
- Reviewed the 15 personal skill folders, including helpers, references, examples, text assets, and the five JPEG preview images. Checked for credential patterns, personal absolute paths, internal network addresses, email addresses, links, and project-specific material. No live credential was identified. A secret scan cannot prove that every possible credential is absent.
- Gitleaks flagged the signing conformance key in `pls/scripts/noise_sig.py`. Base64url decoding produces the predictable bytes 0 through 31. The scanner exception requires both that exact value and that file path; other keys in the same file remain subject to detection.
- Copied personal skill files are unchanged from the installed versions, with SHA-256 checksums in the personal inventory. Excluded three compiled Python cache files. No credential stores, environment files, account configuration, session history, or provider-managed skill content were imported.
- The secret-check self-test verifies that the deterministic vector passes at its intended path, the same value fails elsewhere, a different credential fails in the same file, and a deleted credential is still detected in history. Copied upstream assets retain their original line endings and whitespace to preserve exact backup checksums; newly authored files pass the whitespace check.

## Details retained because this is a private backup

The `pls` skill documents its service hostname, environment variable names, Keychain lookup identifiers, and local credential-file locations. These are references to credentials, not credential values; the helper still needs separately supplied credentials at runtime. This audit did not read those credential stores or execute publishing commands.

The `bento` examples retain project branding, activity counts, feature-request text, issue references, and mock game and flight displays. Some example data is described as illustrative by the source skill. These assets and the project-specific workflow notes should receive a separate privacy review before any future public release.

## Repeat before pushing changes

Run `scripts/check-secrets` with Gitleaks installed, then review the diff for confidential context and inspect any new binary assets manually. Keep scan reports outside the repository. The script checks locally available history; fetch other remote refs before relying on it for a complete history review.
