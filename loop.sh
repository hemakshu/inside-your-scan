#!/usr/bin/env bash
# Always-on checker: runs the quick check every 5 minutes for ~5.5 hours, then the workflow starts the next round.
# This replaces GitHub's scheduled runs, which are often skipped or hours late.
set -u
END=$(( $(date +%s) + ${LOOP_MINUTES:-330} * 60 ))
TOOLS=0
MAKE_FAILS=0
NEXT_MAKE_OK=0

git config user.name "inside-your-scan"
git config user.email "actions@users.noreply.github.com"

save_state() {
  git add state/
  if ! git diff --cached --quiet; then
    git commit -q -m "state: $(date +%F_%H%M)"
    if ! git pull -q --rebase origin main; then
      echo "⚠️  state clash with another run; keeping the newer state from GitHub"
      git rebase --abort 2>/dev/null; git reset -q --hard origin/main
    fi
    git push -q origin HEAD:main || echo "⚠️  couldn't push state (will retry next round)"
  fi
}

while [ "$(date +%s)" -lt "$END" ]; do
  git pull -q --rebase origin main 2>/dev/null || { git rebase --abort 2>/dev/null; git reset -q --hard origin/main; }
  echo "── $(TZ=Asia/Kolkata date '+%a %d %b %H:%M IST')"
  OUT=$(mktemp)
  GITHUB_OUTPUT=$OUT python tick.py || echo "⚠️  quick check failed; trying again in 5 minutes"
  if grep -q "make=true" "$OUT" && [ "$(date +%s)" -ge "$NEXT_MAKE_OK" ] && [ "$MAKE_FAILS" -lt 6 ]; then
    if [ "$TOOLS" = 0 ]; then
      echo "🔧 Installing video tools …"
      sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg >/dev/null
      pip install -q -r requirements.txt && python -m playwright install --with-deps chromium >/dev/null && TOOLS=1
    fi
    if python make.py; then
      MAKE_FAILS=0
    else
      MAKE_FAILS=$((MAKE_FAILS + 1))
      NEXT_MAKE_OK=$(( $(date +%s) + 1800 ))   # retry a failed video after 30 minutes
      echo "⚠️  video failed ($MAKE_FAILS); next try in 30 minutes"
    fi
  fi
  save_state
  sleep 300
done
echo "⏱  Round finished; the next one starts now."
