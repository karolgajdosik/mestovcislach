#!/usr/bin/env bash
# Commit a push zmien v data/ a public/data/ z GitHub Actions – bezpečne aj pri súbežných jobs (rebase s opakovaním).
# Použitie: bash scripts/uloz_data.sh "popis"
set -u
git config user.name "mestovcislach-bot"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add data/ public/data/
if git diff --cached --quiet; then
  echo "Žiadne nové dáta."
  exit 0
fi
git commit -q -m "Dáta: ${1:-zber} $(date -u +%Y-%m-%d)"
for i in 1 2 3 4 5 6; do
  git pull --rebase -X theirs -q && git push -q && break
  sleep $((i * 7))
done
git fetch -q origin main
if ! git merge-base --is-ancestor HEAD origin/main; then
  echo "::error::Push dát zlyhal"
  exit 1
fi
