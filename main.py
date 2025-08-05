from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import traceback

app = FastAPI()

@app.get("/check_seats")
def check_seats(crn: str, term: str):
    try:
        url = f"https://selfservice.mypurdue.purdue.edu/prod/bwckschd.p_disp_detail_sched?term_in={term}&crn_in={crn}"
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"
        }
        response = requests.get(url, headers=headers, timeout=10)

        # Save the page for debugging
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(response.text)

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract the course title
        title_tag = soup.find("th", class_="ddlabel")
        course_title = title_tag.text.strip() if title_tag else "Unknown Course"

        # Look for the seating info table
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
        # Save traceback to file for debugging
        with open("debug_error.log", "w") as f:
            f.write(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={"error": f"Could not fetch data: {e}"}
        )

if __name__ == "__main__":
    import uvicorn
    print("✅ FastAPI backend starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
