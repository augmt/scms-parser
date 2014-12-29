#!/bin/bash

git remote add -f smogon-scms https://github.com/smogon/scms
git checkout smogon-scms/master dex/analyses

git remote remove smogon-scms
rm -rf .git/FETCH_HEAD .git/logs/refs/remotes/smogon-scms .git/refs/remotes/smogon-scms
git reflog expire --expire=now --all
git gc --prune=now

if test -n "$(git status --porcelain)"; then
    git commit -am "Scripted fetch and checkout from smogon/scms github repo"
    git push
fi
exit 0
