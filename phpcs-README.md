# PHPCS for drafting-central-portal

Live PHP is 8.1.34. `php -l` only checks syntax. This also checks PHP 8.1 compatibility and WordPress rules.

## Install (once, outside the plugin folder)

    composer global config allow-plugins.dealerdirect/phpcodesniffer-composer-installer true
    composer global require --dev wp-coding-standards/wpcs phpcompatibility/phpcompatibility-wp dealerdirect/phpcodesniffer-composer-installer

## Run (from the repo root)

    phpcs --standard=phpcs.xml.dist
    phpcs --standard=phpcs.xml.dist --report=summary
    phpcbf --standard=phpcs.xml.dist

`phpcbf` fixes spacing only. Review the diff before committing.

Compatibility check only:

    phpcs --standard=PHPCompatibilityWP --runtime-set testVersion 8.1 wp-content/plugins/drafting-central-portal

## Settings to confirm

- `minimum_wp_version` (set to 6.5; use the real minimum)
- Prefix check is off: WPCS rejects `dc_`/`DC_` (under 3 letters). Turn it on if you use a longer prefix.
- Text domain `drafting-central-portal`

## Limits (tested 04/11/2026)

- The stable PHPCompatibility (9.3.5) is old. It correctly flagged `??` and return types for PHP 5.6, but it did **not** flag PHP 8.0 union types or the `?->` operator, and it has no sniffs for 8.1 enums, `never`, readonly or 8.2+ features. `testVersion 8.1` therefore catches removed and deprecated functions, not new syntax.
- PHPCompatibility 10 would fix this but needs PHP_CodeSniffer 4, which the WordPress standards don't support yet.
- So also lint with real PHP 8.1: `docker run --rm -v "$PWD":/w -w /w php:8.1-cli sh -c 'find wp-content/plugins/drafting-central-portal -name "*.php" -print0 | xargs -0 -n1 php -l'` (or any 8.1 CLI on your PC). An 8.1 `php -l` rejects 8.2+ syntax such as readonly classes and `true`/`null`/`false` standalone types.
