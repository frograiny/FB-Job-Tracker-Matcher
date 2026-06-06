import csv
import os

TRACKER_PATH = "/home/truongan/my_agent_project/applications_tracker.csv"

def log_actual_jobs():
    jobs = [
        ["Qualcomm", "PhD Internship - AI Research", "Đã chuẩn bị Cover Letter"],
        ["VinMotion", "AI / Robotics Intern", "Đã chuẩn bị Cover Letter"],
        ["Tokyo Tech Lab Vietnam", "Python / NodeJS / AI Intern", "Đã chuẩn bị Cover Letter"],
        ["iCOMM Vietnam", "Python Developer Intern", "Đã chuẩn bị Cover Letter"],
        ["FPT Software", "AI / Machine Learning / Data Intern", "Đã chuẩn bị Cover Letter"]
    ]
    
    file_exists = os.path.exists(TRACKER_PATH)
    with open(TRACKER_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Công ty", "Vị trí", "Trạng thái"])
        for job in jobs:
            writer.writerow(job)
    print("Đã ghi nhận các công việc thực tế vào file log!")

if __name__ == "__main__":
    log_actual_jobs()
