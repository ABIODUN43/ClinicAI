import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.training_data import (
    build_extraction_meta,
    extract_report_metadata,
    infer_state_metrics_from_text,
    manual_state_metrics_for_report,
    merge_state_metric_overrides,
    write_state_metric_review_csv,
)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/extract_ncdc_sitrep.py <pdf_path> [output_json]")
        return 1

    pdf_path = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / "backend" / "data" / f"{pdf_path.stem}.json"
    override_path = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else output_path.with_name(f"{output_path.stem}_state_overrides.csv")
    review_path = output_path.with_name(f"{output_path.stem}_state_review.csv")

    payload = extract_report_metadata(pdf_path)
    inferred_metrics = infer_state_metrics_from_text(pdf_path, summary=payload["summary"])
    extraction_source = "text-inference"
    if not inferred_metrics:
        inferred_metrics = manual_state_metrics_for_report(payload["year"], payload["epi_week"])
        extraction_source = "manual-fallback"

    merged_metrics, overrides_applied = merge_state_metric_overrides(inferred_metrics, override_path)
    payload["state_metrics"] = merged_metrics
    payload["extraction_meta"] = {
        **build_extraction_meta(merged_metrics, extraction_source),
        "override_csv_path": str(override_path),
        "review_csv_path": str(review_path),
        "overrides_applied": overrides_applied,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_state_metric_review_csv(merged_metrics, review_path)
    print(f"Wrote extracted SITREP payload to {output_path}")
    print(f"Wrote state review CSV to {review_path}")
    if not overrides_applied:
        print(f"No override CSV applied. Add corrections in {override_path} and rerun this script to merge them.")
    else:
        print(f"Applied override CSV from {override_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
