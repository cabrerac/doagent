#!/usr/bin/env bash
# Run one DOAgent Werewolf game, then one service game.
# Each game writes its own log under the DOAgent run folder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1

MODEL="${1:-moonshotai/Kimi-K3}"
NAME="${2:-werewolf_kimi_1}"
LOG_DIR="${ROOT}/experiments/multiagentbench/werewolf_runs"
mkdir -p "$LOG_DIR"

note() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*"
}

note "DOAgent started. Model ${MODEL}."
if ! python -m experiments.multiagentbench.run_werewolf_doagent \
  --model "$MODEL" \
  --logging-level 2 \
  > "${LOG_DIR}/${NAME}_doagent.log" \
  2>&1
then
  note "DOAgent failed. See ${NAME}_doagent.log."
  exit 1
fi
note "DOAgent finished."

note "Service started. Name ${NAME}."
if ! python -m experiments.multiagentbench.run_werewolf_service \
  --name "$NAME" \
  --model "$MODEL" \
  > "${LOG_DIR}/${NAME}_service.log" \
  2>&1
then
  note "Service failed. See ${NAME}_service.log."
  exit 1
fi
note "Service finished."
