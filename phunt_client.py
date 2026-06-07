"""Product Hunt GraphQL API client — fetch today's top products."""

import requests
from datetime import datetime, timezone, timedelta
from config import PHUNT_API_TOKEN

API_URL = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query GetTodayPosts($first: Int!, $postedAfter: DateTime) {
  posts(order: VOTES, first: $first, postedAfter: $postedAfter) {
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
        topics {
          edges {
            node {
              name
            }
          }
        }
      }
    }
  }
}
"""


def _get_today_pt() -> str:
    """Get today's date in Product Hunt time (Pacific Time) as ISO string."""
    # Product Hunt uses Pacific Time (UTC-7 or UTC-8 depending on DST)
    # Use UTC-7 (PDT) as rough approximation
    pt_now = datetime.now(timezone(timedelta(hours=-7)))
    today_start = pt_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start.isoformat()


def fetch_top_products(count: int = 5) -> list[dict]:
    """Fetch top products from Product Hunt.

    Returns list of dicts with keys:
        name, tagline, description, url, votes, thumbnail, topics
    """
    headers = {
        "Authorization": f"Bearer {PHUNT_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"query": QUERY, "variables": {"first": count, "postedAfter": _get_today_pt()}}

    resp = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    products = []
    for edge in data["data"]["posts"]["edges"]:
        node = edge["node"]
        topics = [t["node"]["name"] for t in node["topics"]["edges"]]
        products.append({
            "name": node["name"],
            "tagline": node["tagline"],
            "description": node["description"],
            "url": node["url"],
            "votes": node["votesCount"],
            "thumbnail": node["thumbnail"]["url"] if node["thumbnail"] else "",
            "topics": topics,
        })
    return products


def display_products(products: list[dict]) -> None:
    """Print products as a numbered list for user selection."""
    print("\n🏆 Product Hunt 今日 Top 5:\n")
    for i, p in enumerate(products, 1):
        topics_str = ", ".join(p["topics"][:3]) if p["topics"] else "N/A"
        print(f"  [{i}] {p['name']}  ({p['votes']} votes)")
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
