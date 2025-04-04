from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from scan import Portscan
db=SQLAlchemy()
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
    try:
        scheduler.add_job(
            id=task_name,
            func=add_task,
            args=[ ip_str, port_str, timeout, threads],
            trigger='date'
        )
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    return {'status': 'success', 'message': 'Task added successfully'}s


def add_task( ip_str, port_str, timeout, threads):
    scanner=Portscan(ip_str=ip_str, port_str=port_str, timeout=timeout, threads=threads)
    scanner.run_scan()
    return scanner.get_results()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)