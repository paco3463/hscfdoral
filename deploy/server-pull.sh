#!/usr/bin/env bash
# hscfdoral.com — runs ON THE WEB SERVER every 15 minutes (cron). Installed once by SSH DELUXE; see deploy/SERVER-SETUP.md.
#
# Pulls the private GitHub repo (read-only deploy key) and copies the built site/ folder into the web root.
# It does nothing until the first deploy has backed up WordPress and created the "approved" marker,
# and it never touches anything outside the web root.
#
#   HSCF_REPO_DIR   clone of paco3463/hscfdoral, OUTSIDE the web root   (default: ~/hscfdoral-repo)
#   HSCF_WEB_ROOT   the folder the domain serves, e.g. ~/public_html     (required)
#   HSCF_BRANCH     branch to publish                                    (default: main)
#   HSCF_DELETE     1 = also remove files in the web root that are no longer in site/ (default: 0)
#
# crontab:  */15 * * * * HSCF_WEB_ROOT=$HOME/public_html $HOME/hscfdoral-repo/deploy/server-pull.sh >> $HOME/hscfdoral-pull.log 2>&1

set -euo pipefail

REPO_DIR="${HSCF_REPO_DIR:-$HOME/hscfdoral-repo}"
WEB_ROOT="${HSCF_WEB_ROOT:?Set HSCF_WEB_ROOT to the web root folder}"
BRANCH="${HSCF_BRANCH:-main}"
APPROVED="$REPO_DIR/.git/hscf-deploy-approved"
LOCK="$REPO_DIR/.git/hscf-pull.lock"
stamp() { date '+%Y-%m-%d %H:%M:%S'; }

# One run at a time
exec 9>"$LOCK"
if command -v flock >/dev/null 2>&1; then flock -n 9 || exit 0; fi

cd "$REPO_DIR"

# Safety: the web root must not be inside the repo, and the repo must not be inside the web root
case "$(cd "$WEB_ROOT" && pwd -P)/" in "$(pwd -P)/"*) echo "$(stamp) refusing: web root is inside the repo"; exit 1;; esac
case "$(pwd -P)/" in "$(cd "$WEB_ROOT" && pwd -P)/"*) echo "$(stamp) refusing: repo is inside the web root (it would be public)"; exit 1;; esac

if [ ! -f "$APPROVED" ]; then
  # First deploy (WordPress backup) has not happened yet. Stay idle.
  exit 0
fi

git fetch --quiet origin "$BRANCH"
LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse "origin/$BRANCH")"
if [ "$LOCAL" = "$REMOTE" ] && [ -f "$WEB_ROOT/index.html" ] && [ ! -f "$REPO_DIR/.git/hscf-force" ]; then
  exit 0
fi

git merge --ff-only --quiet "origin/$BRANCH"
rm -f "$REPO_DIR/.git/hscf-force"

# Sanity checks on the build before it goes live
for f in site/index.html site/en/index.html site/sitemap.xml site/robots.txt site/.htaccess; do
  [ -s "$f" ] || { echo "$(stamp) refusing: $f is missing or empty"; exit 1; }
done
if grep -q 'draft-banner' site/index.html; then echo "$(stamp) refusing: draft banner on the home page"; exit 1; fi

RSYNC_OPTS=(-a --chmod=D755,F644 --exclude ".DS_Store" --exclude "._*")
if [ "${HSCF_DELETE:-0}" = "1" ]; then
  # Never remove things the host or the old site still needs
  RSYNC_OPTS+=(--delete-after --filter "protect .well-known/" --filter "protect cgi-bin/" --filter "protect .user.ini"
               --filter "protect php.ini" --filter "protect error_log" --filter "protect wordpress-backup*/")
fi

if command -v rsync >/dev/null 2>&1; then
  rsync "${RSYNC_OPTS[@]}" site/ "$WEB_ROOT/"
else
  cp -R site/. "$WEB_ROOT/"
fi

echo "$(stamp) published $(git rev-parse --short HEAD): $(git log -1 --pretty=%s)"
