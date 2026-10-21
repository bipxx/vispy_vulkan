"""Freeze a new native epoch only from an explicitly approved ownership manifest."""

import argparse
import json
import sys

sys.dont_write_bytecode = True
import native_epoch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ownership-manifest", required=True)
    parser.add_argument("--ownership-sha256", required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    try:
        result = native_epoch.freeze(native_epoch.ROOT, args.ownership_manifest, args.ownership_sha256,
                                     preflight_only=args.preflight_only)
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Native epoch freeze rejected: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
