"""
FERC eLibrary PDF Downloader
============================
Replicates what the browser does when you click "Generate PDF" on:
  https://elibrary.ferc.gov/eLibrary/search

Flow
----
1.  POST  /eLibrary/GeneralSearch/search           → get search hits
2.  Pick the first hit, extract accession number + file metadata
3.  POST  /eLibrary/GeneralSearch/GeneratePDF      → kick off server-side PDF build
4.  GET   /eLibrary/GeneralSearch/GetGeneratedPDF  → poll until the PDF is ready
5.  Stream the PDF bytes to disk

Dependencies
------------
    pip install requests
"""

import time
import os
import requests

# ── Base URL ────────────────────────────────────────────────────────────────────
BASE_URL = "https://elibrary.ferc.gov/eLibrary"

# Shared session so cookies / headers are reused across every request
session = requests.Session()
session.headers.update({
    "Accept":          "application/json, text/plain, */*",
    "Content-Type":    "application/json",
    "Origin":          "https://elibrary.ferc.gov",
    "Referer":         "https://elibrary.ferc.gov/eLibrary/search",
    "User-Agent":      (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
})


# ── 1. General Search ────────────────────────────────────────────────────────────
def general_search(search_text: str = "", results_per_page: int = 10) -> dict:
    """
    POST /eLibrary/GeneralSearch/search
    Mirrors the GeneralSearchParams type in the ferc-elibrary-api wrapper.
    Returns the raw JSON response (GeneralSearchResult shape).
    """
    payload = {
        "searchText":          search_text,
        "resultsPerPage":      results_per_page,
        "curPage":             1,
        "sortBy":              "Filed Date",
        "groupBy":             "N",
        "searchDescription":   False,
        "searchFullText":      False,
        "allDates":            True,
        "eFiling":             False,
        "accessionNumber":     None,
        "parentAccessionNumber": "",
        "idolResultID":        "",
        "fercCite":            "",
        "fedRegisterCite":     "",
        "fedCourtCaseNumber":  "",
        "orderNumber":         "",
        "opinion":             "",
        "libraries":           [],
        "categories":          [],
        "classTypes":          [],
        "affiliations":        [],
        "availability":        None,
        "docketSearches":      [],
        "dateSearches":        [],
    }

    url = f"{BASE_URL}/GeneralSearch/search"
    print(f"[1] Searching eLibrary  →  {url}")
    resp = session.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ── 2. Extract the first usable hit ─────────────────────────────────────────────
def extract_first_hit(search_result: dict) -> dict:
    """
    Pull the first searchHit that has an accessionNumber and at least one file.
    Returns a normalised dict with the keys we need later.
    """
    hits = search_result.get("searchHits", [])
    if not hits:
        raise ValueError("No search results returned.")

    for hit in hits:
        accession = hit.get("accessionNumber") or hit.get("accession_num")
        if not accession:
            continue

        # File list lives under different keys depending on FERC API version
        file_list = (
            hit.get("fileList")
            or hit.get("files")
            or []
        )

        print(f"\n[2] First result:")
        print(f"    Accession : {accession}")
        print(f"    Description: {hit.get('description', hit.get('docDescription', ''))}")
        print(f"    Filed Date : {hit.get('filedDate', hit.get('filed_date', ''))}")
        print(f"    Files found: {len(file_list)}")

        # Build DownloadFileParams for the first file in the list (if any)
        file_params = None
        if file_list:
            f = file_list[0]
            file_params = {
                "accession":   accession,
                "fileid":      f.get("fileid") or f.get("fileId") or 0,
                "FileIDAll":   f.get("FileIDAll") or f.get("fileIdAll") or "",
                "FileType":    f.get("FileType") or f.get("fileType") or "",
                "Islegacy":    f.get("Islegacy") or f.get("isLegacy") or False,
                "fileidLst":   f.get("fileidLst") or f.get("fileIdLst") or [],
            }

        return {
            "accessionNumber": accession,
            "hit":             hit,
            "file_params":     file_params,
        }

    raise ValueError("No hits contained a valid accession number.")


# ── 3. Trigger server-side PDF generation ────────────────────────────────────────
def trigger_generate_pdf(accession_number: str, file_params: dict | None = None) -> str:
    """
    POST /eLibrary/GeneralSearch/GeneratePDF
    Asks the FERC server to build a PDF for the document.

    Returns the PDF request ID (used to poll status).
    """
    payload: dict = {"accessionNumber": accession_number}
    if file_params:
        payload.update(file_params)

    url = f"{BASE_URL}/GeneralSearch/GeneratePDF"
    print(f"\n[3] Triggering PDF generation  →  {url}")
    resp = session.post(url, json=payload, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    print(f"    Server response: {data}")

    # The API may return the request ID under several key names
    request_id = (
        data.get("pdfRequestId")
        or data.get("requestId")
        or data.get("id")
        or data.get("jobId")
        or ""
    )
    if not request_id:
        # Some FERC endpoints return the ID at the top level as a plain string
        if isinstance(data, str):
            request_id = data

    if not request_id:
        raise ValueError(f"Could not extract a PDF request ID from: {data}")

    print(f"    PDF request ID: {request_id}")
    return str(request_id)


# ── 4. Poll until the PDF is ready ───────────────────────────────────────────────
def poll_for_pdf(
    request_id: str,
    accession_number: str,
    poll_interval: float = 3.0,
    max_attempts: int = 40,
) -> bytes:
    """
    GET /eLibrary/GeneralSearch/GetGeneratedPDF?id=<request_id>

    Polls the FERC server until the PDF bytes arrive (or we give up).
    Returns raw PDF bytes on success.
    """
    url = f"{BASE_URL}/GeneralSearch/GetGeneratedPDF"
    print(f"\n[4] Polling for PDF  →  {url}")

    for attempt in range(1, max_attempts + 1):
        print(f"    Attempt {attempt}/{max_attempts} …", end=" ", flush=True)

        resp = session.get(
            url,
            params={
                "id":              request_id,
                "accessionNumber": accession_number,
            },
            timeout=60,
            stream=True,
        )

        content_type = resp.headers.get("Content-Type", "")

        if resp.status_code == 200 and "application/pdf" in content_type:
            pdf_bytes = resp.content
            print(f"PDF ready! ({len(pdf_bytes):,} bytes)")
            return pdf_bytes

        if resp.status_code == 202 or "pending" in resp.text.lower():
            print("still generating …")
        elif resp.status_code == 200 and "json" in content_type:
            # Some versions return JSON status objects
            data = resp.json()
            status = data.get("status", "")
            print(f"status = {status}")
            if status.lower() in ("complete", "done", "finished"):
                # Try a direct download URL if provided
                download_url = data.get("url") or data.get("pdfUrl") or data.get("downloadUrl")
                if download_url:
                    pdf_resp = session.get(download_url, timeout=60)
                    pdf_resp.raise_for_status()
                    print(f"    Downloaded from redirect URL ({len(pdf_resp.content):,} bytes)")
                    return pdf_resp.content
        else:
            print(f"unexpected  status={resp.status_code}  content-type={content_type}")

        time.sleep(poll_interval)

    raise TimeoutError(f"PDF not ready after {max_attempts} polling attempts.")


# ── 5. Save PDF to disk ──────────────────────────────────────────────────────────
def save_pdf(pdf_bytes: bytes, accession_number: str, output_dir: str = ".") -> str:
    """Write the PDF bytes to a local file and return the file path."""
    safe_name = accession_number.replace("/", "-").replace("\\", "-")
    filename   = os.path.join(output_dir, f"{safe_name}.pdf")
    with open(filename, "wb") as fh:
        fh.write(pdf_bytes)
    print(f"\n[5] Saved  →  {os.path.abspath(filename)}  ({len(pdf_bytes):,} bytes)")
    return filename


# ── Main ─────────────────────────────────────────────────────────────────────────
def main(search_text: str = "", output_dir: str = ".") -> None:
    """
    End-to-end: search → pick first result → generate PDF → download → save.

    Parameters
    ----------
    search_text : str
        Keyword(s) to search.  Leave empty for the default "recent filings" view.
    output_dir  : str
        Directory where the downloaded PDF will be saved.
    """
    # 1. Search
    search_result = general_search(search_text=search_text, results_per_page=10)
    total = search_result.get("totalHits", search_result.get("numHits", "?"))
    print(f"    Total hits: {total}")

    # 2. Pick the first hit
    first = extract_first_hit(search_result)
    accession   = first["accessionNumber"]
    file_params = first["file_params"]

    # 3. Trigger PDF generation
    request_id = trigger_generate_pdf(accession, file_params)

    # 4. Poll until ready and collect bytes
    pdf_bytes = poll_for_pdf(request_id, accession)

    # 5. Save
    os.makedirs(output_dir, exist_ok=True)
    save_pdf(pdf_bytes, accession, output_dir)


if __name__ == "__main__":
    # ── Configuration ────────────────────────────────────────────────────────────
    SEARCH_TEXT = ""        # e.g. "natural gas pipeline" — leave blank for latest filings
    OUTPUT_DIR  = "."       # directory where the PDF will be saved

    main(search_text=SEARCH_TEXT, output_dir=OUTPUT_DIR)
