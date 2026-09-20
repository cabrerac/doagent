"""Compare gridworld topologies with one measured run per topology."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from examples.gridworld.session import load_config
from experiments._shared import write_summary
from experiments.gridworld.evaluate import evaluate_gridworld


TOPOLOGIES = {
    "centralised": None,
    "peer_to_peer": {
        "agent_0": ["agent_1"],
        "agent_1": ["agent_2"],
        "agent_2": ["agent_3"],
        "agent_3": ["agent_0"],
    },
    "federated": None,
}


def main() -> None:
    """Run three topology conditions with fixed storage, seed, and policies."""
    parser = argparse.ArgumentParser(description="Compare gridworld topologies")
    parser.add_argument(
        "--output-dir",
        default="output/topo_comparison",
    )
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    config_path = (
        Path(args.config)
        if args.config
        else root / "examples" / "gridworld" / "config.yaml"
    )
    config = load_config(config_path)
    results = {
        topology: evaluate_gridworld(
            config,
            storage="file",
            output_base=args.output_dir,
            topology_mode=topology,
            visibility=visibility,
        )
        for topology, visibility in TOPOLOGIES.items()
    }
    summary_path = Path(args.output_dir) / "topology_comparison_summary.json"
    write_summary(
        summary_path,
        {"runs": {key: asdict(value) for key, value in results.items()}},
    )
    print(f"Comparison summary written to {summary_path}")


if __name__ == "__main__":
    main()
