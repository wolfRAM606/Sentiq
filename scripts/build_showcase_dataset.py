"""Build data/sample/sentiq_showcase_feedback.csv: a SYNTHETIC dataset for demonstrating every Sentiq feature.

All reviews were written for this project. Course codes are invented and instructors are anonymised as
"Faculty A" to "Faculty E". Nothing here is real student feedback, and it is never used for training.

What it exercises:
* auto column mapping (headers are not Sentiq's default names; "Intended Sentiment" maps to the reference-label role)
* five courses with different storylines, two terms and a visible change over time (DS201 grading improves)
* one small group (EE150, under 15 reviews) so the group indicator is withheld
* all twelve teaching aspects, with both issues and strengths, so recommendations of both kinds appear
* negation ("not helpful", "never answers"), contrast ("clear but ..."), multiple aspects in one review,
  ambiguous words without context ("fair enough", "the wifi is fast"), off-topic comments (no aspect)
* validation: two empty rows, two duplicates, two non-alphabetic rows, one review over 5,000 characters,
  mixed and invalid dates, a non-numeric rating, a comma-decimal rating, accented text and an HTML/script string

Run from the project root:  python scripts/build_showcase_dataset.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample" / "sentiq_showcase_feedback.csv"

FALL, SPRING = "Fall 2025", "Spring 2026"
COURSES = {
    "DS201 Data Structures": "Faculty A",
    "ML340 Machine Learning": "Faculty B",
    "MA110 Linear Algebra": "Faculty C",
    "HS205 Professional Communication": "Faculty D",
    "EE150 Basic Electronics": "Faculty E",
}

# (course, term or None for alternate, rating, intended sentiment, text)
R = []


def add(course, rating, sentiment, text, term=None):
    R.append((course, term, rating, sentiment, text))


# ---- DS201: grading problems in Fall, fixed in Spring (shows the time trend) ----
ds = "DS201 Data Structures"
for rating, s, t in [
    (5, "positive", "The explanations of trees and heaps were very clear, and the worked examples made each concept easy to understand."),
    (2, "negative", "The marking scheme for the midterm was never shared, and the grading felt unfair compared to other sections."),
    (2, "negative", "Marks for the lab test were inconsistent; two of us wrote the same answer and got different scores."),
    (5, "positive", "Faculty A has excellent subject knowledge and answers every question with confidence."),
    (1, "negative", "Exam questions had nothing to do with what was taught in class, and the evaluation seemed biased."),
    (3, "neutral", "Please upload the lecture notes before class so we can follow along."),
    (4, "positive", "The coding assignments were challenging but they really helped me understand linked lists and hashing."),
    (2, "negative", "We did not get feedback on our assignments for weeks, so we could not improve before the exam."),
    (5, "positive", "Step by step walkthroughs of sorting algorithms on the board were the best part of the course."),
    (2, "negative", "Not fair that quiz marks counted even though half the class had network problems during the test."),
    (3, "neutral", "The course covers the standard syllabus; nothing special but nothing missing."),
    (4, "positive", "Lab sessions were useful and the teaching assistants were supportive."),
    (1, "negative", "The grading rubric for the project changed after we submitted it."),
    (5, "positive", "I really enjoyed the course overall and would recommend it to juniors."),
    (3, "neutral", "Recursion needed more time; the rest of the pace was fine."),
    (5, "positive", "Very practical examples from real software projects showed where these structures are used."),
]:
    add(ds, rating, s, t, FALL)
for rating, s, t in [
    (5, "positive", "This term the marking criteria were shared in advance and grading felt fair and transparent."),
    (5, "positive", "Detailed feedback on every assignment within a week, which helped a lot before the exams."),
    (5, "positive", "Clear explanations, patient answers in office hours, and fair exams. Great course."),
    (3, "neutral", "The workload is reasonable, though the last assignment overlapped with other deadlines."),
    (5, "positive", "Graph algorithms finally made sense thanks to the visual demonstrations in class."),
    (2, "negative", "The final exam was much harder than the practice papers we were given."),
    (5, "positive", "Faculty A explains concepts clearly and always checks whether everyone is following."),
    (4, "positive", "Interactive problem-solving sessions kept the whole class engaged."),
    (3, "neutral", "Some slides had small errors, but the instructor corrected them quickly."),
    (4, "positive", "The rubric was clear and the marks matched the effort we put in."),
    (5, "positive", "Well organised course with a weekly plan that we could rely on."),
    (2, "negative", "The lab room computers were too slow to run our programs properly."),
    (5, "positive", "Best teacher I have had so far in the department."),
    (4, "positive", "The practice problems were directly relevant to interviews and internships."),
    (3, "neutral", "It would help to have recorded lectures for revision."),
    (5, "positive", "Explanations were not confusing at all, even for difficult topics like dynamic programming."),
    (5, "positive", "Very knowledgeable and passionate about the subject."),
]:
    add(ds, rating, s, t, SPRING)

# ---- ML340: pace and workload issues, strong knowledge and practical work ----
ml = "ML340 Machine Learning"
for rating, s, t in [
    (2, "negative", "The lectures move too fast and I could not follow the derivations."),
    (1, "negative", "Way too much workload: three assignments and a project were due in the same week."),
    (5, "positive", "Excellent subject knowledge; Faculty B is clearly up to date with current research."),
    (2, "negative", "Assignment instructions were confusing and the deadlines were unrealistic."),
    (5, "positive", "The real world case studies on recommendation systems were fascinating."),
    (2, "negative", "The maths was not explained clearly; many steps were skipped."),
    (3, "neutral", "Interesting content, but the pace is very fast for students without a statistics background."),
    (5, "positive", "Hands on labs with real datasets were the best part of this course."),
    (2, "negative", "There was no time to actually learn the material because of the constant assignments."),
    (3, "neutral", "The slides are dense; sharing the reading list earlier would help."),
    (5, "positive", "Industry examples made every topic feel relevant to a real job."),
    (2, "negative", "The instructor rushed through the syllabus and hardly took any questions."),
    (3, "neutral", "The group project was a good idea, but the groups were too large."),
    (2, "negative", "I did not understand neural networks at all because the explanation was rushed."),
    (5, "positive", "Office hours were very helpful and Faculty B always made time to discuss doubts."),
    (2, "negative", "The deadlines overlapped with other courses and the workload became stressful."),
    (5, "positive", "Engaging lectures with live coding demos; I never felt bored."),
    (3, "neutral", "Great content, but it really needs to be spread over two semesters."),
    (1, "negative", "The class goes so fast that most of us gave up taking notes."),
    (4, "positive", "Grading was transparent and the rubric came with every assignment."),
    (3, "neutral", "Recorded videos would help students who struggle with the pace."),
    (5, "positive", "I learnt a lot; this course changed how I think about data."),
    (2, "negative", "Too many assignments and not enough feedback on any of them."),
    (5, "positive", "The knowledgeable instructor connected theory to practice in every lecture."),
    (2, "negative", "Lectures are too fast and the examples are too advanced for beginners."),
    (5, "positive", "Kaggle-style mini competitions made the practical work exciting."),
    (3, "neutral", "The course is demanding. Be ready to spend a lot of time on it."),
    (2, "negative", "The project requirements were vague and changed twice during the term."),
    (5, "positive", "Brilliant teaching methodology: intuition first, then the maths."),
    (2, "negative", "Never enough time in class to ask questions."),
    (5, "positive", "Clear explanation of gradient descent with an animation I still remember."),
    (2, "negative", "Workload is heavy and the pace does not slow down even before exams."),
    (5, "positive", "Very knowledgeable and passionate about the subject."),
    (3, "neutral", "Mixed feelings: brilliant content, exhausting schedule."),
]:
    add(ml, rating, s, t)

# ---- MA110: excellent clarity, monotonous lectures, outdated materials ----
ma = "MA110 Linear Algebra"
for rating, s, t in [
    (5, "positive", "Faculty C explains every concept clearly, with geometric intuition first."),
    (5, "positive", "Very clear explanations; I finally understand eigenvectors."),
    (4, "positive", "The pace is comfortable and the instructor checks that everyone is following."),
    (2, "negative", "The textbook is outdated and hard to follow."),
    (3, "neutral", "More applications of matrices in engineering would make it less theoretical."),
    (4, "positive", "The notes are well structured and easy to revise from."),
    (2, "negative", "Lectures are monotonous; it is just derivations on the board for two hours."),
    (5, "positive", "Patient and kind, always ready to answer questions after class."),
    (4, "positive", "The exams were fair and matched the practice problems."),
    (2, "negative", "Classes feel boring because there is no discussion or interaction."),
    (5, "positive", "Great teaching methodology; the board derivations are easy to follow."),
    (2, "negative", "The reference books recommended are old and do not match the syllabus."),
    (3, "neutral", "Average course. The content was standard and nothing stood out."),
    (5, "positive", "Subject knowledge is outstanding and topics are connected beautifully."),
    (2, "negative", "Not enough practical examples; I still do not know where we use determinants."),
    (4, "positive", "Weekly quizzes kept me consistent with studying."),
    (2, "negative", "Faculty C is not very responsive on email outside class hours."),
    (5, "positive", "Overall a wonderful experience; I would take another course with this instructor."),
    (3, "neutral", "The lectures were clear but the assignments were sometimes longer than expected."),
    (2, "negative", "Dull sessions with no student participation at all."),
    (5, "positive", "Clear explanation of proofs, and the tutorials were very useful."),
    (2, "negative", "The handouts are photocopies from years ago with missing pages."),
    (4, "positive", "Everything about the course was well organised."),
    (3, "neutral", "The material is fine but could use more visual explanations."),
    (5, "positive", "I liked how every new idea was explained clearly before the formal proof."),
    (2, "negative", "I struggled to stay awake; the lectures need more interaction."),
    (4, "positive", "Fair grading and helpful comments on the homework."),
    (3, "neutral", "Interesting subject, though the textbook is not great."),
    (5, "positive", "The best maths teacher I have had at university."),
    (2, "negative", "The course materials are scattered and outdated."),
    (5, "positive", "Concepts were never confusing because of the careful explanations."),
    (3, "neutral", "A solid course overall with room for more engaging activities."),
]:
    add(ma, rating, s, t)

# ---- HS205: high engagement, scattered materials, unclear assignment briefs ----
hs = "HS205 Professional Communication"
for rating, s, t in [
    (5, "positive", "Very engaging and interactive sessions; everyone got a chance to present."),
    (4, "positive", "Detailed feedback on every report helped me improve my writing."),
    (2, "negative", "The course materials were scattered across different platforms and hard to find."),
    (3, "neutral", "Some slides were helpful but the reading was too long for one week."),
    (4, "positive", "Practical writing tasks like emails and proposals were useful for internships."),
    (2, "negative", "Assignment requirements were unclear and the instructions changed twice."),
    (5, "positive", "Friendly and supportive instructor who motivates us to speak confidently."),
    (3, "neutral", "Group discussions were good, but grading for participation felt subjective."),
    (4, "positive", "Well organised course with a clear weekly plan."),
    (2, "negative", "The resources shared were outdated and some links did not work."),
    (5, "positive", "The mock interviews were very relevant to real life job applications."),
    (3, "neutral", "The class was fine. I expected more on technical documentation tools."),
    (5, "positive", "One of the most enjoyable classes; discussions were always lively."),
    (2, "negative", "The presentation rubric was not shared in advance, so the marks felt arbitrary."),
    (4, "positive", "Faculty D is punctual and always well prepared."),
    (3, "neutral", "The workload was light, maybe too light to really practise writing."),
    (4, "positive", "Peer review activities made me more engaged with my classmates' work."),
    (2, "negative", "Lecture slides were not uploaded after class even though we asked several times."),
    (4, "positive", "A good balance between theory and practical exercises."),
    (3, "neutral", "I could not attend some sessions; recordings would have helped."),
    (2, "negative", "The assignment brief was vague, and we lost marks for things that were never mentioned."),
    (5, "positive", "Role plays and debates made every class interactive."),
    (2, "negative", "The study material is spread over three websites and an email thread."),
    (5, "positive", "Encouraging feedback that never made anyone feel embarrassed."),
    (3, "neutral", "Useful course, but the readings could be shorter."),
    (5, "positive", "I gained real confidence in public speaking."),
    (1, "negative", "Not helpful at all when we asked for clarification on the final report format."),
    (5, "positive", "Excellent communication course; I would recommend it to everyone."),
    (3, "neutral", "Good class discussions, average course materials."),
    (5, "positive", "Café-style debate sessions were très engaging and the instructor encouraged everyone to speak."),
]:
    add(hs, rating, s, t)

# ---- EE150: a deliberately small group (under 15) with availability problems ----
ee = "EE150 Basic Electronics"
for rating, s, t in [
    (2, "negative", "Faculty E often comes late to class and we lose the first fifteen minutes."),
    (1, "negative", "Emails are never answered, even before the exam."),
    (4, "positive", "The lab experiments were practical and well planned."),
    (2, "negative", "Office hours were cancelled most weeks without notice."),
    (3, "neutral", "The circuits content is fine but the classes start late."),
    (2, "negative", "Hard to reach the instructor outside class; no response to messages."),
    (5, "positive", "Clear explanation of Ohm's law with hands on breadboard practice."),
    (2, "negative", "Not punctual, and the class often ends early too."),
    (3, "neutral", "Labs are good; lectures are average."),
    (4, "positive", "Lab assistants were helpful and patient."),
    (2, "negative", "The instructor is rarely available for doubt clearing."),
    (4, "positive", "Practical sessions with real components were the highlight."),
]:
    add(ee, rating, s, t)

# ---- language edge cases spread across courses ----
add(ds, 4, "positive", "He is a great teacher.")                                     # general statement -> Overall
add(ml, 3, "neutral", "Fair enough.")                                                 # ambiguous 'fair', no context
add(ma, 3, "neutral", "The campus wifi is fast and reliable.")                        # ambiguous 'fast', off-topic
add(hs, 3, "neutral", "The canteen food near the department is cheap and tasty.")     # no aspect at all
add(ee, 3, "neutral", "Parking near the building is always full.")                    # no aspect at all
add(ml, 4, "positive", "<b>Honestly</b> the notes were <script>alert('hi')</script> useful.")  # shown as text, never run
LONG = (
    "I want to give detailed feedback because this course mattered to me. "
    "The lectures were clear when the instructor slowed down, the labs were the best part of the week, "
    "and the case studies connected the theory to real problems. However, the pace in the second half "
    "was too fast, the assignments piled up at the same time as other courses, and I often felt there "
    "was no time to ask questions. With a lighter schedule and earlier release of the reading list, this "
    "would be one of the best courses in the programme. "
) * 13
add(ml, 3, "neutral", LONG.strip())                                                   # over 5,000 characters


def main():
    rng = random.Random(2026)
    rows = []
    starts = {FALL: date(2025, 8, 20), SPRING: date(2026, 1, 12)}
    for i, (course, term, rating, sentiment, text) in enumerate(R):
        term = term or (FALL if i % 2 else SPRING)
        day = starts[term] + timedelta(days=rng.randint(0, 110))
        rows.append({"Response ID": f"S{i + 1:03d}", "Course": course, "Instructor": COURSES[course], "Term": term,
                     "Submitted On": day.isoformat(), "Rating": str(rating), "Student Feedback": text,
                     "Intended Sentiment": sentiment})
    # date and rating format variety (all still valid reviews)
    rows[3]["Submitted On"] = "12/09/2025"
    rows[5]["Submitted On"] = "Sept 14 2025"
    rows[7]["Submitted On"] = "next Monday"          # cannot be parsed -> counted, left blank
    rows[9]["Rating"] = "four"                        # not numeric -> counted, left blank
    rows[11]["Rating"] = "4,5"                        # comma decimal -> 4.5
    # rows that validation must exclude, each for a stated reason
    base = {"Course": ds, "Instructor": "Faculty A", "Term": SPRING, "Submitted On": "2026-02-02", "Rating": "3", "Intended Sentiment": ""}
    extra = [
        {**base, "Student Feedback": ""},                          # empty
        {**base, "Student Feedback": "    "},                      # whitespace only
        {**base, "Student Feedback": "10/10 !!!"},                 # no letters
        {**base, "Student Feedback": "5"},                         # no letters
        dict(rows[13]),                                            # exact duplicate (same text and course)
        dict(rows[40]),                                            # exact duplicate
    ]
    for j, r in enumerate(extra):
        r["Response ID"] = f"S{len(rows) + j + 1:03d}"
    rows.extend(extra)
    rng.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
