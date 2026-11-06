"""Build the project report (report/Driver_Behaviour_Report.docx) with python-docx."""

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
FIG = HERE / "figures"
OUT = HERE / "Driver_Behaviour_Report.docx"

ACCENT = RGBColor(0x1F, 0x4E, 0x79)
GREY = RGBColor(0x59, 0x59, 0x59)
FONT = "Calibri"

doc = Document()

# ---------- page and styles ----------
for s in doc.sections:
    s.page_height, s.page_width = Cm(29.7), Cm(21.0)
    s.top_margin = s.bottom_margin = Cm(2.2)
    s.left_margin = s.right_margin = Cm(2.3)

styles = doc.styles
normal = styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(11)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.15

for name, size, before, after in [("Heading 1", 16, 18, 6), ("Heading 2", 13, 12, 4), ("Title", 26, 0, 6)]:
    st = styles[name]
    st.font.name = FONT
    rpr = st.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(attr), FONT)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        if fonts.get(qn(attr)) is not None:
            del fonts.attrib[qn(attr)]
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = ACCENT
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True


def para(text="", bold_lead=None, size=None, color=None, align=None, italic=False, after=None):
    p = doc.add_paragraph()
    if bold_lead:
        r = p.add_run(bold_lead)
        r.bold = True
    r = p.add_run(text)
    r.italic = italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def bullets(items):
    for n, item in enumerate(items):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.keep_with_next = n < len(items) - 1
        if isinstance(item, tuple):
            r = p.add_run(item[0])
            r.bold = True
            p.add_run(item[1])
        else:
            p.add_run(item)
        p.paragraph_format.space_after = Pt(2)


