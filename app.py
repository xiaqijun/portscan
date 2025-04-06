from flask import Flask, render_template, request
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from scan import Portscan
from datetime import datetime,timedelta
import uuid
from model import Task, db
scanners = {}
migrate=Migrate()
scheduler=APScheduler()
app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)
migrate.init_app(app, db)
scheduler.init_app(app)
if not scheduler.running:
    scheduler.start()
@app.route('/add_task', methods=['POST'])
def add_task():
    task_name=request.json.get('task_name')
    ip_str=request.json.get('ip_str')
    port_str=request.json.get('port_str')
    timeout=request.json.get('timeout')
    threads=request.json.get('threads')
    id=str(uuid.uuid4())
    scanner=Portscan(ip_str=ip_str, port_str=port_str, timeout=timeout, threads=threads)
    scanners[id]=scanner
    try:
        scheduler.add_job(
            id=id,
            func=add_task,
            args=[id,scanner],
            trigger='date',
            run_date=datetime.now() + timedelta(seconds=5),
            replace_existing=True,
        )
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    task = Task(
        name=task_name,
        task_id=id,
        status='running',
        result_file=None,
        created_at=datetime.now()
    )
    db.session.add(task)
    db.session.commit()

    return {'status': 'success', 'message': '任务添加成功', 'task_id': id}

def add_task( id,scanner):
    scanner.run_scan()
    with scheduler.app.app_context():
        task = Task.query.filter_by(task_id=id).first()
        if task:
            task.status = 'completed'
            task.result_file = scanner.get_results()
            db.session.commit()

@app.route('/stop_task', methods=['POST'])
def stop_task():
    task_id = request.json.get('task_id')
    scanner=scanners.get(task_id)

    if scanner:
        scanner.stop()
        return {'status': 'success', 'message': '任务停止成功'}
    else:
        return {'status': 'error', 'message': '任务不存在或已完成'}

if __name__ == '__main__':
    app.run(host='192.168.1.8',port=5000, debug=True)