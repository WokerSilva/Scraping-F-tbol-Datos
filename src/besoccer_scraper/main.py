from __future__ import annotations

import json

from besoccer_scraper.cli.app import main


def _serialize_output(result: object) -> str:
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2, ensure_ascii=False, sort_keys=False)
    return str(result)


if __name__ == "__main__":
    print(_serialize_output(main()))
