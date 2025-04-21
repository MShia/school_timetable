# Automated School Timetable Scheduler with Streamlit Dashboard

import streamlit as st
import pandas as pd
import numpy as np
from ortools.sat.python import cp_model

st.set_page_config(page_title="School Timetable Scheduler", layout="wide")

st.title("📚 Automated School Timetable")

# Editable Teachers Input
st.sidebar.header("👩‍🏫 Teachers Setup")
teacher_names = st.sidebar.text_area("Enter Teacher Names (comma-separated)", "Mr. Smith, Ms. Jane, Mr. John, Ms. Rose").split(',')
teacher_names = [t.strip() for t in teacher_names if t.strip()]

subject_options = st.sidebar.text_area("Enter Subjects (comma-separated)", "Math, English, Physics, History, Science").split(',')
subject_options = [s.strip() for s in subject_options if s.strip()]

teachers = {}
for teacher in teacher_names:
    subjects_for_teacher = st.sidebar.multiselect(f"Subjects taught by {teacher}", subject_options, default=subject_options[:1], key=f"subj_{teacher}")
    if subjects_for_teacher:
        teachers[teacher] = subjects_for_teacher

# Editable Subject Periods Input
st.sidebar.header("📘 Subjects Periods per Week")
subjects = {}
for subj in subject_options:
    periods = st.sidebar.number_input(f"{subj} periods/week", min_value=1, max_value=10, value=3, key=f"per_{subj}")
    subjects[subj] = periods

# Editable Classes
st.sidebar.header("🏫 Classes")
class_input = st.sidebar.text_area("Enter Classes (comma-separated)", "Grade 1, Grade 2").split(',')
classes = [c.strip() for c in class_input if c.strip()]

# Static configuration
periods_per_day = 6
days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
time_slots = [(d, p) for d in days for p in range(1, periods_per_day + 1)]

# Scheduler Model
model = cp_model.CpModel()
schedule = {}
all_teachers = list(teachers.keys())
all_subjects = list(subjects.keys())

# Define variables
for cls in classes:
    for (day, period) in time_slots:
        for subj in all_subjects:
            for t in all_teachers:
                schedule[(cls, day, period, subj, t)] = model.NewBoolVar(f"{cls}_{day}_{period}_{subj}_{t}")

# Constraints
for cls in classes:
    for subj in subjects:
        valid_teachers = [t for t in all_teachers if subj in teachers[t]]
        if not valid_teachers:
            st.error(f"❌ No teacher available for subject '{subj}' for class '{cls}'")
            st.stop()
        model.Add(
            sum(schedule[(cls, d, p, subj, t)] for (d, p) in time_slots for t in valid_teachers) == subjects[subj]
        )

for cls in classes:
    for (d, p) in time_slots:
        model.Add(
            sum(schedule[(cls, d, p, subj, t)] for subj in all_subjects for t in all_teachers) <= 1
        )

for t in all_teachers:
    for (d, p) in time_slots:
        model.Add(
            sum(schedule[(cls, d, p, subj, t)] for cls in classes for subj in all_subjects) <= 1
        )

# Solve model
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30
status = solver.Solve(model)

# Output

def extract_schedule():
    timetable = []
    for cls in classes:
        for (d, p) in time_slots:
            for subj in all_subjects:
                for t in all_teachers:
                    if solver.Value(schedule[(cls, d, p, subj, t)]):
                        timetable.append([cls, d, p, subj, t])
    df = pd.DataFrame(timetable, columns=["Class", "Day", "Period", "Subject", "Teacher"])
    return df

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    df_timetable = extract_schedule()

    class_selected = st.selectbox("Select Class to View Timetable", classes)
    df_class = df_timetable[df_timetable["Class"] == class_selected]

    pivot = df_class.pivot(index="Period", columns="Day", values="Subject").fillna("")
    st.subheader(f"Timetable for {class_selected}")
    st.dataframe(pivot)

    if st.checkbox("Show Teacher View"):
        teacher_selected = st.selectbox("Select Teacher", all_teachers)
        df_teacher = df_timetable[df_timetable["Teacher"] == teacher_selected]
        st.subheader(f"Schedule for {teacher_selected}")
        st.dataframe(df_teacher.sort_values(by=["Day", "Period"]))
else:
    st.error("❌ Could not find a feasible timetable. Try adjusting input constraints.")
