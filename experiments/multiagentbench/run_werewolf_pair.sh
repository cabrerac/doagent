#!/usr/bin/env bash
# Run one or more Werewolf pairs.
# Each repetition has doagent/ and service/ under werewolf_runs/<name>/<index>/.
# The console log for an arm stays in that arm's folder.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONUNBUFFERED=1
PYTHON="${ROOT}/.wvenv/bin/python"

MODEL="${1:-moonshotai/Kimi-K3}"
NAME="${2:-werewolf_kimi_1}"
REPEATS="${3:-1}"
LOG_DIR="${ROOT}/experiments/multiagentbench/werewolf_runs"
RUN_ROOT="${LOG_DIR}/${NAME}"
PAIR_LOG="${RUN_ROOT}/pair.log"
mkdir -p "$RUN_ROOT"

note() {
  local line
  line="$(date '+%Y-%m-%d %H:%M:%S') $*"
  echo "$line" | tee -a "$PAIR_LOG"
}

FAILS=0
note "Pair started. Model ${MODEL}. Repetitions ${REPEATS}. Folder ${RUN_ROOT}."

for index in $(seq 1 "$REPEATS"); do
  LABEL="$(printf '%02d' "$index")"
  DEST="${RUN_ROOT}/${LABEL}"
  DO_DIR="${DEST}/doagent"
  SV_DIR="${DEST}/service"
  mkdir -p "$DO_DIR" "$SV_DIR"
  note "Repetition ${LABEL} started. DOAgent ${DO_DIR}. Service ${SV_DIR}."

  note "DOAgent started. Repetition ${LABEL}."
  if ! "$PYTHON" -m experiments.multiagentbench.run_werewolf_doagent \
    --model "$MODEL" \
    --logging-level 2 \
    --output "$DO_DIR" \
    > "${DO_DIR}/console.log" \
    2>&1
  then
    note "DOAgent failed. Repetition ${LABEL}. See ${DO_DIR}/console.log."
    FAILS=$((FAILS + 1))
    continue
  fi
  note "DOAgent finished. Repetition ${LABEL}."

  note "Service started. Repetition ${LABEL}."
  if ! "$PYTHON" -m experiments.multiagentbench.run_werewolf_service \
    --name "${NAME}_${LABEL}" \
    --model "$MODEL" \
    --output "$SV_DIR" \
    > "${SV_DIR}/console.log" \
    2>&1
  then
    note "Service failed. Repetition ${LABEL}. See ${SV_DIR}/console.log."
    FAILS=$((FAILS + 1))
    continue
  fi
  note "Service finished. Repetition ${LABEL}."
done

if [ "$FAILS" -ne 0 ]; then
  note "Pair finished with ${FAILS} failed repetition(s). See pair.log and each console.log."
  exit 1
fi
note "Pair finished. Repetitions ${REPEATS}."
