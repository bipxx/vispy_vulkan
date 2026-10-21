"""Build a new isolated SDK epoch with explicit ownership and frozen-input pins."""

import argparse
import json
import sys

sys.dont_write_bytecode = True
import native_epoch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ownership-manifest", required=True)
    parser.add_argument("--ownership-sha256", required=True)
    parser.add_argument("--frozen-inputs-sha256", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--attempt", default="initial")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    try:
        result = native_epoch.build(native_epoch.ROOT, args.ownership_manifest, args.ownership_sha256,
                                    args.frozen_inputs_sha256, resume=args.resume, attempt=args.attempt,
                                    preflight_only=args.preflight_only)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Native epoch build rejected: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
