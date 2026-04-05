import json
from datetime import datetime, timezone
from urllib.request import urlopen, Request


OUTPUT_PATH = "data/etf-data.json"


def fetch_json(url: str):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as res:
        return json.loads(res.read().decode("utf-8"))


def main():
    # 현재 코인 가격 가져오기
    coin_url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum,solana&vs_currencies=usd"
    )
    coin = fetch_json(coin_url)

    btc = float(coin["bitcoin"]["usd"])
    eth = float(coin["ethereum"]["usd"])
    sol = float(coin["solana"]["usd"])

    # ETF 종가는 일단 수동 고정
    # 나중에 이 부분만 자동화하면 됨
    ETF_CLOSE = {
        "ETHU": 21.65,
        "BITX": 14.39,
        "SOLT": 41.16,
        "MSTU": 3.90,
    }

    # 기준일
    ref_date = "2026-04-02"

    data = {
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "ref_date": ref_date,
        "partial": False,
        "errors": [],
        "prices": {
            "ETHU": {
                "close": ETF_CLOSE["ETHU"],
                "date": ref_date,
                "coin_close": eth
            },
            "BITX": {
                "close": ETF_CLOSE["BITX"],
                "date": ref_date,
                "coin_close": btc
            },
            "SOLT": {
                "close": ETF_CLOSE["SOLT"],
                "date": ref_date,
                "coin_close": sol
            },
            "MSTU": {
                "close": ETF_CLOSE["MSTU"],
                "date": ref_date,
                "coin_close": btc
            }
        }
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ etf-data.json 업데이트 완료")
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
