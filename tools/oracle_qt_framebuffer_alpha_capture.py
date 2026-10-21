"""Isolated, fixed upstream/candidate public Qt framebuffer-alpha captures."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import numpy as np

from fixture_qt_framebuffer_alpha import CASES, render
from oracle_capture import ROOT, provenance, sha256, write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--kind",choices=("upstream","candidate"),required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--worker",choices=CASES)
    args=p.parse_args()
    os.environ.setdefault("QT_API","pyqt6")
    os.environ.setdefault("QT_SCALE_FACTOR","1")
    import vispy
    vispy.use(app="pyqt6",**({"gl":"gl+"} if args.kind=="upstream" else {}))
    if args.worker:
        record={"case":args.worker,"provenance":provenance(args.kind)}
        try:
            arrays,params,observations=render(args.worker)
            artifacts={}
            for name,array in arrays.items():
                path=args.output/f"{args.worker}.{name}.npy"
                np.save(path,array,allow_pickle=False)
                artifacts[name]={"file":path.name,"sha256":sha256(path)}
            record.update(parameters=params,observations=observations,artifacts=artifacts,status="captured")
        except Exception as error:
            record.update(status="failed",error=str(error),traceback=traceback.format_exc())
        write_json(args.output/f"{args.worker}.capture.json",record)
        print(json.dumps({"case":args.worker,"status":record["status"],"error":record.get("error")}))
        return int(record["status"]!="captured")
    args.output.mkdir(parents=True,exist_ok=False)
    manifest={"schema":1,"kind":args.kind,"fixture_sha256":sha256(ROOT/"tools/fixture_qt_framebuffer_alpha.py"),
              "capture_sha256":sha256(__file__),"comparison":"exact all frozen arrays; no candidate-dependent tolerance",
              "fixtures":{},"errors":{}}
    for case in CASES:
        command=[sys.executable,"-X","faulthandler",str(Path(__file__).resolve()),"--kind",args.kind,
                 "--output",str(args.output),"--worker",case]
        child=subprocess.run(command,capture_output=True,timeout=60)
        process={"command":command,"exit_code":child.returncode}
        for stream in ("stdout","stderr"):
            path=args.output/f"{case}.{stream}.log"
            path.write_bytes(getattr(child,stream))
            process[stream]={"file":path.name,"sha256":sha256(path)}
        record=json.loads((args.output/f"{case}.capture.json").read_text())
        record["process"]=process
        manifest["fixtures" if child.returncode==0 and record["status"]=="captured" else "errors"][case]=record
        write_json(args.output/"manifest.json",manifest)
        print(json.dumps({"case":case,"exit_code":child.returncode,"status":record["status"]}),flush=True)
    return int(bool(manifest["errors"]))


if __name__=="__main__":
    raise SystemExit(main())
