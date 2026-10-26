"""Build Sentiq's SYNTHETIC demonstration dataset (data/sample/demo_feedback.csv).

All reviews below were written for demonstration purposes. They are not real
student feedback and are never used to train or evaluate the sentiment model.
A few deliberately invalid rows (empty, duplicate, non-alphabetic) are included
so the validation report can be demonstrated.

Run from the project root:  python scripts/build_demo_dataset.py
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample" / "demo_feedback.csv"

COURSES = {
    "CS201 Data Structures": "Instructor A",
    "CS305 Machine Learning": "Instructor B",
    "MA102 Linear Algebra": "Instructor C",
    "HS110 Technical Communication": "Instructor D",
}

# (course, rating, text)
REVIEWS = [
    # --- CS201 Data Structures --------------------------------------------
    ("CS201 Data Structures", 5, "The explanations of trees and graphs were very clear and the examples made every concept easy to understand."),
    ("CS201 Data Structures", 4, "Great subject knowledge, the instructor answers every question with confidence."),
    ("CS201 Data Structures", 2, "The grading of the second exam felt unfair and the marking scheme was never shared with us."),
    ("CS201 Data Structures", 2, "Marks for the lab test were inconsistent between students who wrote the same answer."),
    ("CS201 Data Structures", 4, "Lectures were well organised and followed the syllabus closely."),
    ("CS201 Data Structures", 3, "The course is okay. Some topics were interesting, others felt rushed at the end of the semester."),
    ("CS201 Data Structures", 1, "Exam questions were not related to what was taught in class and the evaluation was biased."),
    ("CS201 Data Structures", 5, "Best teacher I have had so far, always patient and encouraging."),
    ("CS201 Data Structures", 4, "Coding assignments were challenging but they really helped me understand linked lists and hashing."),
    ("CS201 Data Structures", 2, "We did not get feedback on our assignments for weeks, so we could not improve before the exam."),
    ("CS201 Data Structures", 4, "The visualisations in the slides helped a lot, although the notes could be more detailed."),
    ("CS201 Data Structures", 3, "Please upload the lecture notes before the class so we can prepare."),
    ("CS201 Data Structures", 5, "Very practical examples from real software projects, I can see where these structures are used."),
    ("CS201 Data Structures", 2, "Grading criteria for the project were vague and changed after submission."),
    ("CS201 Data Structures", 4, "The instructor is approachable and replies to emails quickly."),
    ("CS201 Data Structures", 3, "Midterm was fine but the final exam was much harder than the practice papers."),
    ("CS201 Data Structures", 4, "Good teaching style, the step by step walkthroughs of algorithms were helpful."),
    ("CS201 Data Structures", 2, "Not fair that the quiz marks were counted even though half the class had a network problem."),
    ("CS201 Data Structures", 5, "I enjoyed the course overall and would recommend it to juniors."),
    ("CS201 Data Structures", 3, "The pace was manageable for most topics, but recursion needed more time."),
    ("CS201 Data Structures", 4, "Lab sessions were useful and the teaching assistant was supportive."),
    ("CS201 Data Structures", 2, "The instructor sometimes comes late to class and we lose ten minutes every week."),
    # --- CS305 Machine Learning -------------------------------------------
    ("CS305 Machine Learning", 2, "The lectures move too fast and I could not follow the derivations."),
    ("CS305 Machine Learning", 2, "Way too much workload: three assignments and a project due in the same week."),
    ("CS305 Machine Learning", 4, "Excellent subject knowledge and very up to date with the latest research."),
    ("CS305 Machine Learning", 1, "Assignment instructions were confusing and the deadlines were unrealistic."),
    ("CS305 Machine Learning", 4, "The real world case studies on recommendation systems were fascinating."),
    ("CS305 Machine Learning", 2, "Explanations of the maths were not clear, the professor skips many steps."),
    ("CS305 Machine Learning", 3, "Interesting content but the pace is very fast for students without a statistics background."),
    ("CS305 Machine Learning", 5, "Hands on labs with real datasets were the best part of this course."),
    ("CS305 Machine Learning", 2, "Too many assignments, there was no time to actually learn the material properly."),
    ("CS305 Machine Learning", 3, "The slides are dense. It would help to share the reading list earlier."),
    ("CS305 Machine Learning", 4, "Professor is knowledgeable and the examples from industry made the topics relevant."),
    ("CS305 Machine Learning", 2, "Hardly any time was given for questions because the instructor rushed through the syllabus."),
    ("CS305 Machine Learning", 3, "The project was a good idea but the group sizes were too large."),
    ("CS305 Machine Learning", 2, "I did not understand neural networks at all, the explanation was rushed."),
    ("CS305 Machine Learning", 4, "Office hours were very helpful and the professor was always available to discuss doubts."),
    ("CS305 Machine Learning", 2, "The deadlines overlapped with other courses and the workload became stressful."),
    ("CS305 Machine Learning", 4, "Engaging lectures with live coding demos, I never felt bored."),
    ("CS305 Machine Learning", 3, "Course content is great but it needs to be spread over two semesters."),
    ("CS305 Machine Learning", 1, "The class goes so fast that most of us gave up taking notes."),
    ("CS305 Machine Learning", 4, "Grading was transparent and the rubric was shared with every assignment."),
    ("CS305 Machine Learning", 3, "Some recorded videos would help students who struggle with the pace."),
    ("CS305 Machine Learning", 5, "Learnt a lot, this course changed how I think about data."),
    # --- MA102 Linear Algebra ---------------------------------------------
    ("MA102 Linear Algebra", 5, "The professor explains every concept clearly with geometric intuition first."),
    ("MA102 Linear Algebra", 5, "Very clear explanations, I finally understand eigenvectors."),
    ("MA102 Linear Algebra", 4, "The pace is comfortable and the instructor checks that everyone is following."),
    ("MA102 Linear Algebra", 4, "Weekly problem sets were reasonable and the solutions were posted on time."),
    ("MA102 Linear Algebra", 3, "The course is fine, but more applications of matrices in engineering would make it less theoretical."),
    ("MA102 Linear Algebra", 4, "Notes are well structured and easy to revise from."),
    ("MA102 Linear Algebra", 2, "The textbook is outdated and hard to follow."),
    ("MA102 Linear Algebra", 5, "Patient, kind and always ready to answer questions after class."),
    ("MA102 Linear Algebra", 4, "Exams were fair and matched the practice problems."),
    ("MA102 Linear Algebra", 3, "Sometimes the lectures are a little monotonous, adding interactive activities could help."),
    ("MA102 Linear Algebra", 5, "Great teaching methodology, the blackboard derivations were easy to follow."),
    ("MA102 Linear Algebra", 4, "The instructor encourages participation and makes the class interesting."),
    ("MA102 Linear Algebra", 2, "Not enough practical examples, I still do not know where we use determinants."),
    ("MA102 Linear Algebra", 4, "Clear explanation of proofs, and the tutorial sessions were very useful."),
    ("MA102 Linear Algebra", 3, "Average course. The content was standard and nothing stood out."),
    ("MA102 Linear Algebra", 5, "Subject knowledge is outstanding and the instructor connects topics beautifully."),
    ("MA102 Linear Algebra", 4, "Quizzes every two weeks kept me consistent with studying."),
    ("MA102 Linear Algebra", 2, "The instructor is not very responsive on email outside class hours."),
    ("MA102 Linear Algebra", 5, "Overall a wonderful experience, I would take another course with this instructor."),
    ("MA102 Linear Algebra", 4, "The lectures were clear but the assignments were sometimes longer than expected."),
    # --- HS110 Technical Communication ------------------------------------
    ("HS110 Technical Communication", 5, "Very engaging and interactive sessions, everyone got a chance to present."),
    ("HS110 Technical Communication", 4, "The instructor gives detailed feedback on every report, which helped me improve."),
    ("HS110 Technical Communication", 2, "The course materials were scattered across different platforms and hard to find."),
    ("HS110 Technical Communication", 3, "Some slides were helpful but the reading material was too long for one week."),
    ("HS110 Technical Communication", 4, "Practical writing tasks like emails and proposals were useful for internships."),
    ("HS110 Technical Communication", 2, "Assignment requirements were unclear and the instructions changed twice."),
    ("HS110 Technical Communication", 5, "Friendly and supportive instructor who motivates us to speak confidently."),
    ("HS110 Technical Communication", 3, "Group discussions were good, but grading for participation felt subjective."),
    ("HS110 Technical Communication", 4, "Well organised course with a clear weekly plan."),
    ("HS110 Technical Communication", 2, "The resources shared were outdated and some links did not work."),
    ("HS110 Technical Communication", 4, "I liked the mock interviews, very relevant to real life job applications."),
    ("HS110 Technical Communication", 3, "The class was fine. I expected more on technical documentation tools."),
    ("HS110 Technical Communication", 5, "One of the most enjoyable classes, the discussions were always lively."),
    ("HS110 Technical Communication", 2, "The presentation rubric was not shared in advance, so marks felt arbitrary."),
    ("HS110 Technical Communication", 4, "Instructor is punctual and always well prepared."),
    ("HS110 Technical Communication", 3, "The workload was light, maybe too light to really practise writing."),
    ("HS110 Technical Communication", 4, "Peer review activities made me more engaged with my classmates' work."),
    ("HS110 Technical Communication", 2, "Lecture slides were not uploaded after class even though we asked several times."),
    ("HS110 Technical Communication", 4, "Good balance between theory and practical exercises."),
    ("HS110 Technical Communication", 3, "Could not attend some sessions; recordings would have helped."),
]

INVALID_ROWS = [
    ("CS201 Data Structures", 3, ""),
    ("CS305 Machine Learning", 2, "   "),
    ("MA102 Linear Algebra", 4, "5/5 !!!"),
]


def main():
    rng = random.Random(42)
    rows = []
    semesters = [("Fall 2025", date(2025, 9, 1)), ("Spring 2026", date(2026, 1, 15))]
    for i, (course, rating, text) in enumerate(REVIEWS + INVALID_ROWS):
        sem, start = semesters[i % 2]
        when = start + timedelta(days=rng.randint(0, 110))
        rows.append({"response_id": f"R{i + 1:03d}", "course": course, "instructor": COURSES[course], "semester": sem,
                     "submitted_on": when.isoformat(), "rating": rating, "feedback": text,
                     "data_origin": "synthetic-demo"})
    # two exact duplicates to demonstrate duplicate detection
    for src in (rows[0], rows[30]):
        dup = dict(src)
        dup["response_id"] = f"R{len(rows) + 1:03d}"
        rows.append(dup)
    rng.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
