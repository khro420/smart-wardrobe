"""Real-browser acceptance walkthrough against an already-running local demo.

Requires Playwright and an installed Edge browser. Creates a unique local account
and uses existing validation imagery; never touches another user's wardrobe.
"""
import json
import os
from pathlib import Path
import time
import uuid

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "storage" / "verification" / "o1" / "browser"
RUN_OUT = ROOT / "backend" / "runs" / "o1"
BASE = os.getenv("WORKFLOW_UI_URL", "http://localhost:3001")
SAMPLE = ROOT / "backend/datasets/deepfashion2_yolo_seg/images/validation/000001.jpg"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    RUN_OUT.mkdir(parents=True, exist_ok=True)
    email = f"workflow-{uuid.uuid4().hex[:10]}@example.test"
    password = "Local-demo-passphrase-2026"
    report = {"base_url": BASE, "sample": str(SAMPLE.relative_to(ROOT)), "account": email, "checks": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        page = context.new_page()
        errors = []
        image_warnings = []
        dialog_messages = []
        dialog_decision = {"accept": True}
        def handle_dialog(dialog):
            dialog_messages.append(dialog.message)
            dialog.accept() if dialog_decision["accept"] else dialog.dismiss()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: image_warnings.append(message.text) if message.type == "warning" and 'Image with src' in message.text else None)
        page.on("dialog", handle_dialog)
        page.goto(BASE + "/auth")
        page.get_by_role("button", name="Register", exact=True).click()
        page.get_by_label("Display name", exact=True).fill("Workflow demo")
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Create private account").click()
        page.wait_for_url(BASE + "/", timeout=60000)
        report["checks"].append("Register and receive an authenticated browser session")
        page.goto(BASE + "/extract")
        page.locator('input[type="file"]').set_input_files(str(SAMPLE))
        page.wait_for_url("**/extract/results?job=**", timeout=60000)
        expect(page.get_by_role("button", name="Accept candidate").first).to_be_visible(timeout=120000)
        count = page.locator("article").count()
        assert count >= 2, f"Expected multiple real candidates, found {count}"
        report["candidate_count"] = count
        report["checks"].append("Real YOLO upload reaches review with multiple candidates")
        for i in range(count):
            expect(page.locator("article").nth(i).locator('img').first).to_be_visible()
        page.screenshot(path=str(OUT / "review-desktop.png"), full_page=True)
        first = page.locator("article").first
        first.get_by_text("Edit details and review image", exact=True).click()
        first.get_by_label("Garment name", exact=True).fill("Reviewed demo garment")
        first.get_by_label("Category", exact=True).select_option("sling_dress")
        first.get_by_label("Primary colour", exact=True).fill("navy")
        first.get_by_label("Fit", exact=True).fill("loose")
        first.get_by_label("Tags (comma separated)", exact=True).fill("demo, reviewed")
        first.get_by_role("button", name="Accept candidate").click()
        expect(first.get_by_text("Review: accepted", exact=True)).to_be_visible()
        expect(page.locator("article").nth(1).get_by_text("Review: pending", exact=True)).to_be_visible()
        report["checks"].append("Accepting one edited candidate leaves the others pending")
        for i in range(1, count):
            card = page.locator("article").nth(i)
            card.get_by_role("button", name="Reject candidate").click()
            expect(card.get_by_text("Review: rejected", exact=True)).to_be_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        page.evaluate("scrollTo(0, 0)")
        page.wait_for_function("document.querySelector('aside').getBoundingClientRect().right <= 1")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile horizontal overflow"
        page.screenshot(path=str(OUT / "review-mobile.png"), full_page=True, animations="disabled")
        page.get_by_role("button", name="Save selected garments", exact=True).click()
        page.wait_for_url("**/wardrobe", timeout=60000)
        expect(page.get_by_text("Reviewed demo garment", exact=True)).to_be_visible(timeout=15000)
        expect(page.get_by_role("button", name="Garments (1)", exact=True)).to_be_visible()
        page.reload()
        expect(page.get_by_text("Reviewed demo garment", exact=True)).to_be_visible()
        report["checks"].append("Only the accepted garment is saved, with edits surviving reload")
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path=str(OUT / "wardrobe-desktop.png"), full_page=True)

        # FR-20--FR-24: complete editing, collection controls, manual outfit,
        # dependency disclosure, explicit confirmation, and archive policy.
        garment_card = page.locator("article").filter(has_text="Reviewed demo garment")
        garment_card.get_by_role("button", name="Edit").click()
        garment_card.get_by_label("Name", exact=True).fill("Edited demo garment")
        garment_card.get_by_label("Category", exact=True).fill("long_sleeve_top")
        garment_card.get_by_label("Primary colour", exact=True).fill("blue")
        garment_card.get_by_label("Pattern", exact=True).fill("solid")
        garment_card.get_by_label("Fit", exact=True).fill("regular")
        garment_card.get_by_label("Styles (comma-separated)", exact=True).fill("smart-casual, campus")
        garment_card.get_by_label("Material", exact=True).fill("cotton")
        garment_card.get_by_label("Tags", exact=True).fill("demo, verified")
        garment_card.get_by_role("button", name="Save changes").click()
        expect(page.get_by_text("Garment updated.", exact=True)).to_be_visible()
        expect(page.get_by_text("Edited demo garment", exact=True)).to_be_visible()
        page.get_by_role("button", name="Toggle favourite for Edited demo garment").click()
        page.get_by_label("Filter garments by favourite").select_option("true")
        expect(page.get_by_text("Edited demo garment", exact=True)).to_be_visible()
        page.get_by_label("Search garments").fill("no such garment")
        expect(page.get_by_text("No matching garments.", exact=False)).to_be_visible()
        page.get_by_label("Search garments").fill("")
        page.get_by_label("Filter garments by favourite").select_option("")
        page.get_by_label("Sort garments").select_option("name_asc")
        expect(page.get_by_text("Edited demo garment", exact=True)).to_be_visible()
        report["checks"].append("Garment search/filter/sort, favourite, and all permitted edits work")

        page.get_by_label("Select Edited demo garment for outfit").check()
        page.get_by_placeholder("Outfit name").fill("Manual campus outfit")
        page.get_by_placeholder("When or how you wear it").fill("Created from confirmed garments")
        page.get_by_role("button", name="Save outfit", exact=True).click()
        expect(page.get_by_text("Manual campus outfit", exact=True)).to_be_visible()
        manual_card = page.locator("article").filter(has_text="Manual campus outfit")
        manual_card.get_by_role("button", name="Edit").click()
        outfit_form = page.locator('form[aria-label="Edit Manual campus outfit"]')
        expect(outfit_form).to_be_visible()
        outfit_form.get_by_label("Name", exact=True).fill("Edited manual outfit")
        outfit_form.locator("textarea").fill("Edited description and membership verified")
        outfit_form.get_by_role("button", name="Save changes").click()
        expect(page.get_by_text("Edited manual outfit", exact=True)).to_be_visible()
        page.get_by_label("Search outfits").fill("membership verified")
        expect(page.get_by_text("Edited manual outfit", exact=True)).to_be_visible()
        page.get_by_label("Search outfits").fill("")
        page.get_by_label("Filter outfits by source").select_option("manual")
        expect(page.get_by_text("Edited manual outfit", exact=True)).to_be_visible()
        page.get_by_label("Filter outfits by source").select_option("")
        report["checks"].append("Manual outfit creation, editing, search, source filter, and ordered membership work")

        page.get_by_role("button", name="Garments (1)", exact=True).click()
        page.get_by_role("button", name="Archive Edited demo garment").click()
        expect(page.locator('p[role="alert"]')).to_contain_text("Remove it from: Edited manual outfit")
        page.get_by_role("button", name="Outfits (1)", exact=True).click()
        dialog_decision["accept"] = True
        page.locator("article").filter(has_text="Edited manual outfit").get_by_role("button", name="Archive").click()
        expect(page.get_by_text("Outfit archived.", exact=True)).to_be_visible()
        page.get_by_role("button", name="Garments (1)", exact=True).click()
        dialog_decision["accept"] = True
        page.get_by_role("button", name="Archive Edited demo garment").click()
        expect(page.get_by_text("Garment archived.", exact=True)).to_be_visible()
        assert any("Archive Edited manual outfit?" in message for message in dialog_messages), dialog_messages
        assert any("Archive Edited demo garment?" in message for message in dialog_messages), dialog_messages
        report["checks"].append("Archive previews dependencies, blocks unsafe removal, and requires explicit confirmation")
        page.screenshot(path=str(OUT / "wardrobe-o1-complete.png"), full_page=True)

        # Exercise the distinct image-based outfit path using a new processing job.
        page.goto(BASE + "/extract")
        page.locator('input[type="file"]').set_input_files(str(SAMPLE))
        page.wait_for_url("**/extract/results?job=**", timeout=60000)
        expect(page.get_by_role("button", name="Accept candidate").first).to_be_visible(timeout=120000)
        outfit_job_url = page.url
        for i in range(2):
            card = page.locator("article").nth(i)
            card.get_by_role("button", name="Accept candidate").click()
            expect(card.get_by_text("Review: accepted", exact=True)).to_be_visible()
        page.get_by_label("Outfit name (required when saving as an outfit)", exact=True).fill("Reviewed demo outfit")
        page.get_by_role("button", name="Save as outfit", exact=True).click()
        page.wait_for_url("**/wardrobe", timeout=60000)
        page.get_by_role("button", name="Outfits (1)", exact=True).click()
        expect(page.get_by_text("Reviewed demo outfit", exact=True)).to_be_visible()
        page.goto(outfit_job_url)
        expect(page.get_by_text("These candidates have already been saved.", exact=False)).to_be_visible()
        assert page.get_by_role("button", name="Save as outfit", exact=True).count() == 0
        report["checks"].append("Saving as an outfit creates its garments and revisiting cannot save twice")
        token = page.evaluate("sessionStorage.getItem('smart_wardrobe_access_token')")
        invalid = context.request.post(BASE + "/api/v1/processing/jobs",
            headers={"Authorization": "Bearer " + token},
            multipart={"file": {"name": "broken.jpg", "mimeType": "image/jpeg", "buffer": b"not an image"}})
        assert invalid.status == 422, invalid.text()
        report["checks"].append("Malformed uploads still return validation errors after real YOLO inference")
        report["page_errors"] = errors
        report["image_warnings"] = image_warnings
        assert not errors, errors
        assert not image_warnings, image_warnings
        context.close(); browser.close()
    report["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    serialised = json.dumps(report, indent=2)
    (OUT / "browser-workflow.json").write_text(serialised, encoding="utf-8")
    (RUN_OUT / "browser-workflow.json").write_text(serialised, encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
