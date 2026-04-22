import asyncio
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
from datetime import datetime
from tqdm import tqdm
import json
import os
import re
import csv

VERGIL_ROOT = "https://vergil.registrar.columbia.edu"
UWB_ROOT = "http://www.columbia.edu/cu/bulletin/uwb/sel"
TERM_WORDS = [None, "Spring", "Summer", "Fall"]

def save_results_locally(data, folder=r"C:\Users\emiik\Downloads"):
    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    json_path = os.path.join(folder, f"vergil_data_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved {len(data)} courses → {json_path}")
    return json_path

def save_results_csv(data, folder=r"C:\Users\emiik\Downloads"):
    if not data:
        print("No courses to save as CSV.")
        return None

    os.makedirs(folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    csv_path = os.path.join(folder, f"vergil_data_{timestamp}.csv")

    rows = []
    for d in data:
        course = d.get("course", {})
        base = {
            "course_identifier": course.get("course_identifier"),
            "dept_code": course.get("department", {}).get("dept_code"),
            "school_code": course.get("school", {}).get("school_code"),
            "course_name": course.get("course_name"),
            "term": course.get("term"),
        }
        classes = course.get("classes", {}).get("class", [])
        if isinstance(classes, dict):
            classes = [classes]
        for cls in classes:
            instructors = cls.get("instructors", [])
            instructor_name = instructors[0]["name"] if instructors else None
            days_times = cls.get("days_times", [])
            if isinstance(days_times, dict):
                days_times = [days_times]
            if not days_times:
                days_times = [{}]
            for dt in days_times:
                row = base.copy()
                row.update({
                    "section": cls.get("section"),
                    "call_number": cls.get("call_number"),
                    "instructor": instructor_name,
                    "start_time": dt.get("mil_time_from"),
                    "end_time": dt.get("mil_time_to"),
                    "days": dt.get("time"),
                })
                rows.append(row)

    fieldnames = [
        "course_identifier", "dept_code", "school_code", "course_name",
        "term", "section", "call_number", "instructor",
        "start_time", "end_time", "days",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} rows → {csv_path}")
    return csv_path

async def fetch(session, url, params=None, retries=4):
    for attempt in range(retries):
        try:
            r = await session.get(url, params=params)
            content = r.content
            if b"Just a moment" in content or b"cf-browser-verification" in content:
                print(f"!! Still Cloudflare on {url} (attempt {attempt+1})")
                await asyncio.sleep(2 ** attempt)
                continue
            return content
        except Exception as e:
            print(f"!! Fetch error ({url}): {e}")
            await asyncio.sleep(0.5 * (attempt + 1))
    return None

def parse_department_page(html, semester):
    soup = BeautifulSoup(html, "lxml")
    regex = re.compile(r"/(\w{2,6})_" + re.escape(semester) + r"\.html")
    depts = []
    rows = soup.select("table tr")[3:-1]
    for row in rows:
        for a in row.find_all("a"):
            href = a.get("href", "")
            m = regex.search(href)
            if m:
                depts.append(m.group(1))
    return depts

def scrape_courses(term_code):
    semester = TERM_WORDS[int(term_code[-1])] + term_code[:-1]
    print(f"\n=== Scraping {semester} ===")
    print("> Fetching departments...")

    async def get_departments():
        async with AsyncSession(impersonate="chrome120") as session:
            all_depts = []
            for c in range(65, 91):
                page = await fetch(session, f"{UWB_ROOT}/dept-{chr(c)}.html")
                if page:
                    depts = parse_department_page(page, semester)
                    all_depts += depts
                await asyncio.sleep(0.3)
            return sorted(set(all_depts))

    departments = asyncio.run(get_departments())
    print(f"> Found {len(departments)} departments from UWB")

    MANUAL_DEPTS = [
        # SAS Humanities
        "AHAR", "CLAS", "EALC", "ENCL", "FRRP", "GERL", "ITAL",
        "MELC", "MUSI", "PHIL", "RELI", "SLAL",
        # LAIC
        "LAIC", "SPAN", "PORT", "CATL", "CAT", "SPPO",
        # SAS Natural Sciences
        "ASTR", "BIOS", "CHEM", "EESC", "EEEB", "MATH", "PHYS", "PSYC", "STAT",
        # SAS Social Sciences
        "AFAM", "ANTH", "ECON", "HIST", "POLS", "SOCI",
        # SEAS
        "APAM", "BMEN", "CEEM", "CHEN", "COMS", "EAEE", "ELEN", "IEOR", "MECE",
    ]

    departments = sorted(set(departments + MANUAL_DEPTS))
    print(f"> Total departments (including manual): {len(departments)}")

    async def get_courses():
        async with AsyncSession(impersonate="chrome120") as session:
            all_courses = []
            failed = []
            empty = []

            for dept in tqdm(departments, desc="Scraping departments"):
                params = {
                    "dept": dept,
                    "key": "*",
                    "moreresults": "2",
                    "term": term_code,
                }
                raw = await fetch(session, f"{VERGIL_ROOT}/doc-adv-queries.php", params=params)
                if not raw:
                    print(f"!! FAILED (no response): {dept}")
                    failed.append(dept)
                    continue
                text = raw.decode("utf-8", errors="ignore")
                if "Just a moment" in text:
                    print(f"!! FAILED (Cloudflare): {dept}")
                    failed.append(dept)
                    continue
                json_start = text.find("[")
                if json_start == -1:
                    print(f"!! EMPTY (no JSON): {dept}")
                    empty.append(dept)
                    continue
                try:
                    data = json.loads(text[json_start:])
                    if not data:
                        print(f"!! EMPTY (0 courses): {dept}")
                        empty.append(dept)
                    else:
                        print(f"   OK ({len(data)} courses): {dept}")
                    all_courses.extend(data)
                except Exception as e:
                    print(f"!! FAILED (JSON parse error): {dept} — {e}")
                    failed.append(dept)
                await asyncio.sleep(0.2)

            print(f"\n=== Summary ===")
            print(f"Failed depts:  {failed}")
            print(f"Empty depts:   {empty}")
            return all_courses

    all_courses = asyncio.run(get_courses())
    save_results_locally(all_courses)
    save_results_csv(all_courses)

if __name__ == "__main__":
    scrape_courses("20253") # CHANGE THIS — <yearsemester> (spring=1, summer=2, fall=3)
    
    all_courses = asyncio.run(get_courses())

