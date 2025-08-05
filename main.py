from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import traceback
import os
import json
import asyncio
import threading

app = FastAPI()

WATCHLIST_FILE = os.path.join(os.path.dirname(__file__), "watchlist.json")
PREVIOUS_SEATS = {}

@app.get("/check_seats")
def check_seats(crn: str, term: str):
    try:
        url = f"https://selfservice.mypurdue.purdue.edu/prod/bwckschd.p_disp_detail_sched?term_in={term}&crn_in={crn}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
        }
        response = requests.get(url, headers=headers, timeout=10)

        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("th", class_="ddlabel")
        course_title = title_tag.text.strip() if title_tag else "Unknown Course"

        seating_table = soup.find("table", class_="datadisplaytable", summary="This layout table is used to present the seating numbers.")
        if not seating_table:
            raise ValueError("Could not find the seating information table.")

        rows = seating_table.find_all("tr")
        if len(rows) < 2:
            raise ValueError("Unexpected structure in seating table.")

        values = rows[1].find_all("td")
        if len(values) != 3:
            raise ValueError(f"Unexpected number of columns in seats row: {len(values)}")

        capacity = values[0].text.strip()
        actual = values[1].text.strip()
        remaining = values[2].text.strip()

        return {
            "CourseTitle": course_title,
            "Capacity": capacity or "N/A",
            "Actual": actual or "N/A",
            "Remaining": remaining or "N/A"
        }

    except Exception as e:
        with open("debug_error.log", "w") as f:
            f.write(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={"error": f"Could not fetch data: {e}"}
        )


async def watch_courses_loop():
    print("🔁 Watcher loop started...")

    while True:
        try:
            with open(WATCHLIST_FILE, "r") as f:
                watchlist = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            watchlist = {}

        print(f"🔍 Loaded watchlist: {watchlist}")

        for user_id, courses in watchlist.items():
            for entry in courses:
                crn = entry["crn"]
                term = entry["term"]
                key = f"{crn}_{term}"

                try:
                    url = f"http://localhost:8000/check_seats?crn={crn}&term={term}"
                    resp = requests.get(url, timeout=10)
                    if resp.status_code != 200:
                        print(f"[{key}] ❌ Error: {resp.json().get('error')}")
                        continue

                    data = resp.json()
                    remaining = data.get("Remaining", "N/A")

                    prev = PREVIOUS_SEATS.get(key)
                    PREVIOUS_SEATS[key] = remaining

                    if prev is not None and prev != remaining:
                        print(f"[{key}] 🔔 Seats changed: {prev} → {remaining}")
                    else:
                        print(f"[{key}] Remaining: {remaining}, Previous: {prev}")

                except Exception as e:
                    print(f"[{key}] ❌ Exception in watch loop: {e}")

        await asyncio.sleep(60)


def start_background_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(watch_courses_loop())

if __name__ == "__main__":
    print("✅ FastAPI backend starting on http://localhost:8000")

    # Delay watcher start by 2 seconds
    def delayed_watcher_start():
        import time
        time.sleep(2)
        start_background_loop()

    threading.Thread(target=delayed_watcher_start, daemon=True).start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

