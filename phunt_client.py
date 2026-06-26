"""Product Hunt GraphQL API client — fetch today's top products."""

import requests
from datetime import datetime, timezone, timedelta
from config import PHUNT_API_TOKEN

API_URL = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query GetPosts($first: Int!, $postedAfter: DateTime, $postedBefore: DateTime) {
  posts(order: VOTES, first: $first, postedAfter: $postedAfter, postedBefore: $postedBefore) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        thumbnail {
          url
        }
        media {
          url
          type
        }
        topics {
          edges {
            node {
              name
            }
          }
        }
        comments(first: 5, order: NEWEST) {
          edges {
            node {
              body
              user {
                name
                username
              }
            }
          }
        }
      }
    }
  }
}
"""


def _get_pt_date_start(days_ago: int = 0) -> str:
    """Get the start of a day in Product Hunt time (Pacific Time) as ISO string.

    Args:
        days_ago: 0 = today, 1 = yesterday, etc.
    """
    # Product Hunt uses Pacific Time (UTC-7 or UTC-8 depending on DST)
    # Use UTC-7 (PDT) as rough approximation
    pt_now = datetime.now(timezone(timedelta(hours=-7)))
    target = pt_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if days_ago:
        target = target - timedelta(days=days_ago)
    return target.isoformat()


def _get_pt_date_end(days_ago: int = 0) -> str:
    """Get the end of a day in Product Hunt time (Pacific Time) as ISO string."""
    pt_now = datetime.now(timezone(timedelta(hours=-7)))
    target = pt_now.replace(hour=23, minute=59, second=59, microsecond=0)
    if days_ago:
        target = target - timedelta(days=days_ago)
    return target.isoformat()


def fetch_top_products(count: int = 5, days_ago: int = 0) -> list[dict]:
    """Fetch top products from Product Hunt.

    Args:
        count: Number of products to fetch.
        days_ago: 0 = today, 1 = yesterday, etc.

    Returns list of dicts with keys:
        name, tagline, description, url, votes, thumbnail, topics
    """
    headers = {
        "Authorization": f"Bearer {PHUNT_API_TOKEN}",
        "Content-Type": "application/json",
    }
    variables = {
        "first": count,
        "postedAfter": _get_pt_date_start(days_ago),
        "postedBefore": _get_pt_date_end(days_ago),
    }
    payload = {"query": QUERY, "variables": variables}

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    if "errors" in data:
        print(f"   ❌ API 错误: {data['errors']}")
        return []
    products = []
    for edge in data["data"]["posts"]["edges"]:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node["topics"]["edges"]]
        # Extract maker's comment (first comment is usually from the maker)
        comments = []
        for c in node.get("comments", {}).get("edges", []):
            comments.append({
                "body": c["node"]["body"],
                "user": c["node"]["user"]["name"],
            })
        products.append({
            "name": node["name"],
            "tagline": node["tagline"],
            "description": node["description"],
            "url": node["url"],
            "votes": node["votesCount"],
            "thumbnail": node["thumbnail"]["url"] if node["thumbnail"] else "",
            "topics": topics,
            "media": [
                {"url": m["url"], "type": m["type"]}
                for m in node.get("media", [])
            ],
            "comments": comments,
        })
    return products


def display_products(products: list[dict], label: str = "今日") -> None:
    """Print products as a numbered list for user selection."""
    print(f"\n🏆 Product Hunt {label} Top 5:\n")
    for i, p in enumerate(products, 1):
        topics_str = ", ".join(p["topics"][:3]) if p["topics"] else "N/A"
        image_count = len([m for m in p["media"] if m["type"] == "image"])
        video_count = len([m for m in p["media"] if m["type"] == "video"])
        media_info = f"{image_count}图"
        if video_count:
            media_info += f" +{video_count}视频"
        print(f"  [{i}] {p['name']}  ({p['votes']} votes, {media_info})")
        print(f"      {p['tagline']}")
        print(f"      Topics: {topics_str}")
        print()


def select_product(products: list[dict]) -> dict:
    """Prompt user to select a product by number."""
    while True:
        try:
            choice = int(input("选择产品编号 (1-5): "))
            if 1 <= choice <= len(products):
                return products[choice - 1]
            print(f"请输入 1-{len(products)} 之间的数字")
        except ValueError:
            print("请输入数字")
