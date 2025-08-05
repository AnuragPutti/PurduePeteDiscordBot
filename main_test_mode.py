from fastapi import FastAPI, Query
import uvicorn

app = FastAPI()

@app.get("/check_seats")
async def check_seats(crn: str = Query(...), term: str = Query("202610")):
    print(f"[TEST MODE] Simulating fetch for CRN {crn} and Term {term}")

    # Simulated responses per CRN (you can change these manually for testing)
    simulated_data = {
        "12384": {
            "CourseTitle": "Policy, Regulation, And Globalization In IT",
            "Capacity": "72",
            "Actual": "70",
            "Remaining": "2"
        },
        "12385": {
            "CourseTitle": "Systems Programming",
            "Capacity": "65",
            "Actual": "65",
            "Remaining": "0"
        }
    }

    data = simulated_data.get(crn)
    if data:
        return data
    else:
        return {
            "CourseTitle": f"[SIMULATED] Example Course - {crn}",
            "Capacity": "60",
            "Actual": "58",
            "Remaining": "2"
        }

if __name__ == "__main__":
    print("☑️ FastAPI server starting in test mode...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
