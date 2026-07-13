import os
import sys
import json
import threading
import time
import glob
import logging

from flask import Flask, render_template, request, jsonify, Response, send_from_directory

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.utils import get_config, create_dir
from crawler.factory import get_crawler
from logger import log

app = Flask(__name__)

# Store crawl job state
crawl_jobs = {}
job_lock = threading.Lock()


def run_crawl_job(job_id, config):
    """Run a crawl job in a background thread."""
    try:
        with job_lock:
            crawl_jobs[job_id]["status"] = "running"
            crawl_jobs[job_id]["message"] = "Đang khởi tạo crawler..."

        log.setup_logging(log_dir=config["output_dpath"],
                          config_fpath=config["logger_fpath"])
        crawler = get_crawler(**config)

        with job_lock:
            crawl_jobs[job_id]["message"] = "Đang crawl dữ liệu..."

        crawler.start_crawling()

        # Collect results
        result_dir = config["output_dpath"]
        results = []
        if os.path.isdir(result_dir):
            for fpath in sorted(glob.glob(os.path.join(result_dir, "**/*.txt"), recursive=True)):
                # Skip url list files in urls/ subfolder
                if "/urls/" in fpath:
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    lines = content.split("\n")
                    title = lines[0] if lines else "(Không có tiêu đề)"
                    body = "\n".join(lines[1:]) if len(lines) > 1 else ""
                    results.append({
                        "file": os.path.basename(fpath),
                        "title": title,
                        "body": body,
                        "images": [],
                    })

                    # Load image metadata if exists
                    img_meta_path = fpath.replace('.txt', '_images.json')
                    if os.path.isfile(img_meta_path):
                        try:
                            with open(img_meta_path, 'r', encoding='utf-8') as mf:
                                img_data = json.load(mf)
                            img_dir = fpath.replace('.txt', '_images')
                            for img_info in img_data:
                                img_file = os.path.join(img_dir, img_info['filename'])
                                if os.path.isfile(img_file):
                                    # Build serve URL
                                    rel_path = os.path.relpath(img_file, '.')
                                    results[-1]['images'].append({
                                        'url': f'/images/{rel_path}',
                                        'caption': img_info.get('caption', ''),
                                    })
                        except Exception:
                            pass

                except Exception:
                    pass

        with job_lock:
            crawl_jobs[job_id]["status"] = "done"
            crawl_jobs[job_id]["message"] = f"Hoàn tất! Đã crawl {len(results)} bài viết."
            crawl_jobs[job_id]["results"] = results

    except Exception as e:
        with job_lock:
            crawl_jobs[job_id]["status"] = "error"
            crawl_jobs[job_id]["message"] = f"Lỗi: {str(e)}"


@app.route("/")
def index():
    # Build category lists for each website
    categories = {
        "vnexpress": [
            "thoi-su", "du-lich", "the-gioi", "kinh-doanh", "khoa-hoc",
            "giai-tri", "the-thao", "phap-luat", "giao-duc", "suc-khoe", "doi-song"
        ],
        "dantri": [
            "xa-hoi", "the-gioi", "kinh-doanh", "bat-dong-san", "the-thao",
            "lao-dong-viec-lam", "tam-long-nhan-ai", "suc-khoe", "van-hoa",
            "giai-tri", "suc-manh-so", "giao-duc", "an-sinh", "phap-luat"
        ],
        "vietnamnet": [
            "thoi-su", "kinh-doanh", "the-thao", "van-hoa", "giai-tri",
            "the-gioi", "doi-song", "giao-duc", "suc-khoe",
            "thong-tin-truyen-thong", "phap-luat", "oto-xe-may",
            "bat-dong-san", "du-lich"
        ],
        "sueddeutsche": [
            "politik", "wirtschaft", "panorama", "sport", "kultur",
            "wissen", "digital", "karriere", "reise", "auto"
        ],
    }
    return render_template("index.html", categories=categories)


@app.route("/api/crawl", methods=["POST"])
def start_crawl():
    data = request.json
    task = data.get("task", "url")
    webname = data.get("webname", "vnexpress")

    # Build unique output dir per job
    job_id = str(int(time.time() * 1000))
    output_dir = os.path.join("result", f"job_{job_id}")

    config = {
        "webname": webname,
        "task": task,
        "logger_fpath": "logger/logger_config.yml",
        "output_dpath": output_dir,
        "num_workers": int(data.get("num_workers", 1)),
        "date_from": data.get("date_from", "") or "",
        "date_to": data.get("date_to", "") or "",
    }

    if task == "url":
        urls = data.get("urls", "").strip()
        if not urls:
            return jsonify({"error": "Vui lòng nhập ít nhất 1 URL"}), 400
        # Write URLs to temp file
        urls_file = os.path.join("result", f"urls_{job_id}.txt")
        create_dir("result")
        with open(urls_file, "w", encoding="utf-8") as f:
            f.write(urls)
        config["urls_fpath"] = urls_file
        config["article_type"] = ""
        config["total_pages"] = 0
    else:
        config["urls_fpath"] = ""
        config["article_type"] = data.get("article_type", "all")
        config["total_pages"] = int(data.get("total_pages", 1))

    with job_lock:
        crawl_jobs[job_id] = {
            "status": "pending",
            "message": "Đang chờ...",
            "results": [],
        }

    thread = threading.Thread(target=run_crawl_job, args=(job_id, config), daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def job_status(job_id):
    with job_lock:
        job = crawl_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


@app.route('/images/<path:filepath>')
def serve_image(filepath):
    """Serve downloaded article images."""
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    return send_from_directory(directory, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
