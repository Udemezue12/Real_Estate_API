from typing import List


class URLParser:
    def parse_url_list(self, raw_value: str, name: str) -> List[str]:
        items = [v.strip() for v in raw_value.split(",") if v.strip()]

        valid_items = [
            v for v in items if v.startswith("http://") or v.startswith("https://")
        ]

        if not valid_items:
            print(f"WARNING: No valid URLs found in {name}")

        return valid_items


parser = URLParser()