def shade(cell, hex_fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def table(header, rows, widths, bold_last=False):
    doc.paragraphs[-1].paragraph_format.keep_with_next = True   # keep the intro sentence with its table
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade(c, "1F4E79")
    for n, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(10)
            if bold_last and n == len(rows) - 1:
                r.bold = True
            if n % 2 == 1:
                shade(cells[i], "EAF1F8")
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            for p in row.cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(1)
    keep_together(t)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def keep_together(t):
    """Stop Word from splitting a table across pages."""
    for i, row in enumerate(t.rows):
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
        if i < len(t.rows) - 1:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True


fig_no = [0]


def figure(file, caption, width=15.5):
    fig_no[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(FIG / file), width=Cm(width))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(f"Figure {fig_no[0]}: {caption}")
    r.italic = True
    r.font.size = Pt(9.5)
    r.font.color.rgb = GREY
    c.paragraph_format.space_after = Pt(10)


def goal_box(goal, achieved):
    """Two-row box at the start of each step: the goal and what we achieved."""
    t = doc.add_table(rows=2, cols=2)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for row, (label, text, fill) in zip(t.rows, [("Goal", goal, "DDEBF7"), ("What we achieved", achieved, "E2EFDA")]):
        row.cells[0].text = ""
        r = row.cells[0].paragraphs[0].add_run(label)
        r.bold = True
        r.font.size = Pt(10)
        row.cells[1].text = ""
        r = row.cells[1].paragraphs[0].add_run(text)
        r.font.size = Pt(10)
        for c in row.cells:
            shade(c, fill)
            c.paragraphs[0].paragraph_format.space_after = Pt(2)
            c.paragraphs[0].paragraph_format.space_before = Pt(2)
        row.cells[0].width = Cm(3.6)
        row.cells[1].width = Cm(12.8)
    keep_together(t)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_number_footer(section):
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for kind, text in [("begin", None), (None, "PAGE"), ("end", None)]:
        run = p.add_run()
        if kind:
            fld = OxmlElement("w:fldChar")
            fld.set(qn("w:fldCharType"), kind)
            run._r.append(fld)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = text
            run._r.append(instr)
        run.font.size = Pt(9)
        run.font.color.rgb = GREY


def toc():
    p = doc.add_paragraph()
    run = p.add_run()
    for kind, text in [("begin", None), (None, 'TOC \\o "1-1" \\h \\z \\u'), ("separate", None), ("end", None)]:
        if kind:
            fld = OxmlElement("w:fldChar")
            fld.set(qn("w:fldCharType"), kind)
            run._r.append(fld)
            if kind == "separate":
                t = OxmlElement("w:t")
                t.text = "Right-click and choose Update Field to show the table of contents."
                run._r.append(t)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = text
            run._r.append(instr)


# =====================================================================
# Title page
# =====================================================================
for _ in range(5):
    doc.add_paragraph()
para("MINI PROJECT REPORT  ·  TELEMATICS", size=11, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)
t = doc.add_paragraph(style="Title")
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
t.add_run("Driver Behaviour Analysis and Safety Scoring")
para("Implementing the UAH-DriveSet paper and extending it into a driver safety score for insurance",
     size=13, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, after=40)

para("Submitted by", size=11, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("Kshitij Verma  (24UCC202)", size=13, align=WD_ALIGN_PARAGRAPH.CENTER, after=2).runs[0].bold = True
para("Lakshya Chandak  (24UCC205)", size=13, align=WD_ALIGN_PARAGRAPH.CENTER, after=40).runs[0].bold = True

para("Paper implemented", size=11, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
para("E. Romera, L. M. Bergasa and R. Arroyo, “Need Data for Driver Behaviour Analysis? "
     "Presenting the Public UAH-DriveSet”, IEEE International Conference on Intelligent "
     "Transportation Systems (ITSC), 2016.", size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, after=40)
para("November 2026", size=11, color=GREY, align=WD_ALIGN_PARAGRAPH.CENTER)
doc.add_page_break()

# =====================================================================
# Abstract + contents
# =====================================================================
doc.add_heading("Abstract", level=1)
para("Insurance companies want to price car insurance by how people actually drive, not just by their "
     "age or car. Phones already carry the sensors needed to measure driving. In this project we "
     "implemented the UAH-DriveSet paper, which recorded 40 trips by 6 drivers acting out three styles "
     "(normal, drowsy and aggressive) using a phone app called DriveSafe.")
para("Starting from the raw phone data, we built our own detectors for hard braking, hard acceleration, "
     "sharp turns, speeding, tailgating, lane drifting and weaving. We turned these into scores out of 100 "
     "that stay within about 5 points of the original app. Using only our own numbers, a simple two-rule "
     "classifier recognised the driving style of 39 out of 40 trips for drivers it had never seen "
     "(97.5%), compared with 36 out of 40 (90%) for the original app.")
para("Finally, we extended the work into a 300–900 driver safety score, similar to a CIBIL credit "
     "score. Every normal trip scored higher than every drowsy or aggressive trip, and every score comes "
     "with clear reasons, which makes it suitable for usage-based insurance.")

contents = para("Contents", size=16, color=ACCENT, after=6)
contents.runs[0].bold = True
contents.paragraph_format.space_before = Pt(18)
toc()
doc.add_page_break()

# =====================================================================
# 1. Introduction
# =====================================================================
doc.add_heading("1. Introduction", level=1)
para("Most road accidents are caused by driver behaviour: speeding, following too closely, braking "
     "late or driving while tired. Telematics is the use of sensors (GPS, motion sensors, cameras) to "
     "measure this behaviour. A smartphone has all of these sensors, so it can act as a low-cost "
     "“black box” for a car.")
para("Our faculty asked us to implement the UAH-DriveSet paper. The paper does two things: it shares a "
     "public dataset of real driving, and it shows how the DriveSafe app turns phone data into driving "
     "scores. Our aims were:")
bullets([
    ("Implement the paper: ", "rebuild the app’s pipeline ourselves from the raw sensor data."),
    ("Check our work: ", "compare every result with the app’s own output, and test on drivers we never tuned on."),
    ("Extend it: ", "turn the result into a driver safety score (300–900) that an insurance company could use."),
])
para("We did the work in six steps, one Jupyter notebook each:")
table(["Step", "What we did", "Result"], [
    ["1", "Loaded and explored the dataset", "Understood the data; app baseline = 90%"],
    ["2", "Detected hard braking, acceleration and turns", "Braking matches the app (F1 = 0.81)"],
    ["3", "Measured speeding, tailgating, drifting, weaving", "Agree closely with the app (up to 0.97)"],
    ["4", "Turned everything into scores out of 100", "Within ~5 points of the app"],
    ["5", "Predicted normal / drowsy / aggressive", "39/40 correct (app: 36/40)"],
    ["6", "Built a 300–900 driver safety score", "Safe and risky trips fully separated"],
], [1.4, 8.0, 7.0])

# =====================================================================
# 2. Dataset
# =====================================================================
doc.add_heading("2. The Dataset", level=1)
para("The UAH-DriveSet was recorded by the University of Alcalá (Spain). A phone running the DriveSafe "
     "app was mounted on the windshield while each driver drove fixed routes and acted out a driving style.")
table(["Item", "Details"], [
    ["Drivers", "6 drivers (D1 to D6), each with their own car"],
    ["Trips", "40 trips, about 500 minutes in total"],
    ["Driving styles", "17 normal, 11 aggressive, 12 drowsy (the true label is in the folder name)"],
    ["Roads", "18 motorway trips, 22 secondary road trips"],
    ["License", "CC BY-NC 4.0: research and education only"],
], [3.5, 12.9])
para("Each trip folder contains plain text files with no headings, only columns of numbers. The ones we used:")
table(["File", "Recorded by", "What it contains", "Used for"], [
    ["RAW_ACCELEROMETERS", "Motion sensor", "Forward, sideways and vertical push, 10 times a second", "Hard brakes, accelerations, turns"],
    ["RAW_GPS", "GPS", "Speed and position, once a second", "Speeding, speed checks"],
    ["PROC_OPENSTREETMAP_DATA", "Online map", "Speed limit of the current road", "Speeding"],
    ["PROC_VEHICLE_DETECTION", "Camera", "Distance to the car in front", "Tailgating"],
    ["PROC_LANE_DETECTION", "Camera", "Car’s position inside its lane", "Drifting, weaving"],
    ["EVENTS_INERTIAL", "App", "Hard brakes, accelerations and turns found by the app", "Comparing with our detector"],
    ["SEMANTIC_FINAL", "App", "App’s final scores and style guess for the trip", "Comparing scores and accuracy"],
], [4.3, 2.6, 5.4, 4.1])
para("We wrote a small Python reader (uah_driveset.py) that loads every file into a table with proper "
     "column names, so the rest of the project could work with clean data.")

# =====================================================================
# Step 1
# =====================================================================
doc.add_heading("3. Step 1: Exploring the Data", level=1)
goal_box("Understand what the data looks like and check that the three driving styles really look different.",
         "A working data loader, a clear picture of how each style shows up in the sensors, and the score to "
         "beat: the app guesses the style correctly for 36 of 40 trips (90%).")
para("We compared one driver (D1) on the same road in all three styles. Aggressive driving was faster and "
     "full of sudden spikes in the motion sensor. Drowsy driving wandered more inside the lane, and it even "
     "had the hardest brake in the dataset (−0.57 g), like a tired driver reacting late. Normal driving "
     "was smooth.")
figure("fig1_accelerations.png", "Motion sensor for driver D1 on the same road. Top: forward/back push "
       "(below zero = braking). Bottom: sideways push (turning). Aggressive driving (red) has many sharp spikes.",
       width=12.5)
para("The dataset does not say which sensor axis is which. By checking the moments when the app reported "
     "braking and turning, we found that the Z column is forward/back and the Y column is sideways. "
     "This was needed for every later step.")

# =====================================================================
# Step 2
# =====================================================================
doc.add_heading("4. Step 2: Detecting Harsh Events", level=1)
goal_box("Find hard braking, hard acceleration and sharp turns ourselves from the raw motion sensor, "
         "instead of relying on the app’s list.",
         "A simple detector whose braking events match the app’s with F1 = 0.81 on new drivers, and whose "
         "per-trip event counts follow the app’s very closely (correlation 0.94).")
doc.add_heading("How the detector works", level=2)
para("The detector follows a few simple rules, like a speed camera for pushes:")
bullets([
    "If the push goes past a threshold line, a harsh event has started; when it drops back, the event ends.",
    "Two pushes less than 1 second apart (3 seconds for acceleration and turns) count as one event.",
    "The strongest point of the push decides the level: low, medium or high.",
    "Anything below 5 km/h is ignored, so a parked car never triggers an event.",
])
table(["Event", "Signal", "Threshold", "Medium / High from"], [
    ["Hard braking", "forward push, negative", "0.12 g", "0.20 g / 0.35 g"],
    ["Hard acceleration", "forward push, positive", "0.09 g", "0.13 g / 0.20 g"],
    ["Sharp turn", "sideways push, either side", "0.12 g", "0.17 g / 0.30 g"],
], [3.6, 5.2, 2.8, 4.8])
figure("fig2_detector.png", "Our detector on one aggressive trip. Grey: sensor signal. Dashed: threshold. "
       "Orange dots: events we found. Black crosses: events the app found.", width=12.5)
doc.add_heading("Choosing the thresholds fairly", level=2)
para("We tried many threshold values on drivers D1–D3 and kept the one that made the fewest mistakes "
     "(false alarms plus missed events) compared with the app. A low line gives many false alarms; a high "
     "line misses real brakes. Drivers D4–D6 were kept aside as a fair test.")
figure("fig3_tuning.png", "Choosing the braking threshold on drivers D1–D3. Total mistakes are lowest at 0.12 g.", width=12.5)
doc.add_heading("Results on new drivers (D4–D6)", level=2)
para("Precision tells us how many of our events are real; recall tells us how many of the app’s "
     "events we caught; F1 combines both (1.0 is perfect).")
table(["Event", "Precision", "Recall", "F1", "Same severity level"], [
    ["Braking", "0.90", "0.74", "0.81", "99%"],
    ["Acceleration", "0.78", "0.46", "0.58", "89%"],
    ["Turning", "0.46", "0.45", "0.45", "76%"],
], [3.6, 2.8, 2.8, 2.4, 4.8])
para("Braking matches the app very well. Turning matches least because the app uses extra rules that the "
     "paper does not describe (for example, it never reported a turn below about 50 km/h). For judging a "
     "driver, the total per trip matters more than each single event, and there our counts follow the "
     "app’s closely.")
figure("fig4_event_rates.png", "Harsh events per 10 km for every trip: ours against the app’s "
       "(correlation 0.94). Aggressive trips (red) have about six times more events than normal ones.", width=10)

# =====================================================================
# Step 3
# =====================================================================
doc.add_heading("5. Step 3: Speeding, Tailgating, Drifting and Weaving", level=1)
goal_box("Measure the other risky behaviours from the paper using the GPS, the map and the camera, "
         "so that drowsy driving can be detected too.",
         "Four new measures that agree strongly with the app and clearly separate the styles: speeding and "
         "tailgating point to aggressive drivers, drifting and weaving point to drowsy drivers.")
para("Step 2 catches aggressive driving well, but drowsy drivers rarely brake hard; they wander in their "
     "lane. So we added four measures, each chosen by trying a few sensible values and keeping the one "
     "that agreed best with the app:")
table(["Behaviour", "Our rule", "Normal", "Drowsy", "Aggressive", "Agreement with app"], [
    ["Speeding", "% of time >10% over the speed limit", "5%", "6%", "30%", "0.86"],
    ["Tailgating", "% of time <0.5 s behind the car ahead", "1%", "1%", "21%", "0.97"],
    ["Drifting", "% of time >0.5 m from lane centre", "8%", "38%", "13%", "0.88"],
    ["Weaving", "drift >0.6 m then correct, per minute", "1.5", "3.9", "2.4", "0.69"],
], [2.4, 5.4, 1.7, 1.7, 2.1, 3.1])
para("For tailgating we used time instead of distance: 20 metres is fine in a traffic jam but dangerous "
     "at 100 km/h, so we divide the distance by our speed. We also found that “weaving” in the app "
     "means zig-zagging inside the lane, not changing lanes; lane changes turned out to be equally common "
     "in all three styles. (Agreement values are correlations with the app’s scores, shown without "
     "the minus sign, which only appears because the app counts safety while we count risk.)")
figure("fig5_behaviours.png", "Each box shows all trips of one style. Speeding and tailgating are high "
       "for aggressive trips; drifting and weaving are high for drowsy trips.")

# =====================================================================
# Step 4
# =====================================================================
doc.add_heading("6. Step 4: Scores out of 100", level=1)
goal_box("Put the seven different risk numbers on one common scale, a score out of 100, like the app’s "
         "report card.",
         "Seven behaviour scores and an overall trip score. For new drivers, our overall score is on average "
         "only 4.8 points away from the app’s.")
para("The seven risk numbers are in different units (events per 10 km, % of time, per minute), so they "
     "cannot be compared directly. We used one simple formula for every behaviour:")
bullets([
    ("Allowance: ", "a little risk is forgiven; up to this amount the score stays at 100."),
    ("Halving step: ", "every extra step of risk above the allowance cuts the score in half."),
])
para("For braking, the allowance is 2.5 weighted brakes per 10 km and the halving step is 3.1. A trip with "
     "5.6 brakes per 10 km scores 50, one with 8.7 scores 25, and so on. Medium and high events count "
     "double. The two settings for each behaviour were found by trying about 2,000 combinations on "
     "drivers D1–D3 and keeping the one closest to the app’s scores.")
para("The overall score of a trip is the plain average of its seven scores, exactly as the app does it.")
figure("fig6_score_vs_app.png", "Overall score of every trip: ours against the app’s. The dots lie close "
       "to the line of perfect agreement.", width=9.5)
figure("fig7_scores_by_style.png", "Average scores by style. Drowsy driving loses points on weaving and "
       "drifting; aggressive driving loses points on braking, speeding and car-following.")

# =====================================================================
# Step 5
# =====================================================================
doc.add_heading("7. Step 5: Predicting the Driving Style", level=1)
goal_box("Using only our own numbers, tell whether a trip was normal, drowsy or aggressive, and beat the "
         "app’s 90%.",
         "A simple, explainable rule that is right for 39 of 40 trips (97.5%) on drivers it had never seen. "
         "Machine-learning models confirmed the result.")
para("From the Step 4 scores we made two risk numbers per trip: aggressive risk (points lost on braking, "
     "acceleration, turning, speeding and tailgating) and drowsy risk (points lost on weaving and drifting). "
     "On a chart, the three styles form three separate groups, so two questions are enough:")
bullets([
    "Is aggressive risk above 26.3? Then the trip is aggressive.",
    "Otherwise, is drowsy risk above 30.9? Then it is drowsy. Otherwise it is normal.",
])
para("Each line sits halfway in the gap between the groups it separates.")
figure("fig8_risk_map.png", "Every trip placed by its two risk numbers, coloured by its true style. "
       "The dashed lines are the rule.", width=10)
para("To test fairly, we used “leave one driver out”: learn from 5 drivers, predict the 6th, and repeat "
     "for every driver. Every prediction is therefore about a driver the method has never seen.")
table(["Method", "Correct", "Accuracy"], [
    ["App (DriveSafe), the paper’s baseline", "36 / 40", "90.0%"],
    ["Our two-rule method", "39 / 40", "97.5%"],
    ["Decision tree (2 levels)", "37 / 40", "92.5%"],
    ["Logistic regression", "40 / 40", "100%"],
    ["Random forest", "40 / 40", "100%"],
], [8.5, 3.5, 3.5])
figure("fig9_accuracy.png", "Accuracy of each method on unseen drivers. The dashed line is the app’s 90%.", width=13)
para("The app mistook three aggressive trips and one drowsy trip for normal driving; our rule got all four "
     "right. Its only mistake was a drowsy trip with the hardest brake in the dataset, which looked "
     "aggressive to the sensors.")
para("Random forest scored one trip higher, but with only 40 trips one trip is not real proof that it is "
     "better. We present the simple rule as our main method because it has only two numbers to learn, "
     "is much less likely to memorise the data, and every decision can be explained to a customer. "
     "That matters for insurance.")

# =====================================================================
# Step 6
# =====================================================================
doc.add_heading("8. Step 6: Driver Safety Score (Our Extension)", level=1)
goal_box("Turn the work into a single, easy-to-understand driver safety score from 300 to 900, like a "
         "CIBIL credit score, that an insurance company could use to set premiums.",
         "An explainable safety score in which every normal trip scores higher than every drowsy or "
         "aggressive trip, with clear bands and reasons for each score.")
para("We stretched the Step 4 overall score onto a 300–900 scale: safety score = 300 + 12 × "
     "(overall score − 50). A perfect trip gets 900; an overall score of 50 or less gets 300. "
     "The score is then placed in a band:")
table(["Safety score", "Band", "Example premium change", "Normal trips", "Drowsy trips", "Aggressive trips"], [
    ["750 – 900", "Excellent", "−20%", "16", "0", "0"],
    ["650 – 749", "Good", "−10%", "1", "2", "0"],
    ["550 – 649", "Average", "no change", "0", "7", "2"],
    ["300 – 549", "Risky", "+25%", "0", "3", "9"],
], [2.6, 2.2, 3.4, 2.6, 2.6, 3.0])
figure("fig10_safety_bands.png", "Safety score of every trip. The lowest normal trip (740) is still above "
       "the highest drowsy or aggressive trip (689).")
para("Because the overall score is an average of seven scores, we can tell each driver exactly where they "
     "lost points. For example, one aggressive trip lost 130 points to tailgating and 113 points to hard "
     "braking, ending at 413 (Risky). A driver can see what to improve.")
para("A driver’s score is the distance-weighted average of their trips. All six drivers scored "
     "773–853 when driving normally and only 407–538 when driving aggressively. With a "
     "₹10,000 base premium, the same person would pay ₹8,000 driving normally and ₹12,500 "
     "driving aggressively.")
figure("fig11_driver_scores.png", "Each driver’s safety score in each driving style. Normal driving is "
       "Excellent for every driver.", width=13)

# =====================================================================
# Summary, limitations, conclusion
# =====================================================================
doc.add_heading("9. Summary of Results", level=1)
table(["What we measured", "Result"], [
    ["Braking events vs the app (new drivers)", "F1 = 0.81, same severity 99% of the time"],
    ["Harsh events per trip vs the app", "Correlation 0.94"],
    ["Tailgating / drifting / speeding vs the app", "Correlation 0.97 / 0.88 / 0.86"],
    ["Overall trip score vs the app (new drivers)", "Average gap 4.8 points out of 100"],
    ["Driving style prediction (unseen drivers)", "39/40 with our rule (app: 36/40)"],
    ["Safety score", "Every normal trip above every drowsy or aggressive trip"],
], [8.2, 8.2])

doc.add_heading("10. Limitations", level=1)
bullets([
    ("Small dataset: ", "40 trips from 6 drivers. Very high accuracy here does not guarantee the same on thousands of drivers."),
    ("Acted behaviour: ", "the drivers performed the styles on purpose, so real behaviour is likely less extreme."),
    ("Compared with the app, not the truth: ", "for events and scores, the app was our reference, and it can be wrong too."),
    ("Example bands: ", "the safety bands and premium changes are illustrative; an insurer would set them from claims data."),
    ("Missing context: ", "night driving, weather and traffic are not in the score yet."),
])

doc.add_heading("11. Conclusion and Future Work", level=1)
para("We implemented the UAH-DriveSet paper from the raw phone data upwards. Our own detectors and scores "
     "closely reproduce the original DriveSafe app, and using only our own numbers we recognised the "
     "driving style better than the app did (97.5% against 90%). We then extended the work into an "
     "explainable 300–900 safety score that clearly separates safe from risky driving and tells the "
     "driver why they got their score.")
para("Possible next steps:")
bullets([
    "Collect more drivers and real (not acted) trips, and check the score against real insurance claims.",
    "Add time of day, weather and road type to the score.",
    "Build a small app or dashboard that shows drivers their score and tips after each trip.",
])

doc.add_heading("References", level=1)
para("[1] E. Romera, L. M. Bergasa and R. Arroyo, “Need Data for Driver Behaviour Analysis? Presenting "
     "the Public UAH-DriveSet”, IEEE 19th International Conference on Intelligent Transportation "
     "Systems (ITSC), 2016.")
para("[2] UAH-DriveSet website: http://www.robesafe.uah.es/personal/eduardo.romera/uah-driveset/")

doc.add_heading("Appendix: Project Files", level=1)
table(["Notebook", "Contents"], [
    ["01_explore_data.ipynb", "Loading the data, comparing styles, app baseline"],
    ["02_event_detection.ipynb", "Harsh event detector, threshold tuning, comparison with the app"],
    ["03_behaviour_features.ipynb", "Speeding, tailgating, drifting and weaving"],
    ["04_scores.ipynb", "Scores out of 100 and the overall trip score"],
    ["05_classification.ipynb", "Predicting normal / drowsy / aggressive"],
    ["06_safety_score.ipynb", "The 300–900 driver safety score"],
], [6.0, 10.4])
para("Supporting Python files: uah_driveset.py (data loader), event_detection.py, behaviour_features.py, "
     "scoring.py, classifier.py and safety_score.py. The dataset itself is not included because of its "
     "size and license; it can be downloaded from the website above.")

for s in doc.sections:
    page_number_footer(s)

doc.save(OUT)
print("saved", OUT)
